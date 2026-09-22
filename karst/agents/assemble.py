"""Six owned fragments -> research.json, using the existing research contract."""
from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ..company_bundle import CompanyBundle
from ..packet import (_citations, _private_selectors, check_packet, check_research,
                      confined, instant, read_json)
from ..schema import ContractError, canonical, digest, embed_evidence_defs, schemas


LAYERS = {'industry': ('L1', 'L2'), 'company': ('L3',), 'valuation': ('L4',),
          'technical': ('L5',), 'counter': (), 'synthesis': ('L6',), 'counter_initial': ()}
ROLES = tuple(role for role in LAYERS if role != 'counter_initial')
PAYLOADS = {'industry': ('phases',), 'company': ('modules', 'phases'),
            'valuation': ('valuation', 'target_date'), 'technical': ('technical', 'market', 'phases'),
            'counter': ('independent_view', 'strongest_counter', 'challenges'),
            'counter_initial': ('independent_view',),
            'synthesis': ('coverage', 'rating', 'execution_state', 'headline', 'plan',
                          'open_questions', 'counter_response')}
UPSTREAM = {'industry': (), 'company': (), 'technical': (), 'counter_initial': (),
            'valuation': ('industry', 'company'),
            'counter': ('counter_initial', 'industry', 'company', 'valuation', 'technical'),
            'synthesis': ('industry', 'company', 'valuation', 'technical', 'counter')}


def _object(properties):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(properties)}


def fragment_schema(role):
    """Derived input shape; no second copy or new version of research.schema."""
    if role not in LAYERS:
        raise ContractError(f'Unknown research role: {role}')
    source = copy.deepcopy(schemas('0.2.0')['research'])
    statement = {'$ref': '#/$defs/statement'}
    extra = {'independent_view': statement, 'strongest_counter': statement,
             'counter_response': statement,
             'challenges': {'type': 'array', 'items': statement}}
    fields = {key: source['properties'][key] if key in source['properties'] else extra[key]
              for key in PAYLOADS[role]}
    result = _object({
        'contract_version': {'const': '0.2.0'}, 'role': {'const': role},
        'packet_id': source['properties']['packet_id'],
        'read_evidence_ids': source['$defs']['layer']['properties']['read_evidence_ids'],
        'input_hashes': _object({key: {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
                                for key in UPSTREAM[role]}),
        'layers': _object({layer: {'$ref': '#/$defs/layer'} for layer in LAYERS[role]}),
        'payload': _object(fields),
        'supplement_requests': copy.deepcopy(schemas('0.2.0')['packet']['properties']['supplement_requests']),
    })
    result.update({'$schema': source['$schema'], '$defs': source['$defs']})
    # Embed canonical dependencies so exported output.schema.json is usable offline
    # by a local runner without resolving URNs or keeping a second schema copy.
    return embed_evidence_defs(result, schemas('0.2.0'))


def validate_fragment(role, fragment, packet, selected, root):
    canonical(fragment)
    errors = sorted(Draft202012Validator(fragment_schema(role), format_checker=FormatChecker()).iter_errors(fragment),
                    key=lambda e: str(list(e.absolute_path)))
    if errors:
        raise ContractError(f'{role}/{list(errors[0].absolute_path)}: {errors[0].message}')
    _private_selectors(fragment)
    if fragment['packet_id'] != packet['packet_id']:
        raise ContractError(f'{role} used another packet version')
    read_ids = set(fragment['read_evidence_ids'])
    if not read_ids <= set(packet['evidence_ids']):
        raise ContractError(f'{role} read log includes unavailable evidence')
    for layer in fragment['layers'].values():
        if not set(layer['read_evidence_ids']) <= read_ids:
            raise ContractError('Layer read log exceeds role read log')
        if any(c['evidence_id'] not in layer['read_evidence_ids'] for c in _citations(layer)):
            raise ContractError('Layer cited evidence absent from its read log')
        if instant(layer['assessed_at']) < instant(packet['created_at']):
            raise ContractError('Fresh role assessment precedes its packet')
    for citation in _citations(fragment):
        eid = citation['evidence_id']
        if eid not in read_ids:
            raise ContractError(f'{role} cited evidence it did not record reading')
        # Same line bounds as the publication core; other locator types retain
        # their source-specific meaning and must be checked by the local runner.
        match = re.fullmatch(r'L(\d+)(?:-L(\d+))?', citation['locator'])
        if match:
            try:
                count = len(confined(root, selected[eid]['artifact']['path']).read_text(encoding='utf-8').splitlines())
            except UnicodeDecodeError as exc:
                raise ContractError('Line locator needs UTF-8 source') from exc
            if not 1 <= int(match[1]) <= int(match[2] or match[1]) <= count:
                raise ContractError('Citation line range is outside source')
    allowed_layers = set(LAYERS[role]) or {'counter'}
    for request in fragment['supplement_requests']:
        if (request['layer'] not in allowed_layers or request['status'] != 'pending'
                or request['evidence_ids'] or request['resolution'] is not None):
            raise ContractError('Role requests must be pending, owned, and without unregistered evidence')
    return fragment


def collect_requests(fragments):
    """Queue for local fetch orchestration; never execute tools from model text."""
    requests = {}
    for fragment in fragments:
        for request in fragment['supplement_requests']:
            old = requests.get(request['request_id'])
            if old is not None and old != request:
                raise ContractError('Conflicting supplement request_id')
            requests[request['request_id']] = copy.deepcopy(request)
    return list(requests.values())


def assemble(packet, evidence_records, fragments, *, bundle_root, run,
             counter_initial, output=None):
    """No model calls, averaging, citation invention or rewriting another role.

    run supplies actual model/version/creation metadata. Six final fragments and
    the sealed counter-first pass remain separate run artifacts for local review.
    """
    selected = check_packet(packet, evidence_records, bundle_root)
    if set(fragments) != set(ROLES):
        raise ContractError('Exactly the six final role fragments are required')
    all_fragments = {**fragments, 'counter_initial': counter_initial}
    for role, fragment in all_fragments.items():
        validate_fragment(role, fragment, packet, selected, bundle_root)
        expected = {key: digest(canonical(all_fragments[key])) for key in UPSTREAM[role]}
        if fragment['input_hashes'] != expected:
            raise ContractError(f'{role} upstream hashes differ; rerun affected downstream roles')
    if fragments['counter']['payload']['independent_view'] != counter_initial['payload']['independent_view']:
        raise ContractError('Counter cannot rewrite its sealed evidence-first view')
    requests = collect_requests(all_fragments.values())
    registered = {r['request_id']: r for r in packet['supplement_requests']}
    for request in requests:
        if registered.get(request['request_id']) != request:
            raise ContractError('Register outstanding supplement requests in a new packet before final assembly')
    allowed = {'research_id', 'created_at', 'mode', 'strategy_version', 'mandate_version', 'method_version', 'models'}
    if not isinstance(run, dict) or set(run) != allowed:
        raise ContractError('run must supply exactly research ID, timestamps, mode, versions and actual models')
    models = run['models']
    if (not isinstance(models, list) or len(models) != len(ROLES) or
            any(not isinstance(m, dict) or 'role' not in m for m in models) or
            {m['role'] for m in models} != set(ROLES)):
        raise ContractError('Record the actual provider/model/prompt version for all six roles')
    research = {**copy.deepcopy(run), 'contract_version': '0.2.0', 'packet_id': packet['packet_id'],
                'layers': {}, 'phases': []}
    for role in ROLES:
        fragment = fragments[role]
        research['layers'].update(copy.deepcopy(fragment['layers']))
        if role == 'counter':
            continue
        for key, value in fragment['payload'].items():
            if key == 'phases':
                research['phases'].extend(copy.deepcopy(value))
            elif key != 'counter_response':
                research[key] = copy.deepcopy(value)
    counter = copy.deepcopy(fragments['counter']['payload']['strongest_counter'])
    if research['headline']['strongest_counter'] != counter or research['layers']['L6']['strongest_counter'] != counter:
        raise ContractError('Synthesis must explicitly carry the counter role strongest objection')
    response = fragments['synthesis']['payload']['counter_response']
    # 0.2 has no counter-response field: preserve it visibly in L6 conclusion.
    conclusion = research['layers']['L6']['conclusion']
    conclusion['text'] += '\n\n對最強反證的回應：' + response['text']
    for citation in response['citations']:
        if citation not in conclusion['citations']:
            conclusion['citations'].append(copy.deepcopy(citation))
    check_research(packet, research, selected, bundle_root)
    if output is not None:
        destination = Path(output)
        # A run directory must be new; never silently overwrite prior research.
        with destination.open('xb') as handle:
            handle.write(canonical(research))
    return research


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--fragments', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        company = CompanyBundle(args.bundle)
        research = assemble(*company.working(),
                            {role: read_json(args.fragments / f'{role}.json') for role in ROLES},
                            bundle_root=args.bundle, run=read_json(args.run),
                            counter_initial=read_json(args.fragments / 'counter_initial.json'))
        company.save_research(research, overwrite=False)
    except (ContractError, OSError, ValueError) as exc:
        parser.exit(2, f'Assembly failed: {exc}\n')
    print(f"research {research['research_id']} saved in {args.bundle}")


if __name__ == '__main__':
    main()
