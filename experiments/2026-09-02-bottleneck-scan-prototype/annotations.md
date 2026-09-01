# 標註表：12 份 MD&A × 判別清單 v0

標註人：agent bottleneck-142（KARST-142）
標註日期：2026-09-02
依據：`bottleneck-lexicon-v0.md`（本表產生前已凍結並獨立 commit，commit 400f0a3）
標註方式：對每份文本的候選句（`texts/*_candidates.md`）逐句套用 D1–D6 定義與 R1–R4 排除規則。
每個維度只要有一句合資格陳述即記 1，否則 0。

---

## 一、逐份評分

| # | 文本 | 臂 | D1 交付週期 | D2 產能 | D3 積壓 | D4 提價 | D5 供應 | D6 見度 | 總分 | 判定（閾值 3） | 結果 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ENPH FY2021 | 樽頸 | 0 | 0 | 0 | 1 | 1 | 0 | **2** | 非樽頸 | 假陰性 |
| 2 | ENPH FY2019 | 正常 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 非樽頸 | 真陰性 |
| 3 | GNRC FY2021 | 樽頸 | 1 | 1 | 0 | 1 | 1 | 0 | **4** | 樽頸 | 真陽性 |
| 4 | GNRC FY2019 | 正常 | 0 | 0 | 0 | 1 | 0 | 0 | **1** | 非樽頸 | 真陰性 |
| 5 | ROK FY2022 | 樽頸 | 1 | 1 | 1 | 1 | 1 | 0 | **5** | 樽頸 | 真陽性 |
| 6 | ROK FY2019 | 正常 | 0 | 0 | 0 | 1 | 0 | 0 | **1** | 非樽頸 | 真陰性 |
| 7 | POWL FY2024 | 樽頸 | 0 | 1 | 0 | 0 | 0 | 0 | **1** | 非樽頸 | 假陰性※ |
| 8 | POWL FY2019 | 正常 | 0 | 0 | 1 | 0 | 0 | 0 | **1** | 非樽頸 | 真陰性 |
| 9 | BE FY2024 | 樽頸 | 0 | 0 | 0 | 0 | 1 | 0 | **1** | 非樽頸 | 假陰性※ |
| 10 | BE FY2019 | 正常 | 0 | 0 | 1 | 0 | 0 | 0 | **1** | 非樽頸 | 真陰性 |
| 11 | CMI FY2021 | 樽頸 | 0 | 0 | 0 | 1 | 1 | 0 | **2** | 非樽頸 | 假陰性 |
| 12 | CMI FY2019 | 正常 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 非樽頸 | 真陰性 |

※ 見第三節：這兩份的「樽頸期」先驗標籤被文本證據直接否定，標籤本身有問題，不是清單漏判。

分數分佈：
- 樽頸臂：2, 4, 5, 1, 1, 2 → 平均 **2.50**，中位數 2
- 正常臂：0, 1, 1, 1, 1, 0 → 平均 **0.67**，中位數 1

---

## 二、關鍵證據（逐份摘錄，附命中維度）

**1. ENPH FY2021（樽頸臂，2 分）**
- D4：「we increased prices to partially offset the impact of higher expedited freight costs and component costs」— 已實施提價。
- D5：「We have seen supply chain challenges and logistics constraints increase, including component shortages, which have... caused delays in critical components」— 當期、實質、指向自己。
- D1/D2/D3/D6 = 0：Enphase 不披露 backlog、不談自身產能受限、不談對客戶的交付期。**清單的六個維度有四個對這家公司根本不適用。**

**2. ENPH FY2019（正常臂，0 分）**
- 僅有「shortages... could adversely affect」（R1 假設語氣，排除）與會計政策樣板句。乾淨的真陰性。

**3. GNRC FY2021（樽頸臂，4 分）**
- D1：「resulting in longer lead times and higher prices to our customers」、「extended lead times for these products as of December 31, 2021」。
- D2：「as we increase our production capacity for home standby generators throughout the year」＋ Trenton SC 新廠 ramping。
- D4：「we have implemented multiple price increases throughout the year」。
- D5：「various supply chain constraints, which are resulting in higher input costs and delays for certain of our products」。
- D3=0：文中只有「higher pricing works through backlog」，無 backlog 變動描述，按 D3 不合資格條款排除。

**4. GNRC FY2019（正常臂，1 分）**
- D4：「price increases implemented since the prior period」— 已實施。**正常年份一樣有提價**，這是 D4 作為樽頸指標的先天弱點。

**5. ROK FY2022（樽頸臂，5 分）— 全樣本最強**
- D3：backlog 由 $2,910.5M 升至 $5,197.0M（+79%），文中稱 record backlog。
- D5：「The results by region, segment, and industry were primarily driven by component availability rather than the underlying demand」— 明言業績由供給而非需求決定，這是最乾淨的樽頸陳述。
- D1：「extended component lead times」、「will over time normalize our product lead times」（反證當期未正常化）。
- D2：「capacity investments, including redundant manufacturing lines and additional electronic assembly equipment」。
- D4：「higher sales, including price increases」。
- D6=0：「extending order visibility to our supply base」是對供應商的動作，不是公司自身收入見度，按 R4 排除。

**6. ROK FY2019（正常臂，1 分）**
- D4：「pricing contributed less than two percentage points to growth」。其餘為行業列表誤匹配。

**7. POWL FY2024（樽頸臂，1 分）**
- D2：「purchase of land and buildings in Houston, Texas... to help further facilitate executing the current backlog」— 為執行積壓而增設施。
- D3=0：「The order backlog at September 30, 2024 was $1.3 billion, **consistent with** our backlog at September 30, 2023」— **積壓持平**，按 D3 不合資格條款排除。
- D5=0：只有「we continue to remain focused on... supply chain challenges」（泛論，R4 排除），另一句是毛利已改善（R3 緩解方向）。

**8. POWL FY2019（正常臂，1 分）**
- D3：「order backlog at September 30, 2019 was $419.0 million, a **61% increase**」— 合資格。
- **對照組的積壓增長（+61%）反而強過樽頸組（持平）**，見第三節。

**9. BE FY2024（樽頸臂，1 分）**
- D5：「We continue to see effects from global supply chain tightness」— 當期陳述，合資格。
- 但緊接：「**While we have not experienced any significant component shortages to date**」，以及勞工限制「these constraints have **since abated**」（R3 緩解）。
- D3=0：BE FY2024 MD&A 完全不談 backlog。

**10. BE FY2019（正常臂，1 分）**
- D3：product sales backlog $1.1B（2019）對 $0.8B（2018），+38%，有明確變動描述 → 合資格。

**11. CMI FY2021（樽頸臂，2 分）**
- D5：「Our industry continues to be unfavorably impacted by supply chain constraints leading to shortages across multiple components categories and **limiting our collective ability to meet end-user demand**」— 全樣本最明確的供給受限句之一。
- D4：「higher volumes and **favorable pricing**」— 已實現提價。**注意：D4 的種子詞是 `favorable price`，匹配不到 `favorable pricing`，是關鍵詞漏檢；這一句是從 D5 候選句裡讀到的。** 見第四節。
- D2=0：「We continue to invest in new product lines and targeted capacity expansions」— 與 FY2019 逐字相同，是樣板句，按 D2 不合資格條款排除。
- D3=0：Cummins 不披露 backlog。

**12. CMI FY2019（正常臂，0 分）**
- D5 的 6 條候選全是退休金資產配置段落誤匹配種子詞 `allocation`。乾淨的真陰性。

---

## 三、標籤本身出問題（誠實記錄，不是事後辯解）

樣本設計時我按「事後已知」給每家公司貼樽頸期標籤。讀完文本後，其中兩個標籤被文本證據直接否定：

- **POWL FY2024**：積壓與去年持平、毛利已改善、供應鏈只以泛論一句帶過。Powell 在 FY2024 的故事是**訂單已經到手、正在交付**，不是供給受限。真正的積壓爆發在 FY2023（FY2024 的 revenue +45% 正是來自 FY2023 awarded 的大合約）。標籤應該指向 FY2023。
- **BE FY2024**：Bloom 自己明說「未遇重大零件短缺」、勞工限制已緩解。它 FY2024 的故事是 **AI 數據中心的需求端故事**，不是供給側樽頸。

這代表：12 份樣本裡，樽頸臂實際只有 4 份標籤可靠（ENPH FY2021、GNRC FY2021、ROK FY2022、CMI FY2021，全部是 2021–22 供應鏈危機期）。

在這 4 份可靠樣本上：閾值 3 的命中率為 **2/4 = 50%**。

這是本原型最重要的方法論教訓：**「事後已知樽頸期」這個標籤，我是憑印象貼的，不是憑獨立證據貼的。** 沒有可靠標籤，任何命中率／誤報率都量不準。

---

## 四、關鍵詞預篩的漏檢（量產架構的直接證據）

- **`favorable price` 匹配不到 `favorable pricing`**（CMI FY2021 D4）。若只靠關鍵詞計數，這一分會丟掉；因為是 LLM 讀候選句，才在 D5 的句子裡看到它。
- **`allocation` 大量誤匹配退休金資產配置**（CMI 兩份，共 10 條噪音候選）。
- **`freight`、`logistic`、`semiconductor` 命中會計政策與行業列表樣板**（ENPH、ROK 兩份皆是）。

即：關鍵詞層的精確度很低（大量假候選），召回也不完全（漏 `pricing`）。
它只能當**檢索器**用，判定必須靠語意層。這一點原型是支持的。

---

## 五、事後敏感度分析（明確標示為事後，不計入成績）

以下數字是看完標註表之後才算的，**不能當作本次原型的成績**，只能當作下一輪的假設：

| 判別規則 | 命中率（6 份樽頸臂） | 誤報率（6 份正常臂） |
|---|---|---|
| 總分 ≥ 3（**凍結閾值，正式成績**） | 2/6 = 33% | 0/6 = 0% |
| 總分 ≥ 2 | 4/6 = 67% | 0/6 = 0% |
| **只看 D5 供應受限單一維度** | 5/6 = 83% | 0/6 = 0% |
| 只看 D5，且只計 4 份可靠標籤 | 4/4 = 100% | 0/6 = 0% |

D5（供應受限）單獨的分辨力，明顯強過六維總分。原因看得出來：D3 積壓、D4 提價在正常年份一樣會出現（POWL FY2019 積壓 +61%、GNRC/ROK FY2019 都有已實施提價），它們是**景氣指標**而不是**樽頸指標**，把它們加進總分等於加噪音。

再說一次：這是 n=12 上的事後觀察，必須用新樣本重驗才算數。

---

## 六、成本量測（每份文本）

| 項目 | 平均 | 範圍 |
|---|---|---|
| MD&A 全文字元 | 74,023 | 31,690 – 160,588 |
| **方案 A：全文 token（估 ÷4）** | **18,506** | 7,922 – 40,147 |
| 預篩後候選句數 | 11.7 | 6 – 22 |
| **方案 B：候選句 token** | **787** | 343 – 1,904 |
| 壓縮比（A→B） | **23.5×** | — |

機器時間（穩態、不含除錯）：抓取每份約 2 個 EDGAR 請求，抽取＋預篩每份 < 1 秒。
本次 12 份由零開始的實際掛鐘時間約 40 分鐘，絕大部分花在 MD&A 抽取的除錯上（見報告第五節）。
