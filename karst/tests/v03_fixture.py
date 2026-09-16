"""Parameterized 0.3 bundle + analysis payload built from the real EDGAR fixtures.

Not a per-stock script: the ticker, CIK and dates arrive from the fixture sidecars
and the SECURITY dict below, and every test reuses the same builder.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from karst.fetch.common import utc_now
from karst.fetch.registry import EvidenceRegistry
from karst.packet import build_packet, confined
from karst.pipeline import pair_staging
from karst.schema import canonical

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SECURITY = {'security_id': 'FIXTURE:FIXTURE', 'issuer_id': 'cik:0000000000', 'ticker': 'FIXTURE',
            'name': 'Fixture issuer', 'currency': 'USD', 'exchange': 'FIXTURE'}


def _statement(text, citations=()):
    return {'text': text, 'citations': [copy.deepcopy(c) for c in citations]}


def build_bundle(root, *, security=None, stage=None):
    """Register the fixture filings into a fresh 0.3 bundle; return (bundle, packet, records).

    ``stage`` receives the staging directory before registration, so a test can land
    extra adapter output (prices, for example) through the ordinary adapter path.
    """
    root = Path(root)
    bundle = root / 'bundle'
    staging = root / 'staging'
    shutil.copytree(FIXTURES / 'edgar', staging / 'edgar')
    if stage is not None:
        stage(staging)
    security = copy.deepcopy(security or SECURITY)
    registry = EvidenceRegistry(bundle)
    entity_ids = sorted({security['issuer_id'], security['security_id']})
    for meta_path, raws in pair_staging(staging):
        for raw in raws:
            registry.register(raw, meta_path, entity_ids=entity_ids)
    # Evidence 0.3 differs from 0.2 only by the declared version; identity is computed
    # on the 0.2 base either way, so restating the version keeps the same evidence IDs.
    records = registry.records(contract_version='0.3.0')
    as_of = max(record['fetched_at'] for record in records)
    # Second precision: the service's own clock ticks in seconds, so a sub-second
    # packet time would make every freshly intaken research look older than its packet.
    created_at = max(utc_now(), as_of)
    packet = build_packet(records, as_of, security, created_at=created_at, root=bundle,
                          contract_version='0.3.0')
    (bundle / 'evidence.json').write_bytes(canonical(records))
    (bundle / 'packet.json').write_bytes(canonical(packet))
    return bundle, packet, records


def citable(bundle, records):
    """First registered source whose bytes are UTF-8 text: line locators must be checkable."""
    for record in records:
        data = confined(bundle, record['artifact']['path']).read_bytes()
        try:
            if len(data.decode('utf-8').splitlines()) >= 3:
                return record['evidence_id']
        except UnicodeDecodeError:
            continue
    raise AssertionError('Fixtures contain no UTF-8 text source')


def payload(packet, evidence_id, *, bars_count=(0, 0, 0)):
    """A complete analysis payload: analysis only, no IDs, clocks, hashes or versions."""
    as_of = packet['as_of']
    cite = [{'evidence_id': evidence_id, 'locator': 'L1-L3'}]
    read = list(packet['evidence_ids'])
    layer = {
        'conclusion': _statement('固定測試判斷：由申報原文推出的結論。', cite),
        'assumptions': [_statement('本系統推論：口徑沿用上一季申報。')],
        'strongest_counter': _statement('最強替代解釋：改善來自一次性項目。', cite),
        'gaps': ['缺逐字稿，無法核實指引語氣。'],
        'read_evidence_ids': read,
    }
    return {
        'headline': {key: _statement(text, cite if key == 'main_reason' else ()) for key, text in (
            ('recommendation', '等待資料：逐字稿到手前不入場。'),
            ('main_reason', '申報顯示的改善未被現價反映。'),
            ('key_assumption', '本系統推論：毛利率改善可延續兩季。'),
            ('strongest_counter', '改善可能來自一次性項目。'),
            ('change_conditions', '下一份逐字稿確認訂單延續即重評。'),
            ('change_since_last', '首次研究，沒有上次可比。'))},
        'layers': {name: copy.deepcopy(layer) for name in ('L1', 'L2', 'L3', 'L4', 'L5', 'L6')},
        'modules': [], 'phases': [],
        'market': {'price': 12.5, 'at': as_of, 'currency': packet['security']['currency'],
                   'citations': copy.deepcopy(cite)},
        'valuation': {
            'valuation_date': as_of[:10], 'status': 'unavailable',
            'method_rationale': _statement('現階段缺正常化現金流，未套 FCFF。'),
            'top_assumptions': [], 'alternative_view': _statement('同業倍數只能作範圍參考。'),
            'change_attribution': _statement('首版，無上次可歸因。'), 'scenarios': [],
            'gap_reason': '缺可終值的正常化現金流，未計算內在價值。',
            'implied_requirements': _statement('現價隱含兩季收入加速，尚未有證據支持。'),
            'target_prices': [], 'expected_distributions': 0},
        'technical': {
            'price_basis': 'raw', 'quote_to_bar_factor': 1, 'citations': [],
            'derived': {'sma200': None,
                        'bars_count': dict(zip(('D', 'W', 'M'), bars_count)),
                        'data_as_of': as_of},
            'key_levels': [], 'reading': _statement('價格資料本次只作背景，未形成技術結論。'),
            'gaps': ['不足 200 根已收定日線，SMA200 不可用。']},
        'plan': {'entry_price': None, 'exit_price': None, 'target_price': None,
                 'stress_price': None, 'round_trip_cost_per_share': 0.02,
                 'execution_rule': _statement('等下一份逐字稿；在此之前不設條件單。'),
                 'invalidators': [_statement('毛利率回落至改善前水平即推翻。')],
                 'next_review_at': as_of},
        'coverage': 'partial', 'rating': 'neutral', 'execution_state': 'wait_evidence',
        'target_date': '2027-12-31', 'open_questions': ['逐字稿何時可取得？'],
        'read_evidence_ids': read, 'supplement_requests': [],
    }


ROLE_META = [{'role': 'researcher', 'execution': 'interactive', 'provider': 'fixture',
              'model_id': 'handwritten-test-fixture', 'prompt_version': 'research-protocol-v1'}]
