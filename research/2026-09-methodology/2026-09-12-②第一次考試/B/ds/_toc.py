import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
eid = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 160
p = 'A3/packets/%s.json' % eid
d = json.load(open(p, encoding='utf-8'))
t = d['2_觸發資料'].get('earnings_call_transcript')
if t is None:
    print('NO TRANSCRIPT')
    sys.exit(0)
if isinstance(t, str):
    segs = [t]
elif isinstance(t, dict):
    segs = t.get('segments') or t.get('transcript_segments') or []
else:
    segs = t
print('NSEG', len(segs))
for i, s in enumerate(segs):
    if isinstance(s, dict):
        s = s.get('text') or s.get('content') or json.dumps(s, ensure_ascii=False)
    s = re.sub(r'\s+', ' ', s).strip()
    print('[%d] (%d) %s' % (i, len(s), s[:n]))
