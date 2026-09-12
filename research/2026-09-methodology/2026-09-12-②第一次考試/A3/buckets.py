# -*- coding: utf-8 -*-
"""KARST-222 票 A:六個行業桶對應表(SIC 兩位數合成;互斥、無重疊、次序固定)。

執行口徑 v1 只寫「SIC 兩位數合成六桶」,沒有給對應表;本檔就是那張表,兩支腳本共用,
並原樣抄進 `picks_before_results.md`。分不出的一律入「其他」。
"""

# 逐桶列出 SIC 兩位數(不含重複;六桶加「其他」覆蓋 00–99 全部)
BUCKETS: dict[str, list[str]] = {
    "能源原材料公用": [f"{i:02d}" for i in list(range(1, 15)) + [29]
                       + list(range(40, 48)) + [49]],
    "醫療": ["28", "38", "80", "81"],
    "科技與軟件": ["36", "48", "73", "87"],
    "金融地產": [f"{i:02d}" for i in range(60, 70)],
    "消費與零售": ["20", "21", "22", "23"] + [f"{i:02d}" for i in range(52, 60)]
                  + ["70", "72", "78", "79"],
    "製造與工業": ["15", "16", "17", "24", "25", "26", "27"] + [f"{i:02d}" for i in range(30, 36)]
                  + ["37", "39", "50", "51"],
}
BUCKET_ORDER = ["能源原材料公用", "醫療", "科技與軟件", "金融地產", "消費與零售", "製造與工業"]

_MAP = {s: b for b, lst in BUCKETS.items() for s in lst}
assert len(_MAP) == sum(len(v) for v in BUCKETS.values()), "六桶對應表有重疊"


def bucket_of(sic2) -> str:
    return _MAP.get(str(sic2).zfill(2)[:2], "其他")


def bucket_table_md() -> str:
    lines = ["| 桶 | SIC 兩位數 |", "|---|---|"]
    for b in BUCKET_ORDER:
        lines.append("| %s | %s |" % (b, "、".join(BUCKETS[b])))
    lines.append("| 其他 | 其餘(未列於上表者) |")
    return "\n".join(lines)
