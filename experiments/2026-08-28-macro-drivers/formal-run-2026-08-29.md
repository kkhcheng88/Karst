# 一次帶宏觀快照的正式運行(KARST-070,2026-08-29)

## 一句話

「因子輪動(ETF 版)」策略此前只有掃描格,一次正式運行都沒有(KARST-067 已指出)。
本票補上第一次:取 `experiments/2026-08-28-macro-rejudge/` 按軸型重判之後最高、
且鄰域真站得住的一格(曲線斜度變化方向),經唯一入口登記參數集,以現役宏觀快照
`2026-08-28-dc2d9f1a1778` 執行一次正式運行(來歷 `FORMAL_RUN`)。策略頁在該策略
正路上(不用只帶 `?run=` 的網址催)已經顯示「序列齊全度」標記,以 API 核對過。

## 取值來源

`experiments/2026-08-28-macro-rejudge/results/summary.json` 的
`drivers.curve_trend.best`:六個宏觀驅動器之中最高的一格,鄰域平均由重判前的
+1.59% 升到 +2.89%(該目錄 README「三件要記住的事」第二點:是真孤峰,不是被
隔壁層拖低造成的假象)。

- 驅動器:曲線斜度變化方向(`curve_trend`)
- 取值:`lookback_days=20`、`tilt=1`、`cadence=monthly`
- 來源掃描編號:`experiments/2026-08-28-macro-drivers/mac-curve_trend`
  (即 KARST-040 首跑、KARST-048 接上軸型判讀那 30 格)

## 登記與執行

經唯一入口(`gateway.register_param_set`,即 `karst` 命令列 `params add` 背後
那一條門)登記參數集,名稱注明示例與來源掃描編號:

- 參數集:**「示例正式-KARST-070-來源mac-curve_trend」第 1 版**
- 策略:「因子輪動(ETF 版)」第 2 版
- 換倉節奏:monthly
- 價格快照:`2026-08-28-000b4820a23a`(現役,六隻因子 ETF)
- 宏觀快照:`2026-08-28-dc2d9f1a1778`(現役,十四條序列,KARST-058 換源之後
  VIX_3M 零留空)
- 期間:2015-01-02 ~ 2026-08-26(2,929 個交易日)
- 成本:零成本(D-030 主報口徑)

跑法直接呼叫 `run_factor_rotation` + `record_factor_rotation_run`(來歷寫
`FORMAL_RUN`),不經 `karst.sweep.runner`——掃描跑法一律記 `SWEEP_RUN`,不管格數
是一格還是一百格,見 `record_factor_rotation_run` 的說明。重跑見
`run_formal_run.py`。

**運行編號:`run-924a54eb843f0988`**(策略版本 2 × 參數集「示例正式-KARST-070-
來源mac-curve_trend」第 1 版 × 2015-01-02~2026-08-26 × 價格快照
2026-08-28-000b4820a23a × 引擎 vectorbt 0.1.0;逐日序列核對「全對」)。
A-009 教訓:引用示例一定要連參數集版本一併寫明,單靠運行編號不夠。

成績(讀回已保存序列算出,不重跑引擎):對 SPY 年化超額 +5.3712%、年化回報
19.22%、最大回撤 −33.70%、換手 5.74——與 `mac-curve_trend` 那格掃描成績逐位相同
(同一組取值、同一份快照,本來就該撞出同一個數;差別只在來歷從 `sweep` 換成
`formal`)。

`karst verify`:全庫清白(登記與運行皆經唯一入口,受治理的每一列都有簽章)。

## 策略頁核對(API,臨時埠 8767)

以 `python -m karst.web --port 8767` 開一個臨時伺服器(不是用戶已開在 8765 那個;
中途曾誤撞用戶那個埠,已即時停掉自己那一個,確認未動用戶的),核對完即關閉。

- `GET /api/overview` → 「因子輪動(ETF 版)」那一行:`runCount: 1`、
  `runId: "run-924a54eb843f0988"`(此前一直是 0/None)
- `GET /api/strategy?id=3` → `runTotal: 1`,`defaultRunId` 就是這次運行——
  策略正路(不帶 `?run=`)已經看得到,不用再靠只帶 `?run=` 的網址催
- `GET /api/runs/run-924a54eb843f0988` → `paramValues.macro_snapshot` =
  `2026-08-28-dc2d9f1a1778`(前端 `strategy.js` 的 `renderConfig()` 靠這一格
  觸發「序列齊全度」晶片)
- `GET /api/macro/completeness?snapshot=2026-08-28-dc2d9f1a1778` → 14 條序列、
  `worstStaleDays: 0`、`staleSeries: []`、`alerts: []`——即晶片會顯示
  「序列齊全度 14 條・尾段貼齊主日曆」(KARST-058 換源之後 VIX_3M 不再落後,
  與 KARST-067 票上舉的那個「尾段落後」例子不同,但同一枚晶片、同一條正路)

三項合起來:策略頁在「因子輪動(ETF 版)」的正路上,序列齊全度標記由這次正式運行
自然帶出,不再需要 KARST-067 那條「只帶 `?run=`」的網址去催。

## 落檔

- `run_formal_run.py` —— 重跑腳本(登記參數集、跑正式運行、落 summary）
- `formal-run-2026-08-29-summary.json` —— 運行編號、參數集版本、快照編號的機讀摘要
- 本檔 —— 核對結果的人讀摘要
