import gzip, re, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試/A/edgar_cache/"
mode = sys.argv[1]
fn = sys.argv[2]
with gzip.open(BASE + fn, 'rt', encoding='utf-8', errors='replace') as f:
    lines = f.read().split('\n')
if mode == 'find':
    rx = re.compile(sys.argv[3], re.I)
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    hits = [i for i, l in enumerate(lines) if rx.search(l)]
    print('LINES', len(lines), 'HITS', len(hits))
    for i in hits[:mx]:
        print(i + 1, '|', lines[i].strip()[:260])
elif mode == 'sed':
    a = int(sys.argv[3]); b = int(sys.argv[4])
    for i in range(a - 1, min(b, len(lines))):
        print(i + 1, '|', lines[i][:1400])
elif mode == 'ctx':
    rx = re.compile(sys.argv[3], re.I)
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    mx = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    hits = [i for i, l in enumerate(lines) if rx.search(l)]
    print('LINES', len(lines), 'HITS', len(hits))
    shown = 0
    for i in hits:
        if shown >= mx:
            break
        shown += 1
        print('=== hit line', i + 1)
        for j in range(max(0, i - n), min(len(lines), i + n + 1)):
            print(j + 1, '|', lines[j][:400])
