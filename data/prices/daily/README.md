# 日線單一價格庫(daily price library)

倉內唯一一份「宇宙全體代號的日線 OHLCV」。D-134 的黃金原則(同一份原料只准一份副本、
有 manifest、有校驗、主鍵不會被代號重用污染)由文本原料延伸到價格。
D-153 第 2 條把 154 家新增收市價與六個未登記價格檔一併收進這裡。

- 建立票:KARST-171(2026-09-03)
- 位置:`C:\projects\Karst\data\prices\daily\`
- 主鍵:**`entity_id` = 證監會申報人編號(CIK,十位補零)**。代號只是帶時段的別名。
- 覆蓋:`data/universe/ticker_periods.parquet` 全部 5,952 個代號時段
- 倉根 `data/` 已被 `.gitignore` 擋住,所以 `part_*.parquet` 不入 git;
  本 README、`manifest.csv`、`failed.csv` 用 `git add -f` 納入版本控制。

---

## 一、檔案

| 檔 | 內容 |
|---|---|
| `part_00.parquet` … `part_15.parquet` | 價格長表,16 個分片,共 20,647,659 列、462 MB |
| `manifest.csv` | 每個代號時段一行,5,952 行 |
| `failed.csv` | `status = fail` 的代號時段(3 行) |
| `README.md` | 本檔 |

**分片規則:** `int(entity_id[-2:]) % 16`。一個實體的全部列一定在同一個分片。
要讀全庫就把 16 個檔一齊讀(`pd.read_parquet` 直接讀目錄亦可)。

### 價格表欄位

| 欄 | 型 | 意思 |
|---|---|---|
| `entity_id` | string | CIK 十位補零。**主鍵** |
| `ticker` | string | 該列的日線由哪個代號抓回來 |
| `date` | date32 | 交易日 |
| `open` / `high` / `low` / `close` | float64 | **拆股調整後、未除息調整** |
| `adj_close` | float64 | **拆股加除息調整**。生產線 D-026 `adjusted-close-only` 口徑就是這一欄 |
| `volume` | float64 | 成交股數 |
| `series_role` | string | `primary`(入實體時間序列)或 `alias`(見第三節) |
| `source` | string | `yfinance(auto_adjust=False, actions=False)` |
| `fetchedAt` | string | 該批的抓取時間,UTC ISO-8601 |

**要拿生產線那個口徑就用 `adj_close`。** 要拿已調整的開高低,乘比率
`adj_close / close`(同一日的比率對四欄通用)。

### manifest.csv 欄位

`entity_id`、`ticker`、`valid_from`、`valid_to`、`rows`、`first_date`、`last_date`、
`status`、`error`、`series_role`、`alias_reason`、`head_gap_days`、`tail_gap_days`、
`attempt`、`batch`、`fetchedAt`

---

## 二、status 怎樣判(是定義,不是可調參數)

| 值 | 條件 | 數 |
|---|---|---|
| `fail` | 一列都取不到(重試一次之後仍然沒有) | 3 |
| `partial` | 有列,但最後一日比 `valid_to` 早超過 **45 日** | 70 |
| `ok` | 其餘 | 5,879 |

完成率(ok + partial)= **99.95%**。

70 個 `partial` 之中 69 個的最後一日同是 2026-07-17,逐個看絕大多數是認股權證
(`IVDAW`、`OXBRW`、`MNTSW` 一類:代號尾一個 `W` 而**沒有連字號**)。
v0 的 E4 只剔 `-W[SI]?$` 這種帶連字號的寫法,納斯達克無連字號的權證代號整批漏網。
權證的價格與正股是兩回事,這一格交主 agent(本票不改規則)。

**頭段刻意不入 status。** `valid_from` 是「首次申報日」的代理,不是上市日
(`RULES.md` 第四節);借殼上市與 1994 年之前已有申報歷史的公司,頭段必然大幅落後。
全庫 5,949 段之中 4,223 段的 `head_gap_days` 超過 45 日,中位數 175 日——
**這量到的是 v0 日期口徑的性質,不是抓取失敗**,所以只逐段記在 `head_gap_days`,
由讀取方自己判斷,不當成殘缺。

---

## 三、同實體多代號:別名閘

同一個實體可以有多個代號時段。兩種情形要分開:

1. **不重疊**(例如 Fiserv:FISV → FI):兩段全部 `primary`,自然接成一條時間序列。
2. **重疊**(雙重股權,例如 GOOGL / GOOG 同時掛牌):只有一條可以入實體序列。

重疊時的裁決次序(照 KARST-084 同實體別名閘的規則形):

1. `valid_to` 空白(仍然生效)優先
2. 真實日線較多優先
3. 代號字母序

輸的那條標 `series_role = alias`,理由寫在 `manifest.csv` 的 `alias_reason`。
**alias 的價格照存不刪**——它是事實,只是不入實體序列。

- `primary` 5,263 段、`alias` 689 段
- 只取 `series_role = 'primary'` 的列,`(entity_id, date)` **零重複**(已核)

---

## 四、抓取參數

| 項目 | 值 |
|---|---|
| 來源 | yfinance 1.3.0 |
| 參數 | `auto_adjust=False, actions=False, threads=True` |
| 批次 | **40 個代號一批**,批與批之間退讓 1.2–2.0 秒 |
| 重試 | 一批跑完之後,失敗者以 8 個一小批、退讓 1.5–2.5 秒重試**一次**;仍然失敗即入 `failed.csv`,不無限重試 |
| 窗口 | 每段只取 `valid_from` 至 `valid_to` 之間;`valid_to` 空白者取到抓取當日 |
| 實跑 | 149 批、8.1 分鐘、5,949 / 5,952 段取得到數 |

KARST-167 實測:200 個一批不退讓,成功率只有 32%;40 個一批加退讓 99.3%。
**下一張要抓 yfinance 的票照這組參數,不要重蹈。**

---

## 五、必須知道的三件事

### 1. `adj_close` 不是不變量——每次派息會把整條歷史重新縮放

與生產快照 `2026-08-28-493fd1df1cb9` 對帳 20 個代號:18 個逐日差在 0.0002% 以內
(float 捨入層次),兩個全期出現**同一個常數比率**的偏差:

| 代號 | 本庫 `adj_close` ÷ 生產快照 `close` | 比率標準差 |
|---|---|---|
| LMT | 0.993853(即低 0.615%) | 2.0e-07 |
| TAP | 0.988478(即低 1.152%) | 1.7e-07 |

比率是常數不是噪音——兩家公司在 2026-08-28 與 2026-09-03 之間除息,
Yahoo 把新一筆股息**追溯**乘回整條歷史。所以:

> **同一個代號在兩個不同日子抓回來的 `adj_close` 必然對不上帳,差幅等於期間的派息率。**
> 要復現一次回測結果,靠的是快照編號,不是「再抓一次」。本庫沒有快照編號,
> 它是**原料庫**不是快照;凡是要復現的運行,照舊要經凍結模組凍成快照。

未調整的 `close` 欄不受派息影響(只受拆股影響),所以要看「當年真實成交價」用 `close`。

### 2. 沒有退市公司

代號來自證監會 2026-09-02 的今日快照(`RULES.md` 第七節第 1 條)。
**當年上市、後來除牌的公司一家都沒有。** 由本庫算出來的任何基礎率一律是倖存者口徑
(D-152 第 2 條),不與文獻或付費來源比較。

### 3. 沒有主日曆、沒有停牌填補

本庫是**原料**:一日有報價就一列,沒有就沒有那一列。生產線的「主日曆對齊 + 停牌前值填補
最多三日 + `bar_status`」(KARST-027)在凍結成快照那一步才做,本庫刻意不做,
免得原料層先做一次判斷、快照層再做一次。

---

## 六、與倉內其餘價格檔的關係

D-153 第 2 條要收的兩批,處置如下。**舊檔一個都沒有刪、沒有改**,只在這裡記低它們已經
被本庫取代:

| 舊檔 | 代號數 | 已登記 | 本庫已覆蓋 | 判 |
|---|---|---|---|---|
| `experiments/2026-09-02-narrative-layers-v2/data/new_close.parquet`(154 家) | 154 | 150 | 150 | **已被本庫取代**(4 個未登記,見下) |
| `experiments/2026-09-02-timing-sweep/data/daily_close.parquet` | 584 | 569 | 569 | 已被本庫取代(15 個未登記) |
| `experiments/2026-09-02-tenbagger-scan/data/counterexample_close.parquet` | 10 | 10 | 10 | **完全被本庫取代** |
| `experiments/2026-08-31-sector-safety/prices_daily.parquet` | 11 | 0 | 0 | 未取代:全部是 ETF(SPY 與板塊 SPDR),不在本宇宙 |
| `experiments/2026-08-31-fear-greed/prices_daily.parquet` | 10 | 0 | 0 | 未取代:同上 |
| `experiments/2026-09-02-tenbagger-casecontrol/data/prices_monthly.parquet` | — | — | — | 未取代:月線、版式不同(索引 `symbol`/`month_end`) |

**「已被本庫取代」的意思是:** 同一批代號,本庫有更齊的欄位(開高低收量,舊檔只有收市價)、
有實體主鍵、有 manifest 與 status。新票要用這批價格請讀本庫,不要再讀舊檔。
舊檔留原位是因為既有分析腳本仍然指着它們,刪檔屬另一張票的事。

### 未登記代號(交主 agent,本票不擅自補登記)

六個舊檔合共 20 個代號不在代號時段表(另有三個是版式問題誤讀的欄名 `close`、
`close_unadjusted`、`volume`,不是代號)。逐個原因:

| 代號 | 原因 | 是不是規則刻意的 |
|---|---|---|
| SPY、IEF、XLB、XLE、XLF、XLI、XLK、XLP、XLU、XLV、XLY | ETF。九隻板塊 SPDR 與 IEF 連 CIK 都不在證監會代號快照;SPY 有 CIK 但無年報被 I3 攔下 | **是**,本宇宙刻意不收 ETF |
| FMCC、FNMA、GTBIF | 只有場外報價,E3 剔 | **是** |
| EA | 證監會 2026-09-02 代號快照裡已經沒有 EA | 是(已不在快照) |
| **XOM、HONA、SPCX** | 有 CIK、在主要交易所,但**未交過年報**,I3 剔 | **不是——這是真漏** |
| NXG | 封閉式基金,無年報,I3 剔 | 是 |
| **AEP** | `submissions` 的 `exchanges` 欄空白,E3 剔 | **不是——這是真漏** |

完整清單連原因:`experiments/2026-09-03-price-library/out/unregistered_reasons.csv`。

**兩個真漏值得主 agent 看:**

1. **I3(至少一份年報)會漏掉新上市與剛重組的公司。** `XOM` 今日指向
   `ExxonMobil Holdings Corp`(CIK 0002115436,2026 年重組的新控股公司)、
   `HONA` 指向 Honeywell Aerospace、`SPCX` 指向 SpaceX——三家都在主要交易所、
   都未夠時間交第一份 10-K,所以整家不在宇宙內。**十倍股線最關心的正是新上市那一批**
   (D-154 已記「漏掉的正是新上市與外國申報那批」),這條規則與那個目標直接相衝。
2. **E3(交易所欄空白即剔)有一個免費資料的坑。** AEP(American Electric Power,
   納斯達克上市的大型公用事業)的 `submissions.exchanges` 是空陣列,所以整家被剔。
   抽樣 400 個「有代號但不在實體表」的 CIK:76 個交易所欄空白,其中 19 個是
   `operating` 而且交過年報(推算全體約 130 家)。逐家看多數是場外殼股,
   但 AEP 證明這條規則會誤剔真正的主板公司。
   量度腳本:`experiments/2026-09-03-price-library/probe_exchange_blindspot.py`。

**本票不改規則、不補登記**——改收錄規則屬宇宙名單票的範圍,列在這裡交主 agent 裁。

---

## 七、重建方法

```
set PYTHONUTF8=1
cd C:\projects\Karst
python experiments\2026-09-03-price-library\fetch_prices.py       # 約 8 分鐘,寫 data/prices/_parts/
python experiments\2026-09-03-price-library\consolidate.py        # 合併成分片、manifest、failed
python experiments\2026-09-03-price-library\stats.py              # 體檢數字
```

`data/prices/_parts/` 是中途產物,合併完成之後刪走(單一副本原則)。
重跑一次會得到**不同的 `adj_close`**——理由見第五節第 1 點。
