"""Parameterized single-researcher bundle + analysis payload from the real EDGAR fixtures.

Not a per-stock script: the ticker, CIK and dates arrive from the fixture sidecars
and the SECURITY dict below, and every test reuses the same builder. The contract
version is a parameter too, so 0.3 keeps being exercised after 0.4 became the default.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

from karst.agents.research import CONTRACT
from karst.fetch.common import utc_now
from karst.fetch.registry import EvidenceRegistry
from karst.packet import build_packet, confined
from karst.fetch.port import pair_staging
from karst.schema import canonical

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SECURITY = {'security_id': 'FIXTURE:FIXTURE', 'issuer_id': 'cik:0000000000', 'ticker': 'FIXTURE',
            'name': 'Fixture issuer', 'currency': 'USD', 'exchange': 'FIXTURE'}
# The AXTI 0.3 bull case, kept as an arithmetic regression only: these are the inputs
# the old annual convention was run with, not a current view of any company.
LEGACY_DCF = {'method': 'fcff_dcf', 'currency': 'USD', 'scale': 'absolute',
              'cashflows': [15.0, -30.0, 60.0, 175.0, 260.0, 327.0],
              'discount_rate': 0.09, 'terminal_growth': 0.035, 'cash': 748.848,
              'nonoperating_assets': 0.0, 'debt': 84.233, 'other_claims': 0.0,
              'diluted_shares': 66.5}
LEGACY_PER_SHARE = 73.03084457399436
BRIDGE = {'cash': 100.0, 'nonoperating_assets': 20.0, 'debt': 60.0,
          'minority_interest': 10.0, 'redeemable_claims': 0.0,
          'convertibles_dilution': 5.0, 'unsupported_claims': [],
          'diluted_shares': 50.0,
          'sbc_treatment': {'basis': 'expensed_in_fcff',
                            'note': '股權激勵已在 FCFF 內支銷，股數未再加一次。'}}


def _statement(text, citations=()):
    return {'text': text, 'citations': [copy.deepcopy(c) for c in citations]}


def dated_dcf(valuation_date, *, timing='end_of_period', scale='absolute'):
    """A dated multi-stage model: one stub year, then full years, normalized terminal."""
    year = int(valuation_date[:4])
    return {'method': 'fcff_dcf_dated', 'currency': 'USD', 'scale': scale,
            'model': {'valuation_date': valuation_date, 'day_count': 'act/365',
                      'timing': timing, 'discount_rate': 0.10,
                      'flows': [{'date': f'{year + 1}-01-01', 'amount': 40.0,
                                 'is_stub': True, 'label': '首個未足一年的 stub'},
                                {'date': f'{year + 2}-01-01', 'amount': 90.0,
                                 'is_stub': False, 'label': '擴張年一'},
                                {'date': f'{year + 3}-01-01', 'amount': 120.0,
                                 'is_stub': False, 'label': '擴張年二'}],
                      'terminal': {'date': f'{year + 3}-01-01', 'final_expansion_fcff': 120.0,
                                   'normalized_fcff': 150.0, 'growth': 0.025,
                                   'basis': '產能到位後的正常化再投資水平。'}},
            'bridge': copy.deepcopy(BRIDGE)}


def ev_multiple(period_start, period_end, *, scale='absolute'):
    return {'method': 'ev_multiple', 'currency': 'USD', 'scale': scale,
            'model': {'metric': 'ebit', 'multiple_basis': 'enterprise_value',
                      'metric_value': 120.0,
                      'period': {'start': period_start, 'end': period_end},
                      'multiple': 11.0, 'comparable_basis': '同業中位數,經資本強度調整。'},
            'bridge': copy.deepcopy(BRIDGE)}


def forward_pe(valuation_date, applies_at, period_start, period_end, *, scale='absolute'):
    return {'method': 'forward_pe', 'currency': 'USD', 'scale': scale,
            'model': {'eps_basis': 'gaap_diluted', 'multiple_basis': 'equity', 'eps': 3.0,
                      'period': {'start': period_start, 'end': period_end},
                      'applies_at': applies_at, 'valuation_date': valuation_date,
                      'multiple': 14.0, 'discount_rate': 0.10,
                      'comparable_basis': '同業前瞻倍數,已核年份與口徑。'},
            'equity': {'diluted_shares': 50.0,
                       'sbc_treatment': {'basis': 'in_diluted_share_count',
                                         'note': '股權激勵計入攤薄股數,盈利未再扣一次。'}}}


def calculated_valuation(as_of, cite):
    """A 0.4 valuation that really carries a DCF, an EV multiple and an equity multiple."""
    day = as_of[:10]
    year = int(day[:4])
    # Each scenario names one operating driver that really feeds its own calculation:
    # changing that input has to move the per-share number, whatever the method is.
    scenarios = [
        ('bear', ev_multiple(f'{year}-01-01', f'{year}-12-31'),
         ('營業利潤', '百萬美元', 120.0, 'model.metric_value')),
        ('base', dated_dcf(day),
         ('第二個擴張年的 FCFF', '百萬美元', 120.0, 'model.flows.2.amount')),
        ('bull', forward_pe(day, f'{year + 1}-12-31', f'{year + 1}-01-01', f'{year + 1}-12-31'),
         ('每股盈利', '美元', 3.0, 'model.eps')),
    ]
    return {
        'valuation_date': day, 'status': 'calculated',
        'method_rationale': _statement('現金流可推導,故主模型用日期化 FCFF;倍數只作對照。'),
        'top_assumptions': [_statement('產能在第二年到位。', cite),
                            _statement('正常化再投資低於擴張期。'),
                            _statement('同業倍數的資本強度可比。')],
        'alternative_view': {'text': '若只按成熟同業倍數定價,得出的每股較低。',
                             'citations': [], 'calculation': ev_multiple(f'{year}-01-01',
                                                                         f'{year}-12-31')},
        'change_attribution': _statement('首版,無上次可歸因。'),
        'scenarios': [{'name': name, 'rationale': _statement(f'{name} 情境的經營假設。'),
                       'drivers': [{'name': driver[0], 'unit': driver[1], 'value': driver[2],
                                    'period': {'start': f'{year}-01-01', 'end': f'{year}-12-31'},
                                    'input_path': driver[3],
                                    'citations': copy.deepcopy(list(cite))}],
                       'calculation': calculation}
                      for name, calculation, driver in scenarios],
        'sensitivities': [
            {'scenario': 'base', 'label': '折現率上調一個百分點',
             'changes': [{'input_path': 'model.discount_rate', 'value': 0.11}],
             'receipt': None},
            {'scenario': 'bear', 'label': '倍數由 11 降至 9',
             'changes': [{'input_path': 'model.multiple', 'value': 9.0}], 'receipt': None},
        ],
        'implied': {'scenario': 'base', 'target_price': 20.0,
                    'solve_for': 'model.discount_rate',
                    'bounds': {'lower': 0.05, 'upper': 0.30},
                    'fixed_assumptions': _statement('固定現金流與終值假設,只解折現率。'),
                    'outcome': 'solved', 'value': None, 'receipt': None},
        'gap_reason': None,
        'implied_requirements': _statement('現價隱含的要求回報高於我們的假設。'),
        'target_prices': [], 'expected_distributions': 0}


def build_bundle(root, *, security=None, stage=None, contract_version=CONTRACT):
    """Register the fixture filings into a fresh bundle; return (bundle, packet, records).

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
    # Evidence 0.3 / 0.4 differ from 0.2 only by the declared version; identity is computed
    # on the 0.2 base either way, so restating the version keeps the same evidence IDs.
    records = registry.records(contract_version=contract_version)
    as_of = max(record['fetched_at'] for record in records)
    # Second precision: the service's own clock ticks in seconds, so a sub-second
    # packet time would make every freshly intaken research look older than its packet.
    created_at = max(utc_now(), as_of)
    packet = build_packet(records, as_of, security, created_at=created_at, root=bundle,
                          contract_version=contract_version)
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


def payload(packet, evidence_id, *, bars_count=(0, 0, 0), valuation=None):
    """A complete analysis payload: analysis only, no IDs, clocks, hashes or versions.

    ``valuation`` replaces the default (deliberately unavailable) valuation block, so a
    test can hand in a real calculated one without a second copy of the whole payload.
    """
    as_of = packet['as_of']
    cite = [{'evidence_id': evidence_id, 'locator': 'L1-L3'}]
    read = list(packet['evidence_ids'])
    empty = {'valuation_date': as_of[:10], 'status': 'unavailable',
             'method_rationale': _statement('現階段缺正常化現金流，未套 FCFF。'),
             'top_assumptions': [], 'alternative_view': _statement('同業倍數只能作範圍參考。'),
             'change_attribution': _statement('首版，無上次可歸因。'), 'scenarios': [],
             'gap_reason': '缺可終值的正常化現金流，未計算內在價值。',
             'implied_requirements': _statement('現價隱含兩季收入加速，尚未有證據支持。'),
             'target_prices': [], 'expected_distributions': 0}
    if packet['contract_version'] >= '0.4.0':
        empty['alternative_view'] = {**empty['alternative_view'], 'calculation': None}
        empty |= {'sensitivities': [], 'implied': None}
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
        'valuation': copy.deepcopy(valuation) if valuation is not None else empty,
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
