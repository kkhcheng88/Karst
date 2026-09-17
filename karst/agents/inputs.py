"""Prepare explicit, auditable inputs; actual OS/tool isolation is runner-owned."""
from __future__ import annotations

import copy
from importlib.resources import files

from ..packet import _private_selectors, check_packet
from ..schema import ContractError, canonical, digest
from .assemble import LAYERS, UPSTREAM, fragment_schema, validate_fragment
from .staging import stage_task


def prompt(role):
    if role not in LAYERS:
        raise ContractError('Unknown role')
    root = files('karst.agents').joinpath('prompts')
    name = 'counter' if role == 'counter_initial' else role
    return root.joinpath('common.md').read_text(encoding='utf-8') + '\n\n' + root.joinpath(name + '.md').read_text(encoding='utf-8')


def prepare_inputs(role, packet, evidence_records, *, bundle_root, destination,
                   allowed_evidence_ids, mandate, discipline_sections, scenario_questions,
                   upstream=None):
    """Export only allowed source files and stage inputs into a NEW task directory.

    Do not point the worker at the original bundle/repo. The local runner must
    launch a fresh context, mount only this directory, and allow public tools.
    mandate is a reviewed research-only projection, not an arbitrary repo path.
    """
    if role not in LAYERS:
        raise ContractError('Unknown role')
    selected = check_packet(packet, evidence_records, bundle_root)
    allowed = list(allowed_evidence_ids)
    if len(set(allowed)) != len(allowed) or not set(allowed) <= set(packet['evidence_ids']):
        raise ContractError('Allowed read list must contain unique usable evidence IDs')
    if set(mandate) != {'version', 'research_only', 'text'} or mandate['research_only'] is not True:
        raise ContractError('Pass a reviewed research-only mandate: version, research_only=true, text')
    if not all(isinstance(mandate[k], str) and mandate[k].strip() for k in ('version', 'text')):
        raise ContractError('Mandate needs nonempty version and text')
    _private_selectors(mandate)
    sections = set(LAYERS[role]) or {'counter'}
    if set(discipline_sections) != sections or any(not isinstance(v, str) or not v.strip() for v in discipline_sections.values()):
        raise ContractError('Supply the relevant discipline sections, not the entire repository')
    if not isinstance(scenario_questions, list) or any(not isinstance(q, str) for q in scenario_questions):
        raise ContractError('scenario_questions must be a list of reviewed question strings')
    upstream = upstream or {}
    if set(upstream) != set(UPSTREAM[role]):
        raise ContractError(f'{role} input allowlist forbids extra/missing upstream roles')
    for name, fragment in upstream.items():
        validate_fragment(name, fragment, packet, selected, bundle_root)
    exported = [copy.deepcopy(selected[eid]) for eid in allowed]
    context = {'role': role, 'bundle_path': '.', 'packet_id': packet['packet_id'],
               'security': packet['security'], 'as_of': packet['as_of'],
               'requirements': packet['requirements'], 'pending_updates': packet['pending_updates'],
               'diagnostics': [{key: selected[eid][key] for key in
                                ('evidence_id', 'source', 'kind', 'status', 'status_reason', 'known_gaps', 'fetched_at')}
                               for eid in packet['diagnostic_ids']],
               'supplement_requests': packet['supplement_requests'],
               'allowed_evidence_ids': allowed, 'evidence': exported,
               'mandate': mandate, 'discipline_sections': discipline_sections,
               'scenario_questions': scenario_questions, 'upstream': upstream,
               'input_hashes': {name: digest(canonical(value)) for name, value in upstream.items()},
               'prompt_sha256': digest(prompt(role).encode('utf-8'))}
    stage_task(bundle_root, exported, destination=destination, input_context=context,
               prompt_text=prompt(role), output_schema=fragment_schema(role))
    return context
