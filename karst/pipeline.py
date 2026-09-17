"""One parameterized CLI wiring staging -> registry -> packet -> role tasks -> release.

No ticker, CIK or date is hard-coded anywhere: identity arrives through
``--ticker/--cik/...`` or ``--security-json`` and paths through ``--bundle``.
This module never calls a model, a broker account tool or the network.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .agents.assemble import LAYERS, ROLES, UPSTREAM, assemble
from .agents.inputs import prepare_inputs
from .agents.protocol import (COUNTER_PREFIX, DISCIPLINE_FILE, MANDATE_FILE, MODEL_FILE,
                              questions_from_model, sections_from_markdown)
from .fetch.port import pair_staging
from .fetch.registry import EvidenceRegistry
from .packet import build_packet, check_packet, instant, read_json
from .publish import publish
from .schema import ContractError, canonical


# --- command helpers --------------------------------------------------------

def _now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _security(args):
    if args.security_json:
        return read_json(args.security_json)
    missing = [name for name in ('ticker', 'cik', 'name', 'exchange', 'currency')
               if not getattr(args, name.replace('-', '_'))]
    if missing:
        raise ContractError('Supply --security-json or all of: ' + ', '.join('--' + m for m in missing))
    cik = str(args.cik).zfill(10)
    return {'security_id': f'{args.exchange}:{args.ticker}', 'issuer_id': f'cik:{cik}',
            'ticker': args.ticker, 'name': args.name,
            'currency': args.currency, 'exchange': args.exchange}


def _entity_ids(args):
    if not (args.security_json or args.cik or args.ticker):
        return None  # Sidecars carry their own entity IDs.
    security = _security(args)
    return sorted({security['issuer_id'], security['security_id']})


def _latest_versions(records):
    """One applicable version per logical source: the newest observation wins."""
    newest = {}
    for record in records:
        current = newest.get(record['source_id'])
        if current is None or instant(record['fetched_at']) >= instant(current['fetched_at']):
            newest[record['source_id']] = record
    return sorted(newest.values(), key=lambda r: r['evidence_id'])


def _bundle_inputs(bundle):
    return read_json(bundle / 'packet.json'), read_json(bundle / 'evidence.json')


# --- subcommands ------------------------------------------------------------

def cmd_register(args):
    registry = EvidenceRegistry(args.bundle)
    entity_ids = _entity_ids(args)
    registered = diagnostics = 0
    for meta_path, raws in pair_staging(args.staging):
        for raw in raws or [None]:
            record = registry.register(raw, meta_path, entity_ids=entity_ids)
            registered += 1
            diagnostics += record['status'] != 'ok'
    print(f'registered {registered} representations, {diagnostics} diagnostics')
    return 0


def cmd_packet(args):
    registry = EvidenceRegistry(args.bundle)
    records = registry.records()
    if not records:
        raise ContractError('Register sources before building a packet')
    if args.select:
        wanted = set(read_json(args.select))
        selected = [r for r in records if r['evidence_id'] in wanted]
        if {r['evidence_id'] for r in selected} != wanted:
            raise ContractError('Selection names evidence that is not registered')
    else:
        selected = _latest_versions(records)
    as_of = args.as_of or max(r['fetched_at'] for r in selected)
    created_at = max(_now(), as_of)
    packet = build_packet(selected, as_of, _security(args), created_at=created_at, root=args.bundle)
    (args.bundle / 'evidence.json').write_bytes(canonical(selected))
    (args.bundle / 'packet.json').write_bytes(canonical(packet))
    print(f"{packet['packet_id']} as_of={as_of} evidence={len(packet['evidence_ids'])} "
          f"diagnostics={len(packet['diagnostic_ids'])}")
    return 0


def _mandate(path):
    text = Path(path).read_text(encoding='utf-8')
    match = re.search(r'v\d+(?:\.\d+)*', text.splitlines()[0] if text.splitlines() else '')
    if not match:
        raise ContractError('Mandate file must declare a version on its first line')
    return {'version': match[0], 'research_only': True, 'text': text}


def _discipline(path, role):
    wanted = LAYERS[role] or (COUNTER_PREFIX,)
    sections = sections_from_markdown(Path(path).read_text(encoding='utf-8'), wanted)
    if set(sections) != set(wanted):
        raise ContractError(f'Discipline file lacks sections for {role}: {sorted(set(wanted) - set(sections))}')
    return {'counter' if key == COUNTER_PREFIX else key: value for key, value in sections.items()}


def cmd_prepare(args):
    packet, records = _bundle_inputs(args.bundle)
    questions = ([q.strip() for q in args.questions.split(',') if q.strip()] if args.questions
                 else questions_from_model(Path(args.questions_file).read_text(encoding='utf-8')))
    if not questions:
        raise ContractError('No scenario questions found; pass --questions explicitly')
    allowed = read_json(args.allow) if args.allow else packet['evidence_ids']
    upstream = {name: read_json(Path(args.fragments) / f'{name}.json') for name in UPSTREAM[args.role]}
    context = prepare_inputs(
        args.role, packet, records, bundle_root=args.bundle,
        destination=Path(args.tasks) / args.role, allowed_evidence_ids=allowed,
        mandate=_mandate(args.mandate_file), discipline_sections=_discipline(args.discipline_file, args.role),
        scenario_questions=questions, upstream=upstream)
    print(f"{Path(args.tasks) / args.role} prompt_sha256={context['prompt_sha256']}")
    for name, value in sorted(context['input_hashes'].items()):
        print(f'  input_hash {name}={value}')
    return 0


def cmd_assemble(args):
    packet, records = _bundle_inputs(args.bundle)
    fragments = Path(args.fragments)
    assemble(packet, records, {role: read_json(fragments / f'{role}.json') for role in ROLES},
             bundle_root=args.bundle, run=read_json(args.run),
             counter_initial=read_json(fragments / 'counter_initial.json'), output=args.out)
    print(args.out)
    return 0


def cmd_publish(args):
    print(publish(args.bundle, args.output).resolve() / 'index.html')
    return 0


def cmd_status(args):
    registry = EvidenceRegistry(args.bundle)
    print(f'manifest records: {len(registry.records())}')
    packet_path = args.bundle / 'packet.json'
    if not packet_path.exists():
        print('packet: not built')
    else:
        packet, records = _bundle_inputs(args.bundle)
        check_packet(packet, records, args.bundle)
        print(f"packet: {packet['packet_id']} as_of={packet['as_of']}")
        for requirement in packet['requirements']:
            print(f"  requirement {requirement['kind']}: {requirement['status']}")
        pending = [r['request_id'] for r in packet['supplement_requests'] if r['status'] == 'pending']
        print(f"  pending supplements: {', '.join(pending) if pending else 'none'}")
        print(f"  pending updates: {len(packet['pending_updates'])}")
    if args.fragments:
        for role in (*ROLES, 'counter_initial'):
            print(f"fragment {role}: {'present' if (Path(args.fragments) / f'{role}.json').exists() else 'missing'}")
    return 0


# --- CLI --------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog='python -m karst.pipeline', description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)

    def add(name, handler, security=False):
        sub = subparsers.add_parser(name)
        sub.add_argument('--bundle', type=Path, required=True)
        if security:
            sub.add_argument('--security-json', type=Path)
            sub.add_argument('--ticker')
            sub.add_argument('--cik')
            sub.add_argument('--name')
            sub.add_argument('--exchange')
            sub.add_argument('--currency')
        sub.set_defaults(handler=handler)
        return sub

    register = add('register', cmd_register, security=True)
    register.add_argument('--staging', required=True)

    packet = add('packet', cmd_packet, security=True)
    packet.add_argument('--as-of', help='UTC cutoff; default: newest fetched_at among selected records')
    packet.add_argument('--select', type=Path, help='JSON file with an explicit evidence_id list')

    prepare = add('prepare', cmd_prepare)
    prepare.add_argument('--role', required=True, choices=sorted(LAYERS))
    prepare.add_argument('--tasks', required=True)
    prepare.add_argument('--fragments', default='.')
    prepare.add_argument('--mandate-file', default=str(MANDATE_FILE))
    prepare.add_argument('--discipline-file', default=str(DISCIPLINE_FILE))
    prepare.add_argument('--questions-file', default=str(MODEL_FILE))
    prepare.add_argument('--questions', help='comma list, overriding --questions-file')
    prepare.add_argument('--allow', type=Path, help='JSON file with the readable evidence_id list')

    assembler = add('assemble', cmd_assemble)
    assembler.add_argument('--fragments', required=True)
    assembler.add_argument('--run', required=True)
    assembler.add_argument('--out', required=True)

    publisher = add('publish', cmd_publish)
    publisher.add_argument('--output', required=True)

    status = add('status', cmd_status)
    status.add_argument('--fragments')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ContractError, OSError, ValueError, KeyError) as exc:
        print(f'karst.pipeline: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
