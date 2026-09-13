import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
eid = sys.argv[1]
a = int(sys.argv[2]); b = int(sys.argv[3])
w = int(sys.argv[4]) if len(sys.argv) > 4 else 900
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
L = d['2_觸發資料']['ex991_full_text'].split('\n')
print('NLINES', len(L))
for i in range(a, min(b, len(L))):
    if L[i].strip():
        print(i, '|', L[i].strip()[:w])
