"""Raw + sidecar -> immutable 0.2 evidence. No network or ticker-specific logic."""
from __future__ import annotations

import copy
import gzip
import json
import mimetypes
import os
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from ..packet import _private_selectors, confined, instant, time_bounds
from ..schema import ContractError, canonical, decode, digest, validate


# These are public tool names, NOT symbol-specific mappings. New adapters may
# supply kind explicitly; broker tools still have to be on this public allowlist.
PUBLIC_KINDS = {
    'quote_company_profile': 'profile', 'quote_owner_plate': 'profile',
    'quote_market_snapshot': 'prices', 'quote_daily_short_volume': 'short_interest',
    'quote_short_interest': 'short_interest', 'quote_valuation_detail': 'valuation',
    'quote_financials_earnings_price_history': 'financials',
    'quote_insider_holder_list': 'ownership', 'quote_insider_trade_list': 'ownership',
    'quote_shareholders_institutional': 'ownership',
    'quote_research_analyst_consensus': 'consensus',
    'quote_research_rating_summary': 'ratings',
    'quote_research_morningstar_report': 'industry_report',
    'business_segments': 'financials', 'consensus': 'consensus',
    'forecast_eps': 'consensus', 'filings': 'filing_index',
    'finance_calendar': 'calendar', 'fund_holder': 'ownership',
    'shareholder': 'ownership', 'short_positions': 'short_interest',
    'quote': 'prices', 'history_candlesticks_by_date': 'prices',
    'industry_valuation': 'valuation', 'valuation': 'valuation',
    'valuation_history': 'valuation', 'security_facts': 'other_public',
    'institution_rating': 'ratings', 'institution_rating_history': 'ratings',
    'institutional_views': 'ratings',
}


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


def evidence_kind(meta):
    source, tool = meta['source'], meta.get('tool') or ''
    method = tool.split('__')[-1]
    if source in ('futu', 'longbridge') and method not in PUBLIC_KINDS:
        raise ContractError(f'Broker tool is not on public allowlist: {tool}')
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


def _status(meta, raw, media_type):
    declared = meta.get('status')
    if declared == 'FAILED':  # Historical fixture, new adapters use error.
        declared = 'error'
    if declared not in (None, 'ok', 'empty', 'error'):
        raise ContractError('status must be ok, empty or error')
    inferred, reason = ('empty', 'Raw response has no bytes') if not raw.strip() else ('ok', None)
    if 'json' in media_type and raw.strip():
        try:
            payload = decode(raw)
        except ContractError as exc:
            inferred, reason = 'error', f'Invalid JSON response: {exc}'
        else:
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
    if declared == 'ok' and inferred != 'ok':
        raise ContractError('Declared ok contradicts empty/error raw response')
    status = declared or inferred
    return status, None if status == 'ok' else (meta.get('status_reason') or reason or
                                               f'Adapter reported {status}; see raw response and known gaps')


def map_record(raw_path, meta, *, entity_ids, artifact_path):
    """Pure mapping; caller supplies resolved entity IDs, never guessed company IDs."""
    raw_path = Path(raw_path)
    raw = raw_path.read_bytes()
    meta = copy.deepcopy(meta)
    file_meta = meta.get('file')
    if file_meta and file_meta.get('name') == raw_path.name:
        if file_meta.get('sha256') != digest(raw) or file_meta.get('bytes') != len(raw):
            raise ContractError('Landed raw file differs from sidecar file hash/size')
    kind = evidence_kind(meta)
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
    validate('evidence', record)
    for field in ('published_at', 'data_as_of'):
        time_bounds(record, field)  # Validate IANA zones now, even before a packet exists.
    return record


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
            self._atomic(path, data)
        return {'path': relative, 'sha256': sha, 'bytes': len(data)}

    @staticmethod
    def _atomic(path, data):
        temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
        try:
            with temporary.open('xb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def records(self):
        path = confined(self.root, 'evidence/manifest.jsonl')
        if not path.exists():
            return []
        records = [validate('evidence', decode(line)) for line in path.read_bytes().splitlines()]
        if len({r['evidence_id'] for r in records}) != len(records):
            raise ContractError('Duplicate evidence IDs in manifest')
        return records

    def register(self, raw_path, meta_path=None, *, entity_ids=None):
        """raw_path=None registers a metadata-only adapter failure as diagnostic.

        The sidecar itself is the preserved failure envelope; no source body is
        invented, and status=ok is never accepted without a landed raw file.
        """
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
        record = map_record(raw_path, meta, entity_ids=entity_ids, artifact_path=relative)
        if record['artifact']['sha256'] != digest(raw):
            raise ContractError('Raw file changed while registering; retry a stable landed file')
        lock = confined(self.root, 'evidence/registry.lock')
        try:
            handle = lock.open('x')
        except FileExistsError as exc:
            raise ContractError('Registry is busy; retry after the single writer finishes') from exc
        try:
            records = self.records()
            artifact = self._object(raw, suffix)
            metadata = self._object(sidecar, '.meta.json')
            existing = next((r for r in records if r['evidence_id'] == record['evidence_id']), None)
            if existing:
                saved = confined(self.root, existing['artifact']['path']).read_bytes()
                if digest(saved) != existing['artifact']['sha256'] or len(saved) != existing['artifact']['bytes']:
                    raise ContractError('Existing evidence artifact is corrupt')
                if instant(meta['fetched_at']) < instant(existing['fetched_at']):
                    raise ContractError('Cannot backdate an existing immutable observation')
                record = existing
            else:
                prior = [r for r in records if r['source_id'] == record['source_id']]
                record['supersedes'] = prior[-1]['evidence_id'] if prior else None
                records.append(record)
                self._atomic(confined(self.root, 'evidence/manifest.jsonl'),
                             b''.join(canonical(r) for r in records))
            receipt = {'evidence_id': record['evidence_id'], 'fetched_at': meta['fetched_at'],
                       'metadata': metadata, 'artifact': artifact}
            path = confined(self.root, 'evidence/observations.jsonl')
            journal = path.read_bytes() if path.exists() else b''
            if receipt not in [decode(line) for line in journal.splitlines()]:
                self._atomic(path, journal + canonical(receipt))
            return copy.deepcopy(record)
        finally:
            handle.close()
            lock.unlink()
