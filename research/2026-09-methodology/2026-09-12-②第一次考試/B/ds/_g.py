import json, sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
eid = sys.argv[1]
pat = re.compile(sys.argv[2], re.I)
win = int(sys.argv[3]) if len(sys.argv) > 3 else 0
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
t = d['2_觸發資料']
txt = t['ex991_full_text']
lines = [l for l in txt.split('\n')]
print('=== PR HITS lines=%d' % len(lines))
for i, l in enumerate(lines):
    if pat.search(l):
        lo = max(0, i - win); hi = min(len(lines), i + win + 1)
        if win:
            for j in range(lo, hi):
                print(j, '|', lines[j].strip()[:700])
            print('  ---')
        else:
            print(i, '|', l.strip()[:700])
tr = t.get('earnings_call_transcript')
if isinstance(tr, dict):
    segs = tr.get('segments') or []
    print('=== TR HITS (segs=%d)' % len(segs))
    for i, s in enumerate(segs):
        sx = s.get('text') or s.get('content') or ''
        if pat.search(sx):
            print(i, '|', sx[:1100])
