# -*- coding: utf-8 -*-
"""由 roster_v1.py + chain_membership_v1.csv 生成 chain_stories_v1.md。
文件與表永遠同步:改表要重跑本檔。"""
import csv, json, os, sys

ROOT = r"C:\projects\Karst"
EXP = os.path.join(ROOT, "experiments", "2026-09-02-chain-layers")
SCRATCH = (r"C:\Users\Kaho\AppData\Local\Temp\claude\C--projects-Karst"
           r"\d2e5d32d-fb0a-455e-a4f0-b5414e1a7c69\scratchpad")
sys.path.insert(0, EXP)
from roster_v1 import CHAINS

rows = list(csv.DictReader(open(os.path.join(EXP, "chain_membership_v1.csv"),
                                encoding="utf-8-sig")))
S = json.load(open(os.path.join(SCRATCH, "v1_summary.json"), encoding="utf-8"))

n_all = len(rows)
n_v1 = sum(1 for r in rows if r["added_by"] == "v1")
n_appr = sum(1 for r in rows if "近似" in r["valid_from_basis"])
n_exact = sum(1 for r in rows if "精確" in r["valid_from_basis"])
n_ev = S["evidence_hit"]
n_20f = S["evidence_none"]
foreign = sorted(t for t, _ in S["foreign"])

CN = {"v0": "v0", "v1": "v1"}
o = []
w = o.append

w("# 鏈層人手表 v1 —— 逐鏈故事與成員(KARST-159 交審稿)")
w("")
w("> 2026-09-02 由 agent 主編(用戶裁決 D-143 ①:「I think it is ok if doable. But I think you can "
  "web research to purpose」/「Approximate may twist the performance. But the overall trend should hold」)。")
w("> **這份表未經用戶審核,不是正本。** 正本待用戶審後由後續票落定。")
w("")
w("## 誠實聲明(三項,先講清楚才看表)")
w("")
w("**一、這張表是事後編的,量到的解析度一定偏高。**")
w("編表的人(我)知道 2022 至 2026 年這幾條故事後來怎樣走——量子股 2024 年炒起、AI 電力樽頸 2025 年才成為"
  "市場共識、加密礦商 2025 年集體轉做 AI 託管。把今日才看得清的分組拿去量 2022 年的同步度,量到的很可能是"
  "「今日的我們知道當年誰跟誰一齊郁」,不是「當年可以事前分得出」。這兩件事答的問題不同。"
  "用戶已接受這個代價,但代價要寫在表上:**任何用這張表得出的成績,都不能當成可以事前複製的成績。**"
  "研究文件 v2 第七節第 2 點已經記名了對治方法(用只看切片日之前的資訊重建同一張表再量一次),那是下一張票的事。")
w("")
w(f"**二、來源品質未經核數。** 成員的位置與故事來自三處:舊倉 ADR-0039 §三之二的四格判詞(質量最高,"
  f"但它本身也是人手判斷,沒有做過統計量度)、本倉機器/語意分層的實測層(layers_v2.csv,有數但只是聚類結果)、"
  f"以及我自己按公開資料的判斷(最弱的一環)。每家的 `source_url` 一律指向該公司在 SEC EDGAR 的最近一份年報,"
  f"`evidence_10k` 是由年報全文快取抽出的一句原文——這兩欄是可以逐家覆核的;"
  f"**但「這家公司屬於這條鏈」這個判斷本身,沒有任何外部來源背書。**"
  f"年報佐證覆蓋 {n_ev}/{n_all} 行({100*n_ev/n_all:.1f}%);"
  f"其餘 {n_20f} 行是外國申報人(20-F/40-F),按票面規定以 `source_url` 代替,名單見文末。")
w("")
w(f"**三、`valid_from` 近似比例:{n_appr}/{n_all} 行({100*n_appr/n_all:.1f}%)標記為近似。**")
w(f"分開看更誠實:v0 原有 {n_all-n_v1} 行沿用舊倉鎖死的日期,一字未改;"
  f"v1 新增 {n_v1} 行之中,只有 {n_exact} 家查到明確的入位事件日(分拆完成日、合併完成日、上市日),"
  f"其餘 {n_appr} 家是近似——**即 v1 新增成員的 {100*n_appr/n_v1:.0f}% 入位日不精確**。近似分兩種:"
  f"2022-01-01 之前已上市而業務未變的,一律填 2022-01-01(沿用 v0 走廊起點);"
  f"2022 年之後才有 SEC 申報紀錄的,填 EDGAR 首次申報日代替上市日。"
  f"**這一欄目前撐不起需要準確入位日的測試**(例如事件研究、或者按入位日切樣本);"
  f"要做那種測試,先補這一欄。")
w("")
w("---")
w("")
w("## 這張表怎樣砌出來")
w("")
w("- **骨幹不動**:v0 的 33 條鏈、143 行原樣保留,`theme`/`ticker`/`valid_from`/`valid_to`/`role`/`note` "
  "六欄一字不改(已機械核對,零差異)。新增欄只是加在後面。")
w("- **同鏈位 = 同上下游位置 + 同故事**(CONTEXT.md「鏈層」,用戶 2026-09-02 原話)。"
  "所以不同位置一律分開成兩條鏈,不塞入同一條——本次因此新開了 19 條鏈,"
  "當中好幾條就是 v0 自己寫明「出隊後應該去哪裡」但一直沒有開的那些"
  "(實體賭場、線上旅遊平台、公用事業級太陽能、鑽機承包商)。")
w("- **純 ETF 不入;美國上市 ADR 可入。**")
w("- 每條鏈的 `position` 與 `story` 盡量直接引用舊倉 ADR-0039 §三之二的"
  "「賣什麼 · 賣給誰 · 售價由什麼決定 · 實體樽頸」四格,而不是我自己另起爐灶。")
w("")
w("### 一句話總帳")
w("")
w("| | 數 |")
w("|---|---:|")
w(f"| 鏈數(v0 骨幹 / v1 新開) | **{S['chains_total']}**({S['chains_v0']} / {S['chains_v1']}) |")
w(f"| 成員行數(v0 原行 / v1 新增) | **{n_all}**({n_all-n_v1} / {n_v1}) |")
w(f"| 不重覆公司數 | **{S['unique_tickers']}** |")
w(f"| 票面目標 | ≥170 家 → 已達 |")
w(f"| 名冊 <5 家的鏈 | {len(S['under5_roster'])} 條:{'、'.join(S['under5_roster'])} |")
w(f"| 年報佐證覆蓋 | {n_ev}/{n_all}({100*n_ev/n_all:.1f}%) |")
w(f"| valid_from 近似 | {n_appr}/{n_all}({100*n_appr/n_all:.1f}%) |")
w("")
w("### 我要用戶特別看的三件事")
w("")
w("1. **有四條鏈補不到五家,而且是結構性補不到,不是我找漏。**"
  "記憶體(三星、海力士不在美股)、減肥藥(全球只有兩間有在售 GLP-1 產品)、"
  "光元件(美股純光元件商只剩三間)、獨立發電商(美股 merchant 發電商本來就四間)。"
  "舊倉 ADR-0039 §4.8 已經逐條寫過同一組理由。**「補不到」本身就是一個發現:"
  "這幾條鏈在美股沒有足夠的可比公司,所以它們永遠量不出統計上顯著的層內同步度**,"
  "不是分層方法不好。")
w("2. **有三條 v0 鏈,成員根本不是同一個位置**——staples 把品牌製造商(PG/KO,提價方)"
  "與大型零售商(WMT/COST,壓價方)混在一起;web3_crypto 把交易所、國庫持幣公司與礦工混在一起;"
  "china 的唯一共通點是政策風險,不是上下游位置。按用戶的定義它們不合格。"
  "我沒有改動 v0 原行(票面規定),但在表上明確標示了,並建議 v2 拆開。")
w("3. **我放寬了一條舊倉的規矩,要用戶知道。** 舊倉 ADR-0039 用「代表性測試」剔走了銅礦的 "
  "HBM/ERO/TGB,理由是「一間得一兩個礦嘅初級礦商,佢電話會講嘅係佢嗰個礦,唔係銅市」。"
  "那條測試是為了挑**可以落注的代表**而設的;這張表要答的是**誰坐在同一個鏈位**,"
  "兩件事的門檻不同,所以我把它們收了進來,並在表上標示了這個分歧。同樣道理,"
  "化肥的 ICL/LXU 當年被擋是因為缺 2021-12-01 的市值數據(排市值才需要),鏈位歸屬不需要,所以補得入。")
w("")
w("---")
w("")
w("## 逐鏈:故事、位置、成員")
w("")
w("欄位讀法:**位置**=在產業鏈上的哪一節;**故事**=同一則什麼消息會把這群公司打同一個方向;"
  "**依據**=這條鏈的定性出處;成員表的「來源」欄 v0=舊倉骨幹、v1=本次新增。")
w("")


def block(themes, title, note=None):
    w(f"### {title}")
    w("")
    if note:
        w(note)
        w("")
    for th in themes:
        c = CHAINS[th]
        st = S["stats"][th]
        rs = [r for r in rows if r["theme"] == th]
        tag = " `v1 新開`" if c["new"] else ""
        w(f"#### `{th}`{tag} —— 名冊 {st['roster']} 家 / 現役 {st['active']} 家")
        w("")
        w(f"- **位置**:{c['position']}")
        w(f"- **故事**:{c['story']}")
        w(f"- **依據**:{c['src']}")
        if c["short"]:
            w(f"- **⚠️ 要留意**:{c['short']}")
        w("")
        w("| 代碼 | 來源 | valid_from | 入位日依據 | 狀態 | 說明 |")
        w("|---|---|---|---|---|---|")
        for r in rs:
            state = f"已剔除 {r['valid_to']}" if r["valid_to"] else "現役"
            note_txt = (r["note"] or "").replace("|", "/").replace("\n", " ")
            if len(note_txt) > 70:
                note_txt = note_txt[:70] + "…"
            basis = r["valid_from_basis"]
            basis = ("精確" if "精確" in basis else "近似" if "近似" in basis else "沿用 v0")
            w(f"| {r['ticker']} | {r['added_by']} | {r['valid_from']} | {basis} | {state} | {note_txt} |")
        w("")


v0_ok = [t for t in CHAINS if not CHAINS[t]["new"] and t not in S["under5_roster"]]
v0_short = [t for t in CHAINS if not CHAINS[t]["new"] and t in S["under5_roster"]]
v1_new = [t for t in CHAINS if CHAINS[t]["new"]]

block(v0_ok, "甲、v0 骨幹鏈(名冊已達五家)")
block(v0_short, "乙、v0 骨幹鏈(名冊不足五家,結構性)",
      "這四條每一條都寫明了為什麼補不到——不是找漏,是美股本來就沒有那麼多同位置同故事的公司。")
block(v1_new, "丙、v1 新開鏈",
      "新開的準則有三種:①v0 自己寫明某家「出隊後應該去哪裡」但一直沒有開那條鏈(實體賭場、線上旅遊平台、"
      "公用事業級太陽能);②本倉機器與語意分層兩種方法都獨立找到同一組公司(航空、鐵路、管理式醫療、"
      "保險經紀、二手車、加密礦、餐飲、折扣零售);③按 D-129 的由上而下框架,一條產業鏈缺了買家一端"
      "或某個關鍵節點就串不起來(超大規模雲廠、資料中心電力設備、煉油、中游管道、純天然氣上游、鑽機承包商)。")

w("---")
w("")
w("## 外國申報人名單(無 10-K 快取,以 source_url 代替)")
w("")
w(f"共 {len(foreign)} 家,申報 20-F(外國私人發行人)或 40-F(加拿大 MJDS)。"
  f"票面規定這批不抓年報全文,`evidence_10k` 留空,`source_url` 指向其 EDGAR 最近一份年報:")
w("")
w("`" + " ".join(foreign) + "`")
w("")
w("---")
w("")
w("## 檔案")
w("")
w("- `chain_membership_v1.csv` —— 本表(UTF-8 BOM,與 v0 同編碼)")
w("- `chain_membership_v0.csv` —— 舊倉骨幹,唯讀,未改一字")
w("- `roster_v1.py` —— 逐鏈的位置、故事、依據、補員名單(本文件的來源)")
w("- `build_v1.py` —— 建表腳本(EDGAR 查證、年報快取、佐證抽取)")
w("- `gen_doc_v1.py` —— 本文件的生成腳本")
w("- 年報全文:`data/sec/10k_text/`(D-134 共用快取),本票新增 46 份,見 `manifest.jsonl` "
  "的 `fetchedBy: KARST-159`")
w("")
w("出處檔(舊倉,唯讀):`docs/adr/0039-representative-rule-and-layer-freeze.md`、"
  "`bt/exp9_full_reader/results/chain_audit_proposal.md`")

open(os.path.join(EXP, "chain_stories_v1.md"), "w", encoding="utf-8").write("\n".join(o) + "\n")
print("chain_stories_v1.md 已寫出,", len(o), "行")
