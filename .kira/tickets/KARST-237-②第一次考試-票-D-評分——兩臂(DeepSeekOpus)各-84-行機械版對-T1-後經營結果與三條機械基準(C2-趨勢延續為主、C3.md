---
id: KARST-237
title: ②第一次考試 票 D 評分——兩臂(DeepSeek/Opus)各 84 行機械版對 T1 後經營結果與三條機械基準(C2 趨勢延續為主、C3 訊號持續、C1 可比指引子樣本),照執行口徑 v1 第四節與主考試執行備忘的事前分組(entry_defect、identity_leak、g0 三檔、門檻決定型、有無收入指引、有無逐字稿、收購驅動、改善在收入/盈利、商品型、series 修正三宗),出主表、交叉表、分歧格、校準表、截尾版、剔除版;結論由主 agent 寫;不列公司名
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: 執行口徑 v1 第四節評分規則與第六節成敗條件;v1.2 修訂頁「判斷層雙臂」事前決定表;B/主考試執行備忘 第 5、7–9、12–13、16–17、19–23、25–26 項事前寫明的分組與處理;第四輪外評「全部落檔後才評分、評分者只讀機械版」;D-175 評分交 DeepSeek
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D06
---

## 工作內容

輸入:B/ds/rows/*.csv 與 B/opus/rows/*.csv(各 84,28 欄;E017/E022/E024 為包修正版重判;B/作廢/ 不讀);A3/controls_operating.csv(C1/C2/C3;C3 改以 quarters 欄收入定義重算 g0_quarters 作門檻);A3/packets/*.json 的 1_事件識別(T1、fiscal_quarter、cik)、4_財務數列(g0、quarters 收入口徑、entry_status)、2_觸發資料(有無逐字稿、prior_release_guidance、preliminary_release);A3/收入欄完整性核查——A3.md 與 A3/修正紀錄——235.md(缺陷組);B/主考試執行備忘.md(分組定義);T1 後實際:data/sec/companyfacts 首報值 Q+1..Q+4 單季收入按年增速(與 g0 同口徑),指引下修由 Q+1、Q+2 業績稿正則;不讀任何卡的人讀版。評分:M1(Q+1、Q+2 平均按年增速)、M2(四季);延續二值 = M1 ≥ 0.8×g0(g0<0 時 ≥ g0)且無下修,敏感度 0.7/0.9 與 M1 ≥ g0;每臂 pred_g2 對 M1 的絕對誤差(中位、平均、截尾 ±200% 平均)、區間命中;pred_g4 對 M2 同;C1(有值者)、C2、C3 對 M1 的絕對誤差;persistence × 延續交叉表與 p_continue 校準表(可靠性圖分五帶)與 AUC;分歧格(臂判高而 C2 判不延續、臂判低而 C2 判延續)實際結果;兩臂互比(同事件誤差差、判級一致率);分組報表(每組:含/剔除):entry_defect(E006/E050/E026)、series 修正三宗、identity_leak(9 宗)、g0 三檔(≤0 / 0–0.3 / >0.3)、門檻決定型(g0 ≤ 0.02 或 ≥ 0.6 或訊號季在 2020Q2–2021Q2)、有無收入指引、有無逐字稿、收購驅動(top_driver_type=收購)、改善所在(收入/盈利,由 improvement_text 關鍵詞)、商品型(SIC 10–14、29)、contamination_note 標「有影響」、pred 尺度違規(|值|>5 除以 100 並標);逐年剔走與分桶剔走;叢集(sic2×曆季)內相關另報;成熟度:Q+4 未到者標未成熟不入 M2。輸出 B/評分——第一次考試.md(主表、交叉表、分歧格、校準、兩臂互比、分組表、逐年剔走、資料缺失表、污染聲明)與 B/評分.csv(逐事件逐臂一行含所有欄);結論段留白由主 agent 寫。不列公司名。含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] 評分.csv 168 行(84 事件 × 2 臂)齊,每行含 M1/M2/延續三定義/誤差/命中/各分組標籤;反例:任何事件缺 M1 而未標原因,即不合格
- [ ] 主表含每臂與 C1/C2/C3 的 MAE 中位、平均、截尾平均、區間命中率;交叉表與校準表(五帶)與 AUC;分歧格;兩臂互比;分組表每組含/剔除兩版;逐年剔走
- [ ] 沒有讀任何卡的人讀版與 B/作廢/;不列公司名;不 commit

## 結果

## 留言
