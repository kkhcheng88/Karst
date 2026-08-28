---
id: KARST-063
title: Alpha158 因子計算:照公開公式自寫 pandas 版本(不裝 qlib),在起步宇宙 12 隻上算出全部 158 條並對照官方數值抽查
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-062]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-29
---

## 工作內容

依 research/2026-08-29-alpha158-feasibility.md 第一、二節與用戶 2026-08-29 裁決(四張票同時開)。範圍:新模組(建議 karst/factors/alpha158.py)以 pandas 實作 Alpha158 全部表達式——K 線形態組、價格組、成交量組、滾動窗口組(28 種運算子 × 5/10/20/30/60 日);輸入是現有 K 線面板(日線開高低收量),輸出是「日期 × 實體 × 因子名」長表,只算不入庫。第一步先跑一次 qlib 的 get_feature_config() 核實 158 條逐組確切條數並記入模組說明。牽涉成交均價的幾條用近似值並在模組說明列明。測試:小樣本(兩三隻股票、短窗)對照公開的 qlib 官方公式抽查至少十條因子數值;只跑自己新增的測試檔。不裝 qlib 為運行依賴(核實條數可用臨時環境)。不加參數預設值。

## 驗收條件

- [x] 158 條因子在起步宇宙 12 隻上全部算得出,逐組條數與 qlib 官方核實一致並寫入模組說明
- [x] 至少十條因子小樣本數值與公開定義對照一致(測試檔),近似處理的條目列明
- [x] 只新增模組與測試,不動因子表、不動唯一入口、不跑全庫測試

## 結果

· 2026-08-29 01:57 Alpha158 的 pandas 實作落檔並收工。

新模組 `karst/factors/alpha158.py`(連新套件 `karst/factors/__init__.py`),純
pandas/numpy 實作 Alpha158 全部 158 條;新測試 `tests/test_alpha158.py` 21 項全綠
(只跑本檔,1.8 秒)。**不入庫、不動唯一入口、不動 schema、不設參數預設值。**

### 一、逐組條數(以 qlib 官方輸出核實)

先在本倉之外的臨時目錄下載 pyqlib 0.9.7 官方輪檔,把 `Alpha158DL.get_feature_config()`
原封不動抽出來跑一次,取回它自己吐的 158 條名稱與表達式(**沒有在本倉裝 qlib,
亦沒有加進依賴**)。同時核實 `contrib/data/handler.py` 的 `Alpha158` handler 是以
無參數方式呼叫它,即預設設定就是這 158 條。

| 組 | 條數 | 內容 |
|---|---|---|
| K 線形態組 | 9 | KMID KLEN KMID2 KUP KUP2 KLOW KLOW2 KSFT KSFT2 |
| 價格組 | 4 | OPEN0 HIGH0 LOW0 VWAP0(官方預設只取窗口 0;CLOSE 不在預設清單內) |
| 成交量組 | 0 | 官方預設 config 沒有 `volume` 這一格,原始 `VOLUME{d}` 一條都不出 |
| 滾動窗口組 | 145 | 29 種運算子 × 5 個窗口(5、10、20、30、60) |
| 合計 | 158 | |

兩處要更正調研檔 `research/2026-08-29-alpha158-feasibility.md`(調研檔不改,
在此記低,實作以官方輸出為準):第 1.3 節把「成交量組」當成獨立一組——實測
官方預設**不出**這一組,成交量只經滾動組的 VMA/VSTD/WVMA/VSUM* 入賬;第 1.4 節
寫「28 種運算子」——實測是 **29 種**(它把 VSUMP/VSUMN/VSUMD 併成一行數),
29 × 5 = 145,加 9 加 4 才夠 158。另外第 1.4 節對 IMAX/IMIN 的白話解說
(「高位距今幾日」)與官方實作**方向相反**:`IdxMax` 是 `argmax()+1`,由窗口
**最舊那格**數起,滿窗時最新一格中選即得 d。模組說明已按官方實作寫。

### 二、近似處理(唯一一條)

`VWAP0 = $vwap/$close` 是 158 條之中**唯一**一條要用日線 OHLCV 以外欄位的
(調研檔估「頂多幾條」,實測是 1 條)。日線來源沒有逐日成交量加權平均價,本檔
以典型價 `(high+low+close)/3` 代之,模組常數 `VWAP_APPROXIMATION` 與清單
`ALPHA158_APPROXIMATED` 都列明,下游要剔走或改算法照那個清單走。其餘 157 條
全部原式,無近似。

### 三、抽查結果

(甲)小樣本手算對照(驗收條件 2):八根整數 K 線上,**20 條以上**因子的期望值
在測試檔內以 Python 內建算術與 `statistics` 逐條手算(一個運算子都不借模組
自己的),全部對得上:KMID、KLEN、KUP、KLOW、KSFT、KSFT2、OPEN0、HIGH0、LOW0、
VWAP0、ROC5、MA5、STD5、MAX5、MIN5、QTLU5、QTLD5、RANK5、RSV5、IMAX5、IMIN5、
IMXD5、CNTP5、CNTN5、CNTD5、SUMP5、SUMN5、SUMD5、VMA5、VSTD5、VSUMP5、VSUMN5、
VSUMD5、WVMA5、BETA5、RSQR5、RESI5、CORR5。另有三項守住最易寫錯的語意:
`min_periods=1`(窗口未滿一樣出值)、`Std` 用 ddof=1、常數段的相關系數與決定
系數要留空。

(乙)全 158 條對照官方表達式(驗收條件 1):起步宇宙十二隻的快照
`2026-08-28-a508d635a5fa`(2015-01-02 至 2026-08-26,2,929 個交易日),把 158 欄
逐欄對住「官方表達式獨立求值」——用 qlib 自己那個編譯好的滾動核心算
Slope/Rsquare/Resi,其餘運算子照 `qlib/data/ops.py` 逐條轉寫:12 隻 × 158 欄 =
1,896 次對照,其中 **1,716 欄逐位相同**(bit-identical)、19 欄相對差 < 1e-9、
161 欄相對差 ≥ 1e-9(全部落在 BETA / RSQR / RESI 三族,最大 6.7e-05)。

那 161 欄**不是算法不同,是 qlib 那邊的浮點漂移**:它的滾動迴歸用一條增量
累加器貫穿整條序列,誤差沿 2,929 格累積;本檔每個窗口重算一次。以有理數
(`fractions.Fraction`)算出精確值再比,在雙方分歧最大那幾格上本檔比 qlib
**近 2 至 5 個數量級**——差的是官方那邊。餘下 155 條沒有這回事,逐位相同。

(丙)十二隻上算得出全部 158 條:`compute_alpha158()` 在這個快照上出
**5,553,384 列**長表(12 × 2,929 × 158),用時 1.8 秒。158 條**無一條整欄留空**;
有值格佔 99.96%,覆蓋率最低是 ROC60 的 97.95%——正好是它按定義要的前 60 格
暖身(60 ÷ 2,929 = 2.05%),不是算不出。

### 四、輸出形狀

`compute_alpha158(bars)` 收 `karst.data.read_price_frame` 那個日線長表,回
`date`、`entity_id`、`factor`、`value` 四欄的長表,按日期、實體、官方因子次序排。
`factor` 是有序類別欄(categorical,類別次序就是 `ALPHA158_NAMES`)——五百幾萬列
用字串欄裝不下,而且這一格的次序同時就是官方次序。單一實體要寬表的話
`compute_alpha158_for_entity(bars)` 回「日期 × 158 欄」。`bar_status` 一概不理:
停牌填補那根 K 線餵不餵進來由呼叫方決定(D-026 第 6 條),本檔照收到的數算,
留空的格算出來照樣留空。

### 五、順手做了一件、以及留給下一張票的

`pyproject.toml` 的 `[tool.setuptools] packages` 加了 `karst.factors` 一項——
不加的話裝好套件之後這個模組不會跟住裝,等於白寫。只加這一個字,其餘沒有動。

下一張票(因子入庫與版本登記)要處理的:158 條各自登記 `factor`/`factor_version`、
按 D-021 補齊可執行時點與產生程序版本、批量寫 `factor_value`,全部經唯一入口。
另外調研檔第 89 行已記:官方預設標籤 `Ref($close,-2)/Ref($close,-1)-1` 是 A 股
T+1 制度的產物,美股不能照抄——本票只做因子,標籤一條都沒有碰。

## 留言
