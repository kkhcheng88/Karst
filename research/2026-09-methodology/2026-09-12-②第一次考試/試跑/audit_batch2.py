# -*- coding: utf-8 -*-
"""KARST-228 批量定位第二輪:解第一批未清的疑點。"""
import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_lookup import search

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_audit_hits2.txt")

Q = [
 ("DS-E001-#4", "E001", "144,871"), ("DS-E001-#4", "E001", "Total revenues (2)"),
 ("DS-E001-#4", "E001", "excluding acquisitions"),
 ("DS-E001-#7", "E001", "PediaCare"), ("DS-E001-#7", "E001", "inventory"),
 ("DS-E001-#7", "E001", "re-entered"),
 ("DS-E001-#20", "E001", "Revenues of the acquired Insight"),

 ("DS-E009-#4", "E009", "general and administrative expense"),
 ("DS-E009-#4", "E009", "705"), ("DS-E009-#4", "E009", "capital"),
 ("DS-E009-#7", "E009", "held for sale, net"),
 ("DS-E009-#20", "E009", "53"), ("DS-E009-#20", "E009", "guidance"),

 ("DS-E017-#4", "E017", "infectious disease"), ("DS-E017-#4", "E017", "16.7 million"),
 ("DS-E017-#7", "E017", "Ancestry"), ("DS-E017-#7", "E017", "license"),
 ("DS-E017-#20", "E017", "no significant concentrations"),

 ("DS-E025-#4", "E025", "units shipped"), ("DS-E025-#4", "E025", "9.6%"),
 ("DS-E025-#7", "E025", "9.6%"),

 ("DS-E033-#4", "E033", "average realized price"), ("DS-E033-#4", "E033", "208.0"),
 ("DS-E033-#4", "E033", "1,800"), ("DS-E033-#4", "E033", "18 million"),
 ("DS-E033-#20", "E033", "primary reasons for our change"),

 ("DS-E041-#4", "E041", "PES net sales"), ("DS-E041-#4", "E041", "11.1%"),
 ("DS-E041-#20", "E041", "inventory destocking"), ("DS-E041-#20", "E041", "variable frequency"),

 ("DS-E049-#4", "E049", "Jones Act"), ("DS-E049-#4", "E049", "62"),
 ("DS-E057-#4", "E057", "5,949"), ("DS-E057-#4", "E057", "303.8"), ("DS-E057-#4", "E057", "3.0"),
 ("DS-E065-#4", "E065", "digital"), ("DS-E065-#4", "E065", "500"),
 ("DS-E073-#29", "E073", "two customers accounted"),

 ("OP-E001-#7", "E001", "7.2%"), ("OP-E001-#7", "E001", "Australia"),
 ("OP-E001-#8", "E001", "pricing"), ("OP-E001-#8", "E001", "increase"),
 ("OP-E009-#4", "E009", "49,500"), ("OP-E009-#4", "E009", "fair value"),
 ("OP-E009-#7", "E009", "124"), ("OP-E009-#7", "E009", "DUC"),
 ("OP-E017-#7", "E017", "764"), ("OP-E017-#7", "E017", "321"),
 ("OP-E025-#4", "E025", "86.1"), ("OP-E025-#4", "E025", "47 million"),
 ("OP-E033-#4", "E033", "Gross price"), ("OP-E033-#4", "E033", "rebates"),
 ("OP-E041-#13", "E041", "38.8"), ("OP-E041-#13", "E041", "40"),
 ("OP-E041-#15", "E041", "Additions to property"),
 ("OP-E049-#7", "E049", "524"), ("OP-E049-#7", "E049", "signal_q_end"),
 ("OP-E057-#29", "E057", "hedge"), ("OP-E057-#29", "E057", "derivative"),
 ("OP-E073-#13", "E073", "two customers accounted"),
 ("OP-E073-#15", "E073", "Incal"),
]

lines = []
last = None
for tag, e, q in Q:
    if tag != last:
        lines.append("\n" + "#" * 6 + " " + tag)
        last = tag
    r = search(e, q)
    lines.append("  Q[%s] <<%s>> hits=%d" % (e, q, len(r)))
    for a, b in r[:4]:
        lines.append("     @%s | %s" % (a, b[:300]))
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", OUT, len(lines))
