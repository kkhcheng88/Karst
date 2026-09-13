import csv, os, glob, re
BASE = os.path.dirname(os.path.abspath(__file__))
rows = os.path.join(BASE, 'rows')
cards = glob.glob(os.path.join(BASE, '*E*.md'))
card_ids = {}
for c in cards:
    b = os.path.basename(c)
    m = re.match(r'^[^A-Za-z]*(E\d{3})', b.replace('卡-', 'card-') if False else b.encode('utf-8').decode('utf-8'))
    mm = re.search(r'(E\d{3})', b)
    if mm and 'note' not in b and '.note.' not in b:
        card_ids.setdefault(mm.group(1), []).append(b)
ids = ['E%03d' % i for i in range(1, 43)]
print('--- team-1 range E001..E042 ---')
bad = []
for e in ids:
    cp = os.path.join(rows, e + '.csv')
    ok_csv = os.path.exists(cp)
    ncol = None
    if ok_csv:
        r = list(csv.reader(open(cp, encoding='utf-8')))
        ncol = (len(r[0]), len(r[1]) if len(r) > 1 else 0)
    have_card = e in card_ids
    note = os.path.exists(os.path.join(rows, e + '.note.md'))
    spec = os.path.exists(os.path.join(rows, e + '.spec.json'))
    if not ok_csv or ncol != (28, 28) or not have_card or spec:
        bad.append((e, ok_csv, ncol, have_card, note, spec))
print('problem rows:', bad if bad else 'NONE')
print('n card files matching E0xx:', len(card_ids))
print('cards list for E011-E042:')
for e in ids[10:]:
    print('  ', e, card_ids.get(e))
print('notes present:', sorted(os.path.basename(p) for p in glob.glob(os.path.join(rows, '*.note.md'))))
