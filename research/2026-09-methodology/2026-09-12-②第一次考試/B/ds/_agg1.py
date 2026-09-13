import csv, os
from collections import Counter
BASE = os.path.dirname(os.path.abspath(__file__))
rows = os.path.join(BASE, 'rows')
recs = []
for i in range(1, 43):
    e = 'E%03d' % i
    with open(os.path.join(rows, e + '.csv'), encoding='utf-8') as f:
        r = list(csv.DictReader(f))
    assert len(r) == 1, e
    recs.append(r[0])
for tag, sub in [('ALL E001-E042', recs), ('BATCH E011-E042', recs[10:])]:
    print('==', tag)
    print('  n', len(sub))
    print('  persistence', Counter(x['persistence_overall'] for x in sub))
    print('  supply', Counter(x['supply_catchup'] for x in sub))
    print('  top_driver', Counter(x['top_driver_type'] for x in sub))
    print('  n_drivers', Counter(x['n_drivers'] for x in sub))
    ps = [float(x['p_continue']) for x in sub]
    print('  p_continue min/med/max %.2f %.2f %.2f' % (min(ps), sorted(ps)[len(ps)//2], max(ps)))
    bad = []
    for x in sub:
        for pre in ('g2', 'g4'):
            lo, pt, hi = float(x['pred_%s_lo' % pre]), float(x['pred_%s_point' % pre]), float(x['pred_%s_hi' % pre])
            if not (lo <= pt <= hi):
                bad.append((x['event_id'], pre))
        p = float(x['p_continue'])
        lab = x['persistence_overall']
        exp = '高' if p >= 0.70 else ('中' if p >= 0.40 else '低')
        if lab != exp:
            bad.append((x['event_id'], 'band', lab, p))
    print('  consistency violations:', bad if bad else 'NONE')
    print('  tags', Counter(x['tags'] for x in sub))
print()
print('| event | overall | p | g2 | supply | note |')
for x in recs[10:]:
    note = 'note' if os.path.exists(os.path.join(rows, x['event_id'] + '.note.md')) else ''
    print('| %s | %s | %s | %s | %s | %s |' % (x['event_id'], x['persistence_overall'], x['p_continue'], x['pred_g2_point'], x['supply_catchup'], note))
