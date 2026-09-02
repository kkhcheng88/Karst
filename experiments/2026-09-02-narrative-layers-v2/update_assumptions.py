"""KARST-157 收工:按結果更新 .kira/assumptions.jsonl 的 A-038。

結果是「量不出」,既非 holds 亦非 overturned,故 status 維持 unverified、
verifiedAt 維持 null,只把查過什麼、查到什麼、剩下哪條路寫回去——
免得下一個人重複查同一件事,或者當它從未查過。

逐行讀寫,只動 A-038 那一行,其餘一字不改。
Run: PYTHONUTF8=1 python update_assumptions.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PATH = REPO / ".kira" / "assumptions.jsonl"

NEW_BRIEF = (
    "人手敘事鏈層的同層殘餘相關高於同 GICS 子行業(兩版證據方向都對、量級都夠,但兩版都量不出);"
    "KARST-157 已把宇宙補齊(可入數 63→102 家)、並試齊語意 embedding 與容許無層的 HDBSCAN——"
    "機器兩條路皆不成立,人手表配對仍只得 61 對過不到 100 門檻。剩下唯一的路:把人手表由每層三家擴到五六家"
)
APPEND = (
    " ——【2026-09-02 KARST-157 查證結果:仍然量不出,status 維持 unverified】"
    "①宇宙已補齊:574→728 家,人手表可入數由 63 家升到 102 家(2023-06-30 切片 103 條有效行只欠 PXD 一家,"
    "量子/鈾/加密礦/GLP-1 四條鏈全部入到數)。人手表方向與量級兩個切片都在用戶那一邊而且比上一版更強:"
    "2023-06-30 同鏈位 0.175 對同子行業 0.061(差 +0.112,置信區間 [−0.041,+0.269]);"
    "2025-06-30 為 0.232 對 0.123(差 +0.126,[−0.019,+0.266]);等效獨立層數 3.77 與 4.98,"
    "對同期九隻板塊 ETF 的 1.96 與 3.03,兩格都過 D-131 那條 +1.0 的尺。"
    "**但配對只得 61 對與 62 對,過不到凍結判準寫死的 100 對門檻,置信區間照舊跨零**,故判量不出。"
    "②③兩條查證方向已經試齊而且都不成立:語意 embedding(all-MiniLM-L6-v2)與 TF-IDF 給出幾乎同一個答案、"
    "覆蓋更低;容許無層的 HDBSCAN 確實修好了上一版的大雜燴問題(最大層 365 家收到 17–24 家),"
    "令 G1 由 0.02–0.04 升到 0.05–0.13,但三個切片仍然全負、置信區間全部跨零。"
    "另有一項不利證據:機器分層與 GICS 的調整互信息由上一版的 0.04–0.45 升到 0.61–0.65——"
    "即機器版本的改善是靠把層畫得更似 GICS 換回來的;逼所有公司入層的對照組互信息跌回 0.37–0.46,"
    "G1−G2 就即刻變回決定性地負(六格置信區間全部不含零)。"
    "**剩下唯一的查證路徑:不是再換演算法,是把人手表本身由每層三家擴到五六家**——"
    "按同一形狀推算要約 166 家成員才生得出 100 對 G1;同時要用只看切片日之前資訊的方法重建同一張表,"
    "才答得到『事前可得』(現時人手表由見過走勢的人編成,只證解析度存在)。"
    "證據:research/2026-09-02-敘事鏈層存在性v2.md;判準凍結 commit 1c4a7b5。"
)


def main() -> int:
    lines = PATH.read_text(encoding="utf-8").splitlines()
    out, hit = [], 0
    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue
        rec = json.loads(ln)
        if rec.get("id") == "A-038":
            rec["status"] = "unverified"      # 量不出:既非 holds 亦非 overturned
            rec["verifiedAt"] = None
            rec["brief"] = NEW_BRIEF
            if "KARST-157 查證結果" not in rec["text"]:
                rec["text"] = rec["text"] + APPEND
            hit += 1
            out.append(json.dumps(rec, ensure_ascii=False))
        else:
            out.append(ln)
    assert hit == 1, f"A-038 命中 {hit} 次"
    PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("A-038 -> unverified(量不出);text 已附 KARST-157 查證結果")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
