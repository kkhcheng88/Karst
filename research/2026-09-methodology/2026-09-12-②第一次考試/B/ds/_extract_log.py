import glob, os, re, csv
BASE = os.path.dirname(os.path.abspath(__file__))
STAMP = re.compile(r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) [A-Z][a-z]{2} [ 0-9]\d \d{2}:\d{2}:\d{2} UTC \d{4})')
print('| # | event_id | start | end | secs | nfiles |')
tot = []
for i in range(11, 43):
    e = 'E%03d' % i
    cands = [c for c in glob.glob(os.path.join(BASE, '*-' + e + '-*.md')) if not c.endswith('.note.md')]
    t = open(cands[0], encoding='utf-8').read()
    k = t.find('執行紀錄')
    sec = t[k:]
    hits = STAMP.findall(sec)
    a, b = (hits[0] if hits else 'NA'), (hits[1] if len(hits) > 1 else 'NA')
    def p(s):
        m = re.search(r'(\d{2}):(\d{2}):(\d{2})', s)
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None
    x, y = p(a), p(b)
    d = (y - x) if (x is not None and y is not None) else None
    n = len(re.findall(r'^\s*\d+\. ', sec, re.M))
    tot.append((i, e, a, b, d, n))
    print('| %d | %s | %s | %s | %s | %d |' % (i, e, a, b, d, n))
print('sum secs from first start to last end:',
      (14 * 3600 + 32 * 60 + 57) - (12 * 3600 + 58 * 60 + 9))
