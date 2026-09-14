# karst/ —— 工作台程式(2026-09-14 建;規矩 D-180)

## 硬規矩(用戶 2026-09-14 明令)

**所有程式由第一日起必須通用。** 原話:「I see you are start making something like fetch_edgar_axti which is stock specific … you must at the end making tons of testing scripts. And the repo will be expanded to be uncontrollable. Can you do the script starting from now must be generic?」

1. 程式只住在 `karst/` 套件內,以模組加參數運行,例如 `python -m karst.fetch --ticker AXTI`;代號、公司名、日期、路徑一律由參數或設定檔傳入,**檔名與程式碼內不准出現任何一隻股票的代號或名字**。
2. 倉內不准有一次性腳本:沒有 `_tmp*.py`、`_peek*.py`、`fetch_<代號>.py`、`check_*.py` 之類;探索與除錯用的臨時碼放 session 的 scratchpad(倉外),用完即棄,不 commit。
3. 測試(若有)只放 `karst/tests/`,同樣通用(用參數化的樣本,不寫死某隻股票的預期數字)。
4. 每個模組一個職責:`fetch`(取證,按來源分子模組)、`manifest`(證據登記)、`packet`(取證包索引)、`ta`(技術結構)、`valuation`(估值算式)、`plan`(風險回報與計劃算式)、`page`(生成頁面)、`run`(一次分析的紀錄)。新增模組要先在本 README 登記用途。
5. 派工指令必須把本規矩原文帶給工人;工人交回的任何股票專屬檔一律不收貨。

## 佈局(第一版)

```
karst/
  README.md
  __init__.py
  config.py        路徑、User-Agent、速率限制;讀 .env 或環境變數,不寫死金鑰
  fetch/
    edgar.py       按 CIK 取申報索引、10-K / 10-Q / 8-K 與附件,先查本地快取(D-134)
    defeatbeta.py  逐字稿、報表、收入拆分、股數、日線
    broker.py      富途 / Longbridge 回傳快照的落地與登記(呼叫由 agent 或 CLI 做)
    prices.py      本地日線庫抽取與續抓合併
  manifest.py      manifest.jsonl 讀寫、內容定址、去重
  packet.py        取證包索引
  ta/              結構計算(區域、200 日 SMA、通道、突破回踩狀態、ATR、相對強弱)
  valuation/       正向三情境與現價反推
  plan.py          風險回報、部位示例
  page/            單檔 HTML 生成
  run.py           run 紀錄(投資委託版本、提示詞版本、模型、證據清單、各層時間)
```

第一版尚未實作;本檔先定規矩與佈局,實作票開出後按此落地。
