import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
eid = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'core'
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))

def P(*a):
    print(*a)

if mode == 'core':
    e = d['1_事件識別']
    P('== 事件識別 ==')
    for k in ['event_id','ticker','cik','name','sic','bucket','T0_公布時間_美東','signal_date_反應日','T1_分析截止','T2_可成交','fiscal_quarter','improvement_type_機械','8-K_items','accessionNumber','swapped_in']:
        P(f'  {k}: {e.get(k)}')
    t = d['2_觸發資料']
    P('== 觸發 ==')
    P('  preliminary_release:', t.get('preliminary_release'), '| chars:', t.get('ex991_chars'), '| going_concern:', t.get('going_concern_hit'))
    pg = t.get('prior_release_guidance') or {}
    P('  prior_guidance acc:', pg.get('accessionNumber'), pg.get('filingDate'), 'n_sent:', pg.get('n_guidance_records'))
    for s in (pg.get('guidance_sentences') or []):
        P('    G|', s[:400])
    tr = t.get('earnings_call_transcript') or {}
    if isinstance(tr, dict):
        P('  transcript:', tr.get('report_date'), 'segments:', tr.get('n_segments'), 'chars:', tr.get('n_chars'), 'qna:', tr.get('has_qna'))
    else:
        P('  transcript:', tr)
    f = d['3_截止前文件']
    P('== 文件 ==')
    for k, v in f.items():
        if isinstance(v, dict):
            P(f'  {k}: {v.get("form")} filed={v.get("filingDate")} acc={v.get("accession")} lines={v.get("n_lines")} gz={v.get("local_gz")}')
    q = d['4_財務數列']
    P('== 數列 ==')
    P('  g0:', q.get('g0_signal_q_yoy'), 'prev_q_yoy:', q.get('prev_q_yoy'), 'accel_pp:', q.get('accel_pp'), 'hist_public:', q.get('hist_quarters_public_by_T1'))
    for r in q['quarters']:
        P('   ', json.dumps(r, ensure_ascii=False)[:420])
    P('== 同業 ==')
    p = d['5_同業與行業']
    P('  rule:', p.get('peer_rule_applied'), 'n:', p.get('n_listed_peers'), 'list:', p.get('peer_list_all_tickers'))
    for r in p.get('peer_annual_reports_2_largest', []):
        P('   peer:', json.dumps(r, ensure_ascii=False)[:700])
    P('== 價格 ==')
    P('  ', json.dumps(d['6_價格狀態'], ensure_ascii=False))
    P('== 共識 ==', json.dumps(d['7_共識'], ensure_ascii=False))
elif mode == 'fin':
    q = d['4_財務數列']
    print('g0', q.get('g0_signal_q_yoy'), 'prev_q', q.get('prev_q_yoy'), 'accel_pp', q.get('accel_pp'))
    print('pe,rev,gp,opinc,ocf,rev_after_T1,capex,cash,debt,DA,ni')
    for r in q['quarters']:
        ex = r.get('extra') or {}
        def g(k):
            v = ex.get(k)
            if isinstance(v, dict):
                return v.get('value')
            return v
        print(r['period_end'], r.get('revenue'), r.get('gross_profit'), r.get('operating_income'), r.get('ocf'),
              r.get('revenue_xbrl_first_filed_after_T1'), g('capex'), g('cash_and_equivalents'), g('total_debt'),
              g('depreciation_amortization'), g('net_income'))
elif mode == 'pr':
    print(d['2_觸發資料']['ex991_full_text'])
elif mode == 'tr':
    lo = int(sys.argv[3]); hi = int(sys.argv[4])
    segs = d['2_觸發資料']['earnings_call_transcript']['segments']
    for s in segs[lo:hi]:
        print(json.dumps(s, ensure_ascii=False))
elif mode == 'trhead':
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 14000
    segs = d['2_觸發資料']['earnings_call_transcript']['segments']
    print('SEGKEYS', json.dumps(list(segs[0].keys()), ensure_ascii=False))
    buf = []
    tot = 0
    for s in segs:
        txt = s.get('text') or s.get('content') or ''
        buf.append(txt)
        tot += len(txt)
        if tot >= n:
            break
    print('\n'.join(buf)[:n])
    print('---TOTALCHARS', sum(len((s.get('text') or s.get('content') or '')) for s in segs), 'SEGS', len(segs))
elif mode == 'trgrep':
    import re
    pat = re.compile(sys.argv[3], re.I)
    segs = d['2_觸發資料']['earnings_call_transcript']['segments']
    for i, s in enumerate(segs):
        txt = s.get('text') or s.get('content') or ''
        if pat.search(txt):
            print(i, '|', txt[:700])
