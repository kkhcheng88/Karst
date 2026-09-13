import csv, glob, os, re
BASE = os.path.dirname(os.path.abspath(__file__))
rows = os.path.join(BASE, 'rows')
for i in list(range(11, 43)):
    e = 'E%03d' % i
    x = list(csv.DictReader(open(os.path.join(rows, e + '.csv'), encoding='utf-8')))[0]
    cands = [c for c in glob.glob(os.path.join(BASE, '*-' + e + '-*.md')) if not c.endswith('.note.md')]
    head = open(cands[0], encoding='utf-8').read()[:700]
    m = re.search(r'g0_signal_q_yoy:\s*([-0-9.]+)', head)
    m2 = re.search(r'g0[^\n]{0,20}?([-0-9.]+)', head)
    g0 = float(m.group(1)) if m else None
    thr = 0.8 * g0 if (g0 is not None and g0 >= 0) else g0
    pt = float(x['pred_g2_point'])
    flag = ''
    if g0 is not None:
        if pt >= thr and x['persistence_overall'] == '低':
            flag = 'POINT>=THR but 低'
        if pt < thr and x['persistence_overall'] == '高':
            flag = 'POINT<THR but 高'
    print('%s g0=%-9s thr=%-9s pt=%-8s %s %s' % (e, g0, None if thr is None else round(thr, 6), pt, x['persistence_overall'], flag))
