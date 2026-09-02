# -*- coding: utf-8 -*-
"""KARST-161 由 chain_membership_v2.csv + roster_v2.py 生成 chain_stories_v2.md。"""
import csv, io, json, os, sys

ROOT = r"C:\projects\Karst"
EXP = os.path.join(ROOT, "experiments", "2026-09-02-chain-layers")
SCRATCH = (r"C:\Users\Kaho\AppData\Local\Temp\claude\C--projects-Karst"
           r"\d2e5d32d-fb0a-455e-a4f0-b5414e1a7c69\scratchpad")
sys.path.insert(0, EXP)
from roster_v2 import CHAINS, REMOVED

S = json.load(open(os.path.join(SCRATCH, "v2_summary.json"), encoding="utf-8"))
# 本票抓過的年報由 manifest 反查(重跑 build_v2 時快取已有,summary 的 fetched 會空)
MANIFEST = os.path.join(ROOT, "data", "sec", "10k_text", "manifest.jsonl")
_f = []
with io.open(MANIFEST, encoding="utf-8") as _fh:
    for _ln in _fh:
        _ln = _ln.strip()
        if _ln and '"chain-purity-161"' in _ln:
            _f.append(json.loads(_ln)["ticker"])
S["fetched"] = sorted(set(_f))
rows = list(csv.DictReader(io.open(os.path.join(EXP, "chain_membership_v2.csv"),
                                   encoding="utf-8-sig")))
rm = list(csv.DictReader(io.open(os.path.join(EXP, "removed_v2.csv"),
                                 encoding="utf-8-sig")))
V1_THEMES = set(S["chains_v1_retired"]) | set(
    t for t in CHAINS if not CHAINS[t]["new"])
NEW_NAMES = [t for t in CHAINS if t not in
             (set(CHAINS) - set(S["chains_v1_retired"]))]  # 佔位,下面另算

# 由 v1 檔取回原本的鏈名集合
v1rows = list(csv.DictReader(io.open(os.path.join(EXP, "chain_membership_v1.csv"),
                                     encoding="utf-8-sig")))
V1SET = set(r["theme"] for r in v1rows)
NEW_NAMES = [t for t in CHAINS if t not in V1SET]
KEPT_NAMES = [t for t in CHAINS if t in V1SET]

L = []
w = L.append

w("# 鏈層人手表 v2 —— 純度版(KARST-161 交審稿)")
w("")
w("> 2026-09-03 由 agent 編製。用戶裁決 D-147 ③(原話):"
  "「Yes, I dont care how much you add, but the purity of the layer is the highest "
  "priority. The company in the same layer should share the same narrative」。")
w("> **這份表未經用戶審核,不是正本。** v1 檔(`chain_membership_v1.csv`、"
  "`chain_stories_v1.md`)一字未改,仍在原處。")
w("")
w("## 誠實聲明(四項,先講清楚才看表)")
w("")
w("**一、這張表是事後編的,量到的解析度一定偏高。**")
w("編表的人知道 2022 至 2026 年這幾條故事後來怎樣走——量子股 2024 年炒起、AI 電力樽頸 2025 年才成為"
  "市場共識、加密礦商 2025 年集體轉做 AI 託管。把今日才看得清的分組拿去量 2022 年的同步度,量到的"
  "很可能是「今日的我們知道當年誰跟誰一齊郁」,不是「當年可以事前分得出」。**任何用這張表得出的成績,"
  "都不能當成可以事前複製的成績。**v2 比 v1 更受這一條影響:本次的拆鏈(例如把已轉型 AI 託管的礦商"
  "拆出來)正正用了 2025 年才明朗的資訊。")
w("")
w("**二、來源品質未經核數。** 成員的位置與故事來自三處:舊倉 ADR-0039 §三之二的四格判詞(質量最高,"
  "但它本身也是人手判斷,沒有做過統計量度)、本倉機器/語意分層的實測層、以及編表人按公開資料的判斷"
  "(最弱的一環)。每家的 `source_url` 指向該公司在 SEC EDGAR 的最近一份年報,`evidence_10k` 是由年報"
  "全文快取抽出的一句原文——這兩欄可以逐家覆核;**但「這家公司屬於這條鏈」這個判斷本身,沒有任何"
  "外部來源背書。**")
w("")
w(f"**三、`valid_from` 近似比例:{S['valid_from_approx']}/{S['rows']} 行"
  f"({S['valid_from_approx_pct']}%)標記為近似。**")
w("v0 原有的行沿用舊倉鎖死的日期,一字未改;v1 與 v2 新增的成員絕大多數是近似(2022-01-01 前已上市"
  "而業務未變的填 2022-01-01;之後才有 SEC 申報紀錄的填 EDGAR 首次申報日)。**這一欄目前撐不起需要"
  "準確入位日的測試**(事件研究、按入位日切樣本)。crypto_treasury 那五家的入位日尤其粗:填的是公開"
  "宣布國庫策略的月份,沒有逐日核對。")
w("")
w("**四、純度判斷是人手判斷,沒有統計量度背書。**")
w("本票對 347 行逐家問了同一句:「這家公司的股價,主要跟這條鏈的共同敘事走,還是跟它自己的故事走?」"
  "答案全部由編表人按公開資料判斷,**沒有做過任何相關係數、事件日回報或同步度量度**。所以本文件"
  "只出事實陳述(存在 / 不存在 / 量不出),不出成績,亦不寫「及格」。要驗證這些分組真的同步,是"
  "後續量法票的事。另外要講明一件實作上的事:**每一行都有一句 purity 判斷,但當中大部分是該鏈的"
  "共同判斷句**(「股價跟某條敘事走」),只有需要另外交代的成員才有自己那一句;逐家獨立寫的那批,"
  "在下面每條鏈的成員表最右欄看得到。")
w("")
w("---")
w("")
w("## 出隊規則(v2 統一用這四條)")
w("")
w("用戶那一句話落地成一個可以逐家問的問題之後,出隊只有四個理由。每一家出隊的公司,在 "
  "`removed_v2.csv` 都寫明中了哪一條。")
w("")
w("| 規則 | 名稱 | 意思 |")
w("|---|---|---|")
w("| a | 位置不同 | 它在鏈上的位置與其餘成員不同(買方對賣方、製造對零售、持牌對輕資產) |")
w("| b | 定價機制不同 | 決定它售價的那個變數,與其餘成員不同 |")
w("| c | 單一資產主導 | 股價主要由一項自有資產或一宗自有事件驅動(舊倉 ADR-0039 的代表性測試) |")
w("| d | 主業已轉向 | 主要股價驅動已轉去另一條鏈;多元業務只入其股價主要跟隨的那條 |")
w("")
w("規則 c 是 D-147 ③ 明文收回來的:主 agent 在 D-146 ③ 曾主張把「只講自己那個礦」的初級銅礦商收回"
  "名冊(門檻放寬為「同鏈位」),用戶裁決之後那個立場已撤回,門檻收緊為**同鏈位且同敘事**。")
w("")
w("---")
w("")
w("## 一句話總帳")
w("")
w("| | v1 | v2 |")
w("|---|---:|---:|")
w(f"| 鏈數 | 52 | **{S['chains_total']}** |")
w(f"| 成員行數 | 309 | **{S['rows']}** |")
w(f"| 不重覆公司數 | 298 | **{S['unique_tickers']}** |")
w(f"| 名冊 <5 家的鏈 | 4 | **{len(S['under5_roster'])}** |")
w(f"| 年報佐證覆蓋 | 273/309(88.3%) | **{S['evidence_hit']}/{S['rows']}"
  f"({round(100*S['evidence_hit']/S['rows'],1)}%)** |")
w(f"| valid_from 近似 | 50.8% | **{S['valid_from_approx_pct']}%** |")
w("")
w(f"- **拆散的 v1 鏈({len(S['chains_v1_retired'])} 條)**:"
  + "、".join(f"`{t}`" for t in S["chains_v1_retired"]))
w(f"- **v2 新出現的鏈名({len(NEW_NAMES)} 條)**:"
  + "、".join(f"`{t}`" for t in NEW_NAMES))
w(f"- **出隊({len(rm)} 行)**:見 `removed_v2.csv`,逐行一句理由。")
w(f"- **新增成員({S['rows_v2']} 行)**:全部由 v2 補入,`added_by=v2`。")
w("")
w("### 三條奉命拆開的鏈,拆成了什麼")
w("")
w("| v1 鏈 | 拆成 | 為什麼 |")
w("|---|---|---|")
w("| `staples` | `staples_brand` / `staples_retail` | 品牌廠靠提價,零售商靠壓價;"
  "同一則成本上升消息,一邊是成本、一邊是議價籌碼,方向相反 |")
w("| `web3_crypto` | `crypto_exchange` / `crypto_treasury` / 礦工併入 `crypto_mining` | "
  "交易所收入跟交易量走、國庫公司股價跟持幣量乘幣價走、礦工收入跟幣價除電價走——三個機制 |")
w("| `china` | `china_ecommerce` / `china_online_content` / `china_education`(新開);"
  "`BIDU` 出隊 | 舊鏈唯一共通點是政策風險而不是上下游位置;拆完之後每一條有自己的收入方程式 |")
w("")
w("礦工那一節按票面「合併去 crypto_mining 或保留一條,寫明理由」處理:**合併**。理由是 v1 的 "
  "`crypto_mining` 已經是同一個位置同一個故事,再開一條純礦鏈只會把樣本切細;但同時發現 v1 的 "
  "`crypto_mining` 自己不純——六家之中四家(CORZ / IREN / WULF / CIFR)自 2024 年起股價已改為跟 AI "
  "託管租約走,按規則 d 另立 `ai_hpc_hosting`。")
w("")
w("### 額外拆開的鏈(v1 自己已標示、或本次覆核發現)")
w("")
w("| v1 鏈 | 拆成 | 為什麼 |")
w("|---|---|---|")
w("| `uranium_power` | `uranium_mining` / `uranium_enrichment`;三家公用事業出隊 | "
  "礦商賣鈾精礦、濃縮商賣分離功,兩個售價機制;公用事業是買家 |")
w("| `streaming` | `streaming_content` / `ctv_adtech`;`SPOT` 出隊 | "
  "自有內容商賣訂閱、廣告平台賣曝光 |")
w("| `fintech` | `alt_lending` / `payments`;`HOOD` 併去 `crypto_exchange` | "
  "信貸商賺息差減撇賬、收單商賺交易費率,兩者的開關不同 |")
w("| `ev` | `ev_us` / `china_ev` | 美國稅務抵免消息打不到中國廠,中國以舊換新補貼消息打不到美國廠 |")
w("| `casino_resorts` | `casino_us_regional` / `casino_macau` | "
  "澳門月度博彩毛收入與中國訪客政策,對美國本土賭場毫無影響 |")
w("| `ag_fertilizer` | `ag_potash_phosphate` / `ag_nitrogen` | "
  "鉀磷看礦山供給、氮看天然氣邊際成本——舊倉自己那一格判詞已經寫住兩個機制 |")
w("| `auto_retail` | 分出 `auto_aftermarket`;`CPRT` 出隊 | "
  "售後零件的需求是在路車齡(反週期),與二手車零售價相反 |")
w("| `crypto_mining` | 分出 `ai_hpc_hosting` | 見上 |")
w("")
w("`aero_aftermarket` 是唯一一條沒有任何 v1 成員的新鏈:它補回 `airlines` 的上游缺口"
  "(收入跟全球飛行小時走)。`china_education` 同樣沒有 v1 成員,是按票面 ① 明文列出的拆法開的。")
w("")
w("---")
w("")
w("## 我要用戶特別看的四件事")
w("")
w("1. **純度收緊之後,`copper` 由八家縮到三家。**這是 D-147 ③ 最直接的後果:三家初級銅礦商"
  "(HBM / ERO / TGB)按規則 c 出隊(舊倉原話是它們的電話會議講的是自己那個礦,不是銅市),"
  "兩家多元化礦商(BHP / RIO)按規則 d 出隊(股價跟鐵礦石與中國鋼鐵走)。餘下 FCX / SCCO / TECK 三家,"
  "**這條鏈從此永遠量不出統計上顯著的層內同步度**。純度與可量度性在這一條上直接相撞,撞出來的結果"
  "是純度贏。")
w("2. **同一件事在 `ag_fertilizer` 再發生一次:拆完之後兩邊都不足五家**(鉀磷四家、氮肥三家)。"
  "如果用戶要的是「可以量」,這一條應該不拆;要的是「純」,就應該拆。我按 D-147 ③ 拆了,但這是"
  "一個可以推翻的選擇,推翻它不用改任何其他判斷。")
w(f"3. **名冊不足五家的鏈由 4 條升到 {len(S['under5_roster'])} 條。**每一條都寫明了是結構性補不到"
  "還是純度收緊的代價。這批鏈**永遠量不出顯著的層內同步度**,只能作候選池成員,不入任何統計判準"
  "(D-146 ① 已定,用戶未反對)。")
w("4. **`banks` 與 `datacenter_power` 兩條,我判了「留」而不是「拆」,理由要用戶知道。**"
  "GS / MS 的收入結構偏交易與財富管理而不是淨利息收入(規則 b 的邊緣個案);PWR 賣的是工程不是設備"
  "(規則 a 的邊緣個案)。兩處我都按用戶那一句的問法判——**它們的股價確實跟該鏈的共同敘事走**——"
  "所以留,並在成員表標明。用戶若認為位置不同就應該拆,這兩條改起來不影響其他鏈。")
w("")
w("---")
w("")
w("## 逐鏈:故事、位置、純度、成員")
w("")
w("欄位讀法:**位置**=在產業鏈上的哪一節;**故事**=同一則什麼消息會把這群公司打同一個方向;"
  "**純度**=這條鏈的共同敘事是什麼、哪家最邊緣;成員表「來源」欄 v0=舊倉骨幹、v1=KARST-159 新增、"
  "v2=本票新增,「由」欄=它在 v1 屬於哪一條鏈。")
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
        tag = " `v2 新開`" if th not in V1SET else ""
        w(f"#### `{th}`{tag} —— 名冊 {st['roster']} 家 / 現役 {st['active']} 家")
        w("")
        w(f"- **位置**:{c['position']}")
        w(f"- **故事**:{c['story']}")
        w(f"- **純度**:{c['purity_note']}")
        if c["short"]:
            w(f"- **⚠️ 補不到五家**:{c['short']}")
        w("")
        w("| 代碼 | 來源 | 由 | valid_from | 入位日 | 狀態 | purity 判斷 |")
        w("|---|---|---|---|---|---|---|")
        for r in rs:
            state = f"已剔除 {r['valid_to']}" if r["valid_to"] else "現役"
            basis = r["valid_from_basis"]
            basis = ("精確" if "精確" in basis else "近似" if "近似" in basis else "沿用 v0")
            frm = r["src_theme_v1"] or "—"
            pur = r["purity"].replace("|", "/")
            w(f"| {r['ticker']} | {r['added_by']} | `{frm}` | {r['valid_from']} | "
              f"{basis} | {state} | {pur} |")
        w("")


split_out = [t for t in CHAINS if CHAINS[t]["src"] in S["chains_v1_retired"]
             or t in ("crypto_mining", "ai_hpc_hosting", "uranium_mining",
                      "uranium_enrichment", "streaming_content", "ctv_adtech",
                      "auto_retail", "auto_aftermarket")]
brand_new = [t for t in CHAINS if CHAINS[t]["src"] is None]
untouched = [t for t in CHAINS if t not in split_out and t not in brand_new]

block(split_out, "甲、由 v1 鏈拆出來的鏈",
      "這一批是本票的主體:每一條的成員都由某條 v1 鏈搬過來,搬的理由寫在上面的拆鏈表。")
block(untouched, "乙、原名保留、只做純度覆核的鏈",
      "這一批沒有拆,但逐家問過同一條問題;有成員出隊的,理由在 `removed_v2.csv`。")
block(brand_new, "丙、v2 全新開的鏈(沒有任何 v1 成員)",
      "只有兩條,而且都寫明了為什麼要開。")

w("---")
w("")
w("## 出隊名單")
w("")
w(f"共 {len(rm)} 行。逐行的完整理由在 `removed_v2.csv`。")
w("")
w("| v1 鏈 | 代碼 | 規則 | 理由 |")
w("|---|---|---|---|")
for r in rm:
    w(f"| `{r['v1_theme']}` | {r['ticker']} | {r['rule']} {r['rule_name']} | "
      f"{r['reason'].replace('|', '/')} |")
w("")
w("---")
w("")
w("## 年報佐證與外國申報人")
w("")
w(f"- 有年報原文佐證:**{S['evidence_hit']}/{S['rows']} 行"
  f"({round(100*S['evidence_hit']/S['rows'],1)}%)**")
w(f"- 本票新增抓取:**{len(S['fetched'])} 份**(`fetchedBy: chain-purity-161`),"
  "全部先查 `manifest.jsonl` 再抓,已有的不重抓;抓取失敗 0")
w(f"- 無佐證:{len(S['evidence_none'])} 家,全部是申報 20-F(外國私人發行人)或 40-F"
  "(加拿大 MJDS)的公司,票面規定不抓全文,以 `source_url` 代替")
w("")
if S["fetched"]:
    w("本票新增的年報:")
    w("")
    w("`" + " ".join(S["fetched"]) + "`")
    w("")
w("無 10-K 佐證的公司:")
w("")
w("`" + " ".join(S["evidence_none"]) + "`")
w("")
w("---")
w("")
w("## 檔案")
w("")
w("- `chain_membership_v2.csv` —— 本表(UTF-8 BOM)")
w("- `removed_v2.csv` —— 出隊名單,每行一句理由")
w("- `chain_membership_v1.csv` / `chain_stories_v1.md` —— v1,**一字未改**,仍是 KARST-159 的交審稿")
w("- `chain_membership_v0.csv` —— 舊倉骨幹,唯讀")
w("- `roster_v2.py` —— 逐鏈的位置、故事、純度判詞、成員與出隊名單(本文件的來源)")
w("- `build_v2.py` —— 建表腳本(EDGAR 查證、年報快取、佐證抽取、與 v1 逐行對帳)")
w("- `gen_doc_v2.py` —— 本文件的生成腳本")
w("- 年報全文:`data/sec/10k_text/`(D-134 共用快取),見 `manifest.jsonl` 的 "
  "`fetchedBy: chain-purity-161`")
w("")

io.open(os.path.join(EXP, "chain_stories_v2.md"), "w", encoding="utf-8").write("\n".join(L))
print("chain_stories_v2.md 已生成,", len(L), "行")
print("split_out", len(split_out), "untouched", len(untouched), "brand_new", len(brand_new))
