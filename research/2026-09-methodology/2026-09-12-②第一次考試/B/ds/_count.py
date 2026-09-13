import re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

base = os.path.join(os.path.dirname(os.path.abspath(__file__)))
ACC = re.compile(r'\b(\d{10}-\d{2}-\d{6})\b')
FN = re.compile(r'\b([A-Za-z0-9_\-]{6,}\.(?:htm|html|txt\.gz|txt|gz|json|pdf))\b')

cards = {}
for fn in os.listdir(base):
    m = re.match(r'^卡-(E0\d\d)-', fn)
    if m:
        cards[m.group(1)] = os.path.join(base, fn)

tot = 0
want = ['E0%d' % i for i in range(45, 85)]
for eid in [e for e in want if e in cards]:
    txt = open(cards[eid], encoding='utf-8').read()
    accs = set(a.replace('-', '') for a in ACC.findall(txt))
    fns = set()
    for f in FN.findall(txt):
        if f.startswith('_'):
            continue
        if not any(f.replace('-', '').startswith(a) for a in accs):
            fns.add(f)
    n = 1 + len(accs) + len(fns)
    tot += n
    print(eid, n, '| acc', sorted(accs), '| fn', sorted(fns))
print('EVENTS', len([e for e in want if e in cards]), 'TOTAL', tot)
