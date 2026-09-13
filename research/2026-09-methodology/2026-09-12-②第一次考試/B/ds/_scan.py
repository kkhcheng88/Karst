# ASCII runner; Chinese literals live only inside this file.
import io, glob, os, csv, re

F1 = "知道結局"            # 知道結局
F2 = "樣本外於"            # 樣本外於
F3 = "方法診斷"            # 方法診斷
F4 = "記版本"                  # 記版本

def key(s):
    m = re.search(r"E(\d+)", s)
    return int(m.group(1)) if m else 0

def flags(t):
    return "".join("1" if x in t else "." for x in (F1, F2, F3, F4))

cards = {}
for p in glob.glob("B/ds/*E0*.md"):
    b = os.path.basename(p)
    if b.startswith("卡-"):
        cards[key(p)] = flags(io.open(p, encoding="utf-8").read())

rows = {}
for p in glob.glob("B/ds/rows/E0*.csv"):
    r = list(csv.reader(io.open(p, encoding="utf-8")))
    if len(r) >= 2:
        rows[key(p)] = flags(r[1][27])

ids = sorted(set(cards) | set(rows))
mine = [i for i in ids if 45 <= i <= 70]
print("id  card  row   (digits = F1..F4 present)")
for i in mine:
    print("%4d  %-5s %-5s" % (i, cards.get(i, "----"), rows.get(i, "----")))
print()
print("counts mine:", len(mine))
print("cards all4:", sorted([i for i in mine if cards.get(i) == "1111"]))
print("rows  all4:", sorted([i for i in mine if rows.get(i) == "1111"]))
