import csv, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = sys.argv[1]
r = list(csv.reader(open(p, encoding='utf-8')))
assert len(r) == 2, ('rowcount', len(r))
h, v = r
assert len(h) == 28 and len(v) == 28, ('cols', len(h), len(v))
d = dict(zip(h, v))
assert d['persistence_overall'] in ('高', '中', '低', '無法判斷'), d['persistence_overall']
assert d['supply_catchup'] in ('會', '不會', '不適用', '查不到'), d['supply_catchup']
assert d['top_driver_type'] in ('價格', '數量', '組合', '成本', '一次性', '低基期', '匯率', '收購'), d['top_driver_type']
for pre in ('pred_g2', 'pred_g4'):
    lo, pt, hi = float(d[pre + '_lo']), float(d[pre + '_point']), float(d[pre + '_hi'])
    assert lo <= pt <= hi, (pre, lo, pt, hi)
assert 0.0 <= float(d['p_continue']) <= 1.0
for k, val in d.items():
    assert '\n' not in val and '\r' not in val, k
print('OK', d['event_id'], d['ticker'], '| g2', d['pred_g2_point'], '| p', d['p_continue'], '|', d['persistence_overall'], '|', d['top_driver_type'], '|', d['supply_catchup'])
