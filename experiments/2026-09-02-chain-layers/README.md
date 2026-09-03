# 鏈層第一版人手表(承接舊倉 KarstETF)

2026-09-02 由主 agent 自舊倉 `C:\projects\Investment\KarstETF\bt\exp9_full_reader\chain_membership.csv` 原檔複製,未改一字(檔首含 UTF-8 BOM,讀取時用 `encoding="utf-8-sig"`)。

## 這張表是什麼

- 舊倉 KarstETF(2026-08-15 停案)用「主題 / 鏈位 / 敘事」三層模型挑選代表公司;`theme` 欄即鏈位,33 條;`valid_to` 空白者為現役,共 98 個唯一代碼。
- 依舊倉 ADR-0039 分四類:16 條可投注鏈位(42 個代表席位)、10 條純需求型不落注、2 條退役、2 條永久剔除、1 條被部分取代(energy→upstream_oil)、1 條待裁(smr_newbuild)。
- 歸層機制:LLM 讀業務描述與分部收入做窮盡分類並附引文核對,再由分析員依四步規則(純度閘→方向測試→代表性測試→市值排序)定代表,鎖死名單。
- **同層對同一消息反應相似**這一條,舊倉只有質性「方向測試」,**從未做過統計量度**(僅一個退役個案引用過相關係數)。所以這張表是「鏈層」(CONTEXT.md)的**候選人手表**,不是已驗證的分層。

## 在 Karst 的用途

- 用戶 2026-09-02 定義:價值鏈=產業鏈,鏈分「鏈層」,同層=同位置、同故事、消息衝擊相似(D-129)。
- 本表作為鏈層第一版,供 KARST-149/151 提出量法時當作待驗證的標籤;驗證方向=同層公司事件日回報相關性是否顯著高於同 GICS 子行業但不同層的公司。
- 多數鏈位本身即一層(不再分上下游);石油鏈例外,舊倉列出 7 個潛在子層但只覆蓋上游開採與油田服務兩層。

## v1 擴編(2026-09-02,KARST-159,交審稿)

用戶裁決 D-143 ① 授權 agent 主編、可用網上資料、接受事後眼光的偏差。KARST-157 算出人手表要每鏈約五家、
約 167 家成員才夠 100 對配對;本次做到 **52 條鏈、309 行、298 家不重覆公司**。

- **正本交審文件**:`chain_stories_v1.md`(逐鏈故事、位置、成員表、來源;首段三項誠實聲明)
- **表**:`chain_membership_v1.csv`(UTF-8 BOM,與 v0 同編碼)。v0 的 143 行、六欄**一字不改**(已機械核對,零差異),
  新增 `story` / `position` / `source_url` / `evidence_10k` / `added_by` / `valid_from_basis` / `filer_type` 七欄。
- **腳本**:`roster_v1.py`(逐鏈定義與補員名單)、`build_v1.py`(EDGAR 查證、年報快取、佐證抽取)、
  `gen_doc_v1.py`(生成交審文件)。改表要重跑 `build_v1.py` 再重跑 `gen_doc_v1.py`。

### 鏈數與家數

| | 數 |
|---|---:|
| 鏈數(v0 骨幹 / v1 新開) | 52(33 / 19) |
| 成員行數(v0 原行 / v1 新增) | 309(143 / 166) |
| 不重覆公司數 | 298(票面目標 ≥170,已達) |
| 名冊 <5 家的鏈 | 4 條:`memory`(3)、`solar`(4)、`cannabis`(1)、`metaverse_innov`(2) |

名冊 <5 的四條,以及現役成員 <5 的十一條(`energy` `memory` `optical_cpo` `power_producers` `glp1`
`solar` `cannabis` `metaverse_innov` `betting` `ev` `smr_newbuild`),逐條原因寫在 `chain_stories_v1.md`
每條鏈的「⚠️ 要留意」一行。**多數是結構性補不到**——舊倉 ADR-0039 §4.8 已經逐條寫過同一組理由
(三星海力士不在美股、全球只有兩間有在售 GLP-1 產品、美股純光元件商只剩三間、merchant 發電商本來就四間)。

### 年報佐證覆蓋(D-134 共用快取)

年報全文**只入** `data/sec/10k_text/`,票內不存副本;逐行 append `manifest.jsonl`,
欄位照現有 `fetchedBy` 那一套(無 `path` 欄,檔名 = `<TICKER>_<accession>.txt.gz`)。
EDGAR 每秒 ≤10 請求,User-Agent `Casy Limited kaho.career@gmail.com`。

| | 數 |
|---|---:|
| 有年報原文佐證 | 273 / 309 行(88.3%) |
| 本票新增抓取 | 46 份(`fetchedBy: KARST-159`) |
| 無佐證(外國申報人,以 source_url 代替) | 36 行 |
| 抓取失敗 | 0 |

本票新增的 46 份(先查快取再抓,已有的不重覆抓):
`ACLS ALAB ALNY AM AR ARRY ASPI BURL BYD CART CMC CORZ CP CRDO EU FLUT FN GPOR HIMS HIVE HUT INFQ
IPI IREN LGIH LIND LTBR LXU META MHO MOD NNE OKLO ONTO PTEN PXD RSI S SHLS SHOP TLN UAN URG UUUU VAL XOM`

缺失名單(36 家外國申報人,申報 20-F 或 40-F,票面規定不抓全文):
`AEM AU B BABA BHP BIDU BILI BP CCJ CNI CSIQ DNN ERO GFI GRAB HBM ICL JD KGC NIO NTES NTR NVO NXE
PDD RIO SGHC SHEL SPOT TCOM TECK TGB TME TTE VIK XPEV`

兩單資料衛生要記住:①EDGAR 現役代碼表把 `XOM` 指向重組後的新控股 CIK(該 CIK 未有年報),
年報仍在舊 CIK 34088 名下,`build_v1.py` 內已硬編碼修正;②`OKLO` 與 `HIMS` 原本的快取只有 2022 年那份
(OKLO 那份其實是併殼前的空殼公司年報),與鏈的故事對不上,已另抓 2025 年度那份。

### valid_from 品質

157 / 309 行(50.8%)標記為近似。分開看:v0 的 143 行沿用舊倉鎖死日期;v1 新增 166 行之中只有 9 家
查到明確的入位事件日,**其餘 95% 是近似**。這一欄目前撐不起需要準確入位日的測試(事件研究、按入位日切樣本)。

### 未做、留給後續票

1. **事前可得那一關未答**(研究文件 v2 第七節第 2 點):要用只看切片日之前的資訊重建同一張表再量一次,
   兩個數相差不遠,「事前可得」才算答到。
2. **三條 v0 鏈成員不是同一個位置**(`staples`、`web3_crypto`、`china`),已在表上標示,建議 v2 拆開;
   v1 依票面規定未動 v0 原行。
3. `uranium_power` 把礦商與濃縮商放同一條、`streaming` 把內容自有商與分發平台放同一條,同樣建議 v2 拆開。

## v2 純度版(2026-09-03,KARST-161,交審稿)

用戶裁決 D-147 ③(原話:「Yes, I dont care how much you add, but the purity of the layer is the
highest priority. The company in the same layer should share the same narrative」)。判斷每家成員
只問一句:**這家公司的股價,主要跟這條鏈的共同敘事走,還是跟它自己的故事走?**

- **正本交審文件**:`chain_stories_v2.md`(逐鏈故事、位置、純度判詞、成員表;首段四項誠實聲明)
- **表**:`chain_membership_v2.csv`(UTF-8 BOM)。新增 `purity`(逐家一句判斷)、`purity_note`
  (逐鏈一句:共同敘事是什麼、哪家最邊緣)、`src_theme_v1`(它在 v1 屬於哪條鏈)三欄。
- **出隊名單**:`removed_v2.csv`,23 行,每行寫明中了四條出隊規則的哪一條加一句理由。
- **腳本**:`roster_v2.py`(逐鏈定義與出隊名單)、`build_v2.py`(重組、EDGAR 查證、與 v1 逐行對帳)、
  `gen_doc_v2.py`(生成交審文件)。
- **v1 與 v0 一字不改**,仍在原處;`build_v2.py` 只讀不寫 v1。

### 出隊四規則

| 規則 | 意思 |
|---|---|
| a 位置不同 | 它在鏈上的位置與其餘成員不同(買方對賣方、製造對零售、持牌對輕資產) |
| b 定價機制不同 | 決定它售價的那個變數,與其餘成員不同 |
| c 單一資產主導 | 股價主要由一項自有資產或一宗自有事件驅動(舊倉 ADR-0039 代表性測試,D-147 ③ 收回) |
| d 主業已轉向 | 主要股價驅動已轉去另一條鏈;多元業務只入其股價主要跟隨的那條 |

### 數

| | v1 | v2 |
|---|---:|---:|
| 鏈數 | 52 | **65**(v1 的 9 條拆散,22 條新鏈名) |
| 成員行數 | 309 | **347**(新增 61,出隊 23) |
| 不重覆公司數 | 298 | **343** |
| 名冊 <5 家的鏈 | 4 | **16** |
| 年報佐證 | 273/309(88.3%) | **306/347(88.2%)**,本票新抓 25 份 |
| valid_from 近似 | 50.8% | **60.5%** |

拆散的 9 條:`staples` `web3_crypto` `china`(票面指定)、`uranium_power` `streaming` `fintech`
`ev` `casino_resorts` `ag_fertilizer`(純度覆核發現)。另外由 `crypto_mining` 拆出 `ai_hpc_hosting`、
由 `auto_retail` 拆出 `auto_aftermarket`;`aero_aftermarket` 與 `china_education` 是沒有 v1 成員的新鏈。

### v2 的兩個代價(交用戶裁)

1. `copper` 由八家縮到三家(三家初級礦商中規則 c、兩家多元化礦商中規則 d),這條鏈從此量不出顯著同步度。
2. `ag_fertilizer` 拆成鉀磷與氮肥之後,兩邊都不足五家。**純度與可量度性在這兩條上直接相撞。**

### 未做、留給後續票

1. 事前可得那一關仍未答(同 v1)。
2. 純度判斷全部是人手判斷,**沒有任何統計量度背書**——本票是編表票,不出成績。
3. `valid_from` 近似比例由 50.8% 升到 60.5%(新增成員多數近似),需要準確入位日的測試仍要先補這一欄。

## v2.1 換鏈日期版(2026-09-03,KARST-168)

用戶裁決 D-152 ②「照建議收貨」,當中一項是 D-151 ② 的建議:**主業轉向的成員不整家出隊,
改記為換鏈日期**——舊鏈一行 `valid_to`=轉向日、新鏈一行 `valid_from`=同日,
令切片日期在轉向日之前的樣本仍然可用。

- **正本**:`chain_membership_v2_1.csv`(UTF-8 BOM)、`chain_stories_v2_1.md`、`removed_v2_1.csv`(UTF-8 BOM)
- **腳本**:`build_v2_1.py`(只讀 v2 三個檔,不寫回;轉向日與佐證是腳本內的一張表,改判詞改那張表再重跑)
- **v0 / v1 / v2 一字不改**,仍在原處(已用逐格比對確認)。

### 逐行覆核 `removed_v2.csv` 23 行的結果

| | 行數 |
|---|---:|
| 改記換鏈日期(規則 d,而且兩條鏈在 v2 都存在) | **2**(MSFT、ORCL) |
| 維持出隊 | **21** |
| ↳ 其中掛規則 d 名下但不是「某一日轉向」 | 4(BHP、RIO、COP、HOOD) |
| ↳ 規則 a / b / c | 17 |

- **MSFT** 轉向日 `2023-01-23`(月準確):FY2023 10-K 明文「In January 2023 we announced the third
  phase of our OpenAI strategic partnership」;OpenAI 一詞在 FY2022 年報 0 次、FY2023 年報 7 次。
- **ORCL** 轉向日 `2023-06-01`(**近似**,取 FY2024 財年首日):FY2024 10-K 業務描述開首首次以
  「用 OCI 訓練生成式 AI 模型的 AI 公司」作代表客戶,FY2022/FY2023 同一段只有通用 AI 字眼。
  這個日期由 2024-06-20 才公開的年報倒推,**本身帶前視成分**。
- **COP** 的轉向日查得到(2012-04-30 完成 Phillips 66 下游分拆,FY2012 10-K 有明文),但在表的
  起點 2022-01-01 之前,補回舊鏈那一行只會得出空區間,所以維持出隊。順帶更正:v0 那一行的
  `valid_to=2026-07-22` 是舊倉的表務日期,不是業務轉向日。
- **BHP / RIO** 全期鐵礦石主導、沒有轉向日,而且 v2 的 65 條鏈沒有鐵礦石那一層可換。
- **HOOD** 那一行本來是同一家公司在 v1 出現兩次的去重,不是轉向;`fintech` 在 v2 已拆散,沒有舊鏈可寫。

### 數

| | v2 | v2.1 |
|---|---:|---:|
| 鏈數 | 65 | 65 |
| 成員行數 | 347 | **349** |
| 不重覆公司數 | 343 | 343 |
| 出隊行數 | 23 | **21** |
| 本票新抓年報 | — | **0 份**(佐證全部在 `data/sec/10k_text` 快取內) |

`chain_membership_v2_1.csv` 比 v2 多三欄(`v21_change`、`switch_date_basis`、`switch_evidence`),
`removed_v2_1.csv` 多三欄(`v21_review`、`switch_date`、`switch_evidence`);沒有改動的行留空。

### 對 v2 內容的唯一一處連帶改動

`software_cloud` 的逐鏈純度句(`purity_note`,該鏈 10 行共用)在 v2 寫住「v2 剔走四家:MSFT 與
ORCL 按規則 d……」,在 v2.1 已經不成立,所以改寫了那一句。除此之外,carried 過來的 347 行
只有 MSFT / ORCL 在 `hyperscalers` 那兩行的 6 格有改(`valid_from`、`note`、`valid_from_basis`)。

### 未做

1. 同一類前視問題在 v2 其他地方仍在:`ai_hpc_hosting` 四家(CORZ / IREN / WULF / CIFR)2024 年才
   轉去 AI 託管,`valid_from` 仍是 2022 年初;HOOD 在 `crypto_exchange` 的 `valid_from` 仍是 2022-01-01。
   按票面「其餘 v2 內容一字不改」本票沒有動,要處理是另一張票。
2. 純度判斷仍然全屬人手,沒有統計量度背書;本票是改表票,不出成績。

## 出處檔(舊倉,唯讀)

- `docs\adr\0024-three-layer-model-theme-layer-narrative.md`
- `docs\adr\0031-classification-mechanism-and-industry-map.md`
- `docs\adr\0039-representative-rule-and-layer-freeze.md`(最終鎖死版)
- `bt\exp9_full_reader\chain_membership.csv`(唯一真源)
- `bt\exp9_full_reader\results\chain_audit_proposal.md`(30 鏈、142 個成員位的舊草稿,已被 ADR-0039 取代;
  v1 用它作補成員的候選名單與出隊理由的旁證)
