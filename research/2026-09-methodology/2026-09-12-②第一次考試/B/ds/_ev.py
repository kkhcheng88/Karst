import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
eid = sys.argv[1]
prchars = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
trchars = int(sys.argv[3]) if len(sys.argv) > 3 else 3500
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
e = d['1_事件識別']
print('== EV ==', eid, d.get('ticker'), d.get('cik'), d.get('name'), 'sic', d.get('sic'), d.get('bucket'))
for k in ['T0_公布時間_美東', 'signal_date_反應日', 'T1_分析截止', 'T2_可成交', 'fiscal_quarter', 'improvement_type_機械', '8-K_items', 'accessionNumber', 'swapped_in', 'EX-99.1_稿頭日期', '公開時段']:
    print('  ', k, '=', e.get(k))
t = d['2_觸發資料']
print('== TRIG ==', 'preliminary', t.get('preliminary_release'), 'pr_chars', t.get('ex991_chars'), 'going_concern', t.get('going_concern_hit'))
print('  trigkeys', list(t.keys()))
pg = t.get('prior_release_guidance') or {}
print('== PRIORGUIDE ==', pg.get('accessionNumber'), pg.get('filingDate'), 'n', pg.get('n_guidance_records'))
for s in (pg.get('guidance_sentences') or []):
    print('  G|', s[:900])
q = d['4_財務數列']
print('== NUM == g0', q.get('g0_signal_q_yoy'), 'prev_q_yoy', q.get('prev_q_yoy'), 'accel_pp', q.get('accel_pp'), 'hist_public', q.get('hist_quarters_public_by_T1'))
print('  numkeys', list(q.keys()))
for r in q['quarters']:
    ex = r.get('extra') or {}
    def g(k, ex=ex):
        v = ex.get(k)
        if isinstance(v, dict):
            return v.get('value')
        return v
    print('  ', r['period_end'], 'rev', r.get('revenue'), 'gp', r.get('gross_profit'), 'op', r.get('operating_income'),
          'ocf', r.get('ocf'), 'afterT1', r.get('revenue_xbrl_first_filed_after_T1'), '|capex', g('capex'), 'cash', g('cash_and_equivalents'),
          'debt', g('total_debt'), 'DA', g('depreciation_amortization'), 'ni', g('net_income'), 'deferred_rev', g('deferred_revenue'),
          'inv', g('inventory'), 'ar', g('accounts_receivable'), 'backlog', g('backlog'), 'rd', g('r_and_d'))
print('== FILES ==')
for k, v in d['3_截止前文件'].items():
    if isinstance(v, dict):
        print('  ', k, v.get('form'), v.get('filingDate'), v.get('accession'), 'lines', v.get('n_lines'), v.get('local_gz'))
    else:
        print('  ', k, v)
print('== PEERS ==', d['5_同業與行業'].get('peer_rule_applied'), d['5_同業與行業'].get('n_listed_peers'), d['5_同業與行業'].get('peer_list_all_tickers'))
for r in d['5_同業與行業'].get('peer_annual_reports_2_largest', []):
    if not isinstance(r, dict):
        print('  PEER', r); continue
    print('  PEER', r.get('ticker'), r.get('filingDate'), r.get('accn'), r.get('local_gz'))
    for x in (r.get('capex_excerpt') or []):
        print('    X|', x[:600])
print('== PRICE ==', json.dumps(d['6_價格狀態'], ensure_ascii=False))
print('== CONSENSUS ==', json.dumps(d['7_共識'], ensure_ascii=False))
print('== MASK ==', json.dumps(d.get('masking_check'), ensure_ascii=False)[:900])
print('== PR (first %d chars) ==' % prchars)
print(t['ex991_full_text'][:prchars])
print('== PR TAIL ==')
print(t['ex991_full_text'][-max(0, prchars // 2):])
tr = t.get('earnings_call_transcript')
if isinstance(tr, dict):
    segs = tr.get('segments') or []
    print('== TR == report_date', tr.get('report_date'), 'segs', len(segs), 'chars', tr.get('n_chars'), 'qna', tr.get('has_qna'))
    tot = 0
    for i, s in enumerate(segs):
        txt = s.get('text') or s.get('content') or ''
        if tot >= trchars:
            break
        print(i, '|', txt[:900])
        tot += len(txt)
else:
    print('== TR ==', tr)
