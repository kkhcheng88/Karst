"""Raw + sidecar -> immutable 0.2 evidence. No network or ticker-specific logic."""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import mimetypes
import os
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from ..packet import _private_selectors, confined, instant, time_bounds
from ..schema import ContractError, canonical, decode, digest, validate
from .port import PUBLIC_KINDS, LandedRecord


def load_meta(path):
    """Preserve sidecar bytes; normalize legacy NaN only in the metadata projection."""
    raw = Path(path).read_bytes()
    constants = []
    def constant(value):
        constants.append(value)
        return None
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError(f'Duplicate sidecar key: {key}')
            result[key] = value
        return result
    try:
        meta = json.loads(raw, parse_constant=constant, object_pairs_hook=pairs)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ContractError(f'Invalid sidecar: {path}') from exc
    if not isinstance(meta, dict):
        raise ContractError('Sidecar must be an object')
    if constants:
        meta.setdefault('known_gaps', []).append(
            'Legacy non-finite sidecar values normalized to null; original sidecar retained.')
    _private_selectors(meta)
    return meta, raw


def evidence_kind(meta, declared=None):
    """The adapter's declared kind wins; the rest is the legacy path for sidecars
    landed before the source port existed. The broker allowlist is checked either way."""
    source, tool = meta['source'], meta.get('tool') or ''
    method = tool.split('__')[-1]
    if source in ('futu', 'longbridge') and method not in PUBLIC_KINDS:
        raise ContractError(f'Broker tool is not on public allowlist: {tool}')
    if declared:
        return declared
    if meta.get('kind'):
        return meta['kind']
    if method in PUBLIC_KINDS:
        return PUBLIC_KINDS[method]
    if source == 'edgar':
        return 'filing' if (meta['params'].get('document') or
                            meta['params'].get('kind') in ('primary', 'exhibit')) else 'filing_index'
    if source.startswith('local-prices'):
        return 'prices'
    if source == 'defeatbeta':
        if re.search(r'get_transcript(?:\(|$)', tool):
            return 'transcript'
        if 'earning_call_transcripts' in tool:
            return 'filing_index'  # Catalogue is NOT transcript text.
        for token, kind in [('calendar', 'calendar'), ('info', 'profile'),
                            ('shares', 'financials'), ('splits', 'prices'),
                            ('quarterly_', 'financials'), ('price', 'prices')]:
            if token in tool:
                return kind
    raise ContractError('Unknown public source/tool; adapter must supply kind')


def iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def normalize_period(coverage):
    """No fiscal inference, datetime slicing, TTM conversion or sentinel dates."""
    coverage = coverage or {}
    start = iso_day(coverage.get('start', coverage.get('from')))
    end = iso_day(coverage.get('end', coverage.get('to')))
    if start is None and end is None:
        end = iso_day(coverage.get('reportDate', coverage.get('period_end')))
    if start and end and start > end:
        raise ContractError('Normalized period start exceeds end')
    return {'start': start, 'end': end}


def _time(value, basis, zone=None, *, strict=False):
    if value is None:
        return None, 'unknown', None, basis
    if iso_day(value):
        return value, 'date', zone, basis
    try:
        moment = instant(value)
        if moment.tzinfo is not None and moment.utcoffset() is not None:
            return moment.isoformat(), 'datetime', None, basis
    except (AttributeError, ValueError, TypeError):
        pass
    if strict:
        raise ContractError('Explicit timestamp has no valid timezone or ISO date')
    return None, 'unknown', None, f'{basis}; original value {value!r} has unproven time precision/timezone'


def _infer_status(raw, media_type):
    """Legacy path: read the envelope for a sidecar that never declared a status."""
    inferred, reason = ('empty', 'Raw response has no bytes') if not raw.strip() else ('ok', None)
    if 'json' in media_type and raw.strip():
        try:
            payload = decode(raw)
        except ContractError as exc:
            return 'error', f'Invalid JSON response: {exc}'
        _private_selectors(payload)
        envelope = payload if isinstance(payload, dict) else {}
        response = envelope.get('response', payload)
        if (envelope.get('error') or envelope.get('error_code') not in (None, 0, '0') or
                (isinstance(response, dict) and (response.get('ret_code') not in (None, 0, '0') or
                 response.get('error') or response.get('error_code') not in (None, 0, '0')))):
            inferred, reason = 'error', 'Source returned an error envelope; see preserved raw response'
        elif response is None or response == [] or response == {}:
            inferred, reason = 'empty', 'Source returned an empty response'
        elif isinstance(response, dict):
            for key in ('records', 'data'):
                if response.get(key) == []:
                    inferred, reason = 'empty', f'Source returned {key}=[]'
    return inferred, reason


def _status(meta, raw, media_type):
    """ok / empty / error is judged once, by the adapter that landed it (KARST-246).

    A sidecar that declares a status is taken at its word: two judgements of the
    same bytes can disagree, and then nobody knows which one the researcher is
    reading. Only a sidecar landed before the source port existed — one with no
    status at all — is still read here. Two things stay checked either way: a
    landed file is required for ok, and the body is scanned for private selectors.
    """
    declared = meta.get('status')
    if declared == 'FAILED':  # Historical fixture, new adapters use error.
        declared = 'error'
    if declared not in (None, 'ok', 'empty', 'error'):
        raise ContractError('status must be ok, empty or error')
    if declared is None:
        status, reason = _infer_status(raw, media_type)
    else:
        status, reason = declared, None
        if 'json' in media_type and raw.strip():
            try:
                payload = decode(raw)
            except ContractError:
                payload = None  # unparseable bytes stay as landed; the adapter's status stands
            if payload is not None:
                _private_selectors(payload)  # privacy guard, not a status judgement
        if status == 'ok' and not raw.strip():
            raise ContractError('Declared ok contradicts an empty landed file')
    return status, None if status == 'ok' else (meta.get('status_reason') or reason or
                                               f'Adapter reported {status}; see raw response and known gaps')


def map_record(raw_path, meta, *, entity_ids, artifact_path, contract_version='0.2.0', kind=None):
    """Pure mapping; caller supplies resolved entity IDs, never guessed company IDs.

    ``contract_version`` only restates the declared version at the end: identity is
    always computed on the 0.2.0 base, so the same bytes keep the same evidence_id
    whichever contract the caller is assembling.
    """
    raw_path = Path(raw_path)
    raw = raw_path.read_bytes()
    meta = copy.deepcopy(meta)
    file_meta = meta.get('file')
    if file_meta and file_meta.get('name') == raw_path.name:
        if file_meta.get('sha256') != digest(raw) or file_meta.get('bytes') != len(raw):
            raise ContractError('Landed raw file differs from sidecar file hash/size')
    kind = evidence_kind(meta, kind)
    _private_selectors(meta['params'])
    if not isinstance(entity_ids, list) or not entity_ids:
        raise ContractError('Adapter must supply nonempty entity_ids')
    media_type = meta.get('media_type') or mimetypes.guess_type(raw_path.name)[0] or 'application/octet-stream'
    status, reason = _status(meta, raw, media_type)
    coverage = meta.get('coverage', meta.get('period'))
    if coverage is not None and not isinstance(coverage, dict):
        coverage = {'source_period': coverage}
    truncated = meta['truncated']
    if isinstance(truncated, dict):
        truncated = truncated.get('is_truncated')
    if not isinstance(truncated, bool):
        raise ContractError('truncated must be boolean or contain is_truncated boolean')
    gaps = list(meta['known_gaps'])
    representation = 'landed'
    for name, entry in (meta.get('files') or {}).items():
        if not entry or entry.get('name') != raw_path.name:
            continue
        representation = name
        if name == 'raw':
            original = gzip.decompress(raw) if raw_path.suffix == '.gz' else raw
            if ('sha256' in entry and digest(original) != entry['sha256']) or (
                    'bytes' in entry and len(original) != entry['bytes']):
                raise ContractError('Landed raw file differs from sidecar hash/size')
            truncated = False  # Fixture truncation applies to derived text only.
        else:
            gaps.append(f'Derived {name} representation: {entry.get("derivation", "see sidecar")}')
    published = meta.get('published_at')
    pub_basis = meta.get('published_at_basis') or 'Source does not establish publication time'
    data_at = meta.get('data_as_of')
    data_basis = meta.get('data_as_of_basis') or 'Source does not establish a dataset snapshot time'
    # Legacy broker timestamps usually describe a row/trade/refresh, not when
    # this whole version became public. New adapters can explicitly attest precision.
    if meta['source'] != 'edgar' and 'published_at_precision' not in meta:
        if kind != 'transcript' and data_at is None and published is not None:
            data_at, data_basis = published, pub_basis
        published = None
        pub_basis = 'Legacy sidecar date is not proof of version publication; original basis: ' + pub_basis
    if meta.get('published_at_precision') == 'unknown':
        published = None
    times = {}
    for field, value, basis in [('published_at', published, pub_basis), ('data_as_of', data_at, data_basis)]:
        value, precision, zone, basis = _time(value, basis, meta.get(field + '_timezone'),
                                            strict=meta.get(field + '_precision') in ('date', 'datetime'))
        if field + '_precision' in meta and meta[field + '_precision'] != precision:
            raise ContractError(f'{field} contradicts explicit precision')
        times.update({field: value, field + '_precision': precision,
                      field + '_timezone': zone, field + '_basis': basis})
    source_url = meta.get('source_url', meta['params'].get('url'))
    identity = {'source': meta['source'], 'tool': meta['tool'], 'params': meta['params'],
                'source_url': source_url, 'representation': representation, 'media_type': media_type}
    source_id = meta.get('source_id') or 'src-' + digest(canonical(identity))
    record = dict(contract_version='0.2.0', source_id=source_id, source=meta['source'], kind=kind,
                  provenance=meta.get('provenance', 'public_market'), entity_ids=sorted(set(entity_ids)),
                  source_url=source_url, tool=meta['tool'], params=meta['params'],
                  fetched_at=meta['fetched_at'], period=normalize_period(coverage), coverage=coverage,
                  truncated=truncated, known_gaps=gaps, media_type=media_type,
                  artifact={'path': artifact_path, 'sha256': digest(raw), 'bytes': len(raw)},
                  status=status, status_reason=reason, **times)
    # A fresh observation alone does not create a new semantic source version.
    semantic = {k: v for k, v in record.items() if k != 'fetched_at'}
    semantic['artifact'] = {k: v for k, v in record['artifact'].items() if k != 'path'}
    # Broker landing envelopes contain OUR acquisition time as well as the
    # provider response. Changing only that outer timestamp is an observation,
    # not a new economic source version. Keep every exact raw envelope in the
    # receipt journal; preserve all provider timestamps inside response.
    if meta['source'] in ('futu', 'longbridge') and 'json' in media_type:
        try:
            envelope = decode(raw)
        except ContractError:
            envelope = None
        if (isinstance(envelope, dict) and 'response' in envelope and
                'fetched_at' in envelope and envelope.get('tool') == meta['tool'] and
                envelope.get('params') == meta['params']):
            body = canonical({key: value for key, value in envelope.items() if key != 'fetched_at'})
            semantic['artifact'] = {'sha256': digest(body), 'bytes': len(body)}
    version = digest(canonical(semantic))
    record.update(source_version=version, evidence_id='ev-' + version, supersedes=None)
    record['contract_version'] = contract_version
    validate('evidence', record)
    for field in ('published_at', 'data_as_of'):
        time_bounds(record, field)  # Validate IANA zones now, even before a packet exists.
    return record


def atomic_write(path, data):
    """Replace ``path`` with ``data`` in one step: a reader sees the old bytes or the new."""
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class EvidenceRegistry:
    """Single-writer, append-only logical journals; atomic file replacement on disk."""
    def __init__(self, bundle_root):
        self.root = Path(bundle_root).resolve()
        self.directory = confined(self.root, 'evidence')
        self.directory.mkdir(parents=True, exist_ok=True)

    def _object(self, data, suffix):
        sha = digest(data)
        relative = f'evidence/objects/{sha[:2]}/{sha}{suffix}'
        path = confined(self.root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise ContractError('Existing content-addressed object is corrupt')
        else:
            atomic_write(path, data)
        return {'path': relative, 'sha256': sha, 'bytes': len(data)}

    def records(self, contract_version=None):
        """Manifest records; ``contract_version`` restates the declared version only.

        Identity is unchanged by that restatement — the same record under 0.3.0 keeps
        its 0.2.0-derived evidence_id, so a packet can be assembled at either version
        without re-registering anything.
        """
        path = confined(self.root, 'evidence/manifest.jsonl')
        if not path.exists():
            return []
        records = _validated(path, path.read_bytes())
        if contract_version is not None:
            records = [{**record, 'contract_version': contract_version} for record in records]
        return records

    def register(self, raw_path, meta_path=None, *, entity_ids=None, contract_version='0.2.0'):
        """Register one landed representation. ``raw_path`` may be a ``LandedRecord``.

        With a LandedRecord the adapter's declared kind is used as it stands — the
        registry registers, it does not classify. Without one (a sidecar landed
        before the port existed) the legacy inference in ``evidence_kind`` runs.
        ``raw_path=None`` registers a metadata-only adapter failure as diagnostic:
        the sidecar itself is the preserved failure envelope, no source body is
        invented, and status=ok is never accepted without a landed raw file.
        """
        return self.register_many([(raw_path, meta_path)], entity_ids=entity_ids,
                                  contract_version=contract_version)[0]

    def register_many(self, items, *, entity_ids=None, contract_version='0.2.0'):
        """Register several landed representations under one lock, in order.

        ``items`` are LandedRecords or ``(raw_path, meta_path)`` pairs. The result is
        the same as registering them one by one — same records, same supersession
        chain, same receipts — but the manifest and the observation journal are each
        read once and replaced once, however many sources one refresh landed.
        """
        prepared = [self._prepare(*(item if isinstance(item, tuple) else (item, None)),
                                  entity_ids=entity_ids, contract_version=contract_version)
                    for item in items]
        if not prepared:
            return []
        lock = confined(self.root, 'evidence/registry.lock')
        try:
            handle = lock.open('x')
        except FileExistsError as exc:
            raise ContractError('Registry is busy; retry after the single writer finishes') from exc
        try:
            manifest = confined(self.root, 'evidence/manifest.jsonl')
            records = self.records()
            index = {r['evidence_id']: r for r in records}
            latest = {r['source_id']: r['evidence_id'] for r in records}
            journal_path = confined(self.root, 'evidence/observations.jsonl')
            journal = journal_path.read_bytes() if journal_path.exists() else b''
            seen = {canonical(decode(line)) for line in journal.splitlines()}
            added, appended, results = [], [], []
            for record, meta, raw, suffix, sidecar in prepared:
                artifact = self._object(raw, suffix)
                metadata = self._object(sidecar, '.meta.json')
                existing = index.get(record['evidence_id'])
                if existing:
                    saved = confined(self.root, existing['artifact']['path']).read_bytes()
                    if digest(saved) != existing['artifact']['sha256'] or len(saved) != existing['artifact']['bytes']:
                        raise ContractError('Existing evidence artifact is corrupt')
                    if instant(meta['fetched_at']) < instant(existing['fetched_at']):
                        raise ContractError('Cannot backdate an existing immutable observation')
                    record = existing
                else:
                    record['supersedes'] = latest.get(record['source_id'])
                    index[record['evidence_id']] = record
                    latest[record['source_id']] = record['evidence_id']
                    added.append(record)
                receipt = canonical({'evidence_id': record['evidence_id'], 'fetched_at': meta['fetched_at'],
                                     'metadata': metadata, 'artifact': artifact})
                if receipt not in seen:
                    seen.add(receipt)
                    appended.append(receipt)
                results.append(copy.deepcopy(record))
            if added:
                body = b''.join(canonical(r) for r in records + added)
                atomic_write(manifest, body)
                _remember(manifest, body)
            if appended:
                atomic_write(journal_path, journal + b''.join(appended))
            return results
        finally:
            handle.close()
            lock.unlink()

    def _prepare(self, raw_path, meta_path=None, *, entity_ids=None, contract_version='0.2.0'):
        """Map one landed representation to its record, outside the writer lock."""
        kind = None
        if isinstance(raw_path, LandedRecord):
            landed, raw_path = raw_path, raw_path.path
            kind, meta_path = landed.kind, meta_path or landed.meta_path
        if raw_path is None and meta_path is None:
            raise ContractError('Supply a raw file or an explicit diagnostic sidecar')
        missing_raw = raw_path is None
        raw_path = Path(meta_path if missing_raw else raw_path)
        meta_path = Path(meta_path) if meta_path else raw_path.with_suffix('.meta.json')
        meta, sidecar = load_meta(meta_path)
        if missing_raw:
            if meta.get('status') not in ('empty', 'error', 'FAILED'):
                raise ContractError('Metadata-only registration requires explicit empty/error status')
            meta.setdefault('known_gaps', []).append('No raw document landed; artifact is the adapter diagnostic sidecar itself.')
        entity_ids = entity_ids if entity_ids is not None else meta.get('entity_ids')
        raw = raw_path.read_bytes()
        suffix = ''.join(raw_path.suffixes[-2:]) if raw_path.suffix == '.gz' else raw_path.suffix
        if not re.fullmatch(r'(?:\.[A-Za-z0-9]+){0,2}', suffix):
            suffix = '.bin'
        relative = f'evidence/objects/{digest(raw)[:2]}/{digest(raw)}{suffix}'
        record = map_record(raw_path, meta, entity_ids=entity_ids, artifact_path=relative,
                            contract_version=contract_version, kind=kind)
        if record['artifact']['sha256'] != digest(raw):
            raise ContractError('Raw file changed while registering; retry a stable landed file')
        return record, meta, raw, suffix, sidecar


# Validated manifest prefix per path: (bytes, blake2b of them). The manifest is
# append-only, so a later read schema-validates only the lines past what was already
# validated; every line is still decoded, and a rewritten prefix is validated in full.
_prefixes = {}


def _fingerprint(data):
    return hashlib.blake2b(data, digest_size=16).digest()


def _validated(path, data):
    known = _prefixes.get(path)
    trusted = known[0] if known and len(data) >= known[0] and \
        _fingerprint(data[:known[0]]) == known[1] else 0
    records = [decode(line) for line in data[:trusted].splitlines()]
    records += [validate('evidence', decode(line)) for line in data[trusted:].splitlines()]
    if len({r['evidence_id'] for r in records}) != len(records):
        raise ContractError('Duplicate evidence IDs in manifest')
    if trusted < len(data):
        _remember(path, data)
    return records


def _remember(path, data):
    _prefixes[path] = (len(data), _fingerprint(data))
