"""KARST-152 收工:改寫 A-037 的狀態,並開 A-038 承接未證的那一半。"""
from __future__ import annotations

import json
from pathlib import Path

P = Path(r"C:\projects\Karst\.kira\assumptions.jsonl")

REASON = (
    "KARST-152 按跑數前凍結的判準(experiments/2026-09-02-narrative-layers/CRITERIA.md,"
    "commit 0aa236d)檢驗:用按申報日定格的 10-K Item 1 業務描述做 TF-IDF 機器分層,"
    "三個切片(2015/2019/2023-06-30)× 三個層數(k=40/60/80)共九格,"
    "「同敘事層不同 GICS 子行業」的殘餘回報相關(0.023–0.038)全部顯著**低於**"
    "「同子行業不同層」(0.112–0.179),G1−G2 由 −0.081 至 −0.166,"
    "以層為抽樣單位的 cluster bootstrap 95% 置信區間九格全部不含零。"
    "即不是「量不出」,是反方向決定性地不成立。"
    "但推翻的範圍只到「機器讀年報自動分故事」這一版做法,不是「故事分層無用」這個命題:"
    "(a)同層又同子行業(G3=0.18–0.21)穩定高過同子行業(G2),即文本有資訊,是 GICS 的補充;"
    "(b)把層按大小拆開(事後診斷),3–25 家的細層平均層內殘餘相關 0.154/0.138/0.240,"
    "三個切片全部高過 GICS 基準,而且是認得出的真故事(2019 年郵輪+賭場酒店+租車+網上訂房一層 0.434);"
    "輸在半數以上公司被平均連結聚類掃進大雜燴層(2023 k=40 最大一層 365/510 家),層內只有 0.05;"
    "(c)舊倉 98 家人手表方向相反且是用戶那一邊(同鏈位 0.168 對同子行業 0.083),"
    "但只得 63 家可入數、30 對與 24 對配對,置信區間 [−0.044, +0.246] 跨零,證不到。"
    "承接未證的那一半見 A-038。"
)

NEW = {
    "id": "A-038",
    "text": (
        "承接 A-037 被推翻之後剩低未證的那一半(KARST-152 收檔時立):"
        "人手建立的敘事鏈層(舊倉 98 家表那種:同上下游位置、同故事),"
        "其同層殘餘回報相關高於同 GICS 子行業。現有證據偏向成立但證不到——"
        "同鏈位 0.168 對同子行業 0.083(2022-01 至 2026-08),方向與量級都是用戶那一邊,"
        "但 98 家代表只有 63 家在標普宇宙內有日線,配對得 30 對與 24 對,"
        "bootstrap 置信區間 [−0.044, +0.246] 跨零。"
        "同一批數的事後診斷顯示人手鏈位的等效獨立數 3.08,對比同期九隻板塊 ETF 的 1.79,"
        "是三個切片之中唯一一個明顯超出板塊層的解析度(機器分層只有 1.2–2.9 對 1.2–2.0)。"
        "若它是假,價值鏈層作為由上而下第二層就沒有 GICS 以外的解析度,"
        "KARST-149/151 及一切鏈上假設要另找單位;若它是真,第二層成立,"
        "但要靠人手或語意模型分層,不能靠 TF-IDF。"
        "查證方向(三項按重要程度):①宇宙擴到標普成份股以外——"
        "用戶想要的鏈層(量子、鈾、加密礦、GLP-1)大部分不在 574 家內,"
        "人手表 35 家代表因此入不到數,而缺席那批正正是最純的主題股,"
        "宇宙不對就連對象都不在樣本裡面,改幾多次演算法都沒有用;"
        "②改用語意 embedding 而非 TF-IDF(捉故事不捉用詞);"
        "③改用容許「無層」的聚類(如 HDBSCAN),不要強行把每家公司塞進一層。"
    ),
    "brief": "人手敘事鏈層的同層殘餘相關高於同 GICS 子行業(現有證據方向對但樣本不足);若假,價值鏈層無解析度優勢",
    "status": "unverified",
    "createdAt": "2026-09-02",
    "source": "KARST-152 / A-037",
    "verifiedAt": None,
}


def main() -> int:
    lines = P.read_text(encoding="utf-8").splitlines()
    out = []
    hit = False
    for ln in lines:
        if not ln.strip():
            continue
        d = json.loads(ln)
        if d.get("id") == "A-037":
            hit = True
            d["status"] = "overturned"
            d["overturnedAt"] = "2026-09-02"
            d["overturnedBy"] = "KARST-152"
            d["overturnedReason"] = REASON
            d["brief"] = (
                "機器讀 10-K 自動分敘事層被推翻:同層不同子行業的殘餘相關(0.02–0.04)"
                "反而顯著低於同子行業不同層(0.11–0.18),九格全部同方向;"
                "但只推翻這一版做法,人手分層方向相反卻證不到,承接見 A-038"
            )
        out.append(json.dumps(d, ensure_ascii=False))
    if not hit:
        raise SystemExit("A-037 not found")
    if not any('"A-038"' in x for x in out):
        out.append(json.dumps(NEW, ensure_ascii=False))
    P.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("A-037 -> overturned; A-038 added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
