# 指引解析器抽查(執行口徑 v1.2 第 5 項)

> 產出:票 A″ 第五步。抽查對象 `cache/guidance_parsed.jsonl`(本次建池共 6,454 筆紀錄)。
> 種子 20260912;樣本 `cache/audit_sample_raw.jsonl`。逐句核對由工人(DeepSeek 執行臂)親自讀原句判。
> 原文來自 EDGAR EX-99.1,**原文不入庫**;下表只引首 ~150 字作核對依據。

## 一、方法

- 抽樣:全體紀錄**簡單隨機抽 40 筆**(第 5 項「40 句抽查」字面),逐筆問三件事:
  ①抽出來的數是不是所指指標的指引值(值/指標對不對);②新舊值對不對(舊值可為空);
  ③`raise_flag`(上調)方向對不對。
- 三種判詞:
  - **對** —— 值與方向都對。
  - **值錯** —— 抽出的是別的指標、別的項目(成本、併購貢獻、平均售價、腳註上標)或只是舊值/上界漏截。
  - **方向錯** —— `raise_flag` 與句子語意相反(如「reaffirmed」「was raised」判反、「issued」判成上調)。
- 另**加抽 20 筆「`metric=revenue` 且 `raise_flag=1`」**(種子 20260913)——這批才是會影響入池與否的那一批
  (入池只認收入上調)。

## 二、四十句逐句核對

| # | 指標 | 抽出值 | 舊值 | 判詞 | 依據(原句首段;判詞理由見括號) |
|---|---|---|---|---|---|
| 01 | eps | 2.55–2.70 | — | **對** | "affirmed its full-year diluted earnings per share guidance to be in the range of $2.55 to $2.70"(affirmed → 非上調,判 0 正確) |
| 02 | revenue | 19.7 | — | **值錯** | "…increase in SG&A as a percent of net sales from 19.7% to…"(是費用佔收入比,不是收入指引) |
| 03 | operating_income | 102 | — | **值錯** | "expects consolidated revenue of about $102 billion, an adjusted operating margin of approximately 13.7%…"(102 是**收入**,不是經營利潤) |
| 04 | cash_flow | 30.7 | — | **值錯** | "Resort EBITDA Margin is expected to be approximately 30.7%…"(是**利潤率**,不是金額) |
| 05 | eps | 5.62–5.82 | — | **對** | "Increased Full-Year 2018 Comparable EPS Forecast Range (non-GAAP) of $5.62 to $5.82"(increase → 判 1 正確) |
| 06 | revenue | 1.3 | — | **對** | "the Company expects revenue to approximate $1.3 billion" |
| 07 | revenue | 359.6 | — | **值錯** | "Adjusted EBITDA in the fourth quarter was approximately $359.6 million, in line with guidance…"(是 EBITDA,且為事後數) |
| 08 | cash_flow | 500–550 | — | **對** | "expects fiscal year 2022 Adjusted EBITDA to be approximately $500 million - $550 million" |
| 09 | cash_flow | 109(單值) | — | **值錯、方向對** | "raising our Adjusted EBITDA outlook … to a range of **negative** $109 million to **negative** $106 million, from a previous range of negative $126 million to negative $122 million"(漏負號與上界;old 未抽到) |
| 10 | revenue | 86,000 | — | **值錯** | "Average weekly sales … decreased to $86,000 for the first quarter of 2017"(是實際平均週銷售,不是指引) |
| 11 | revenue | 25–30 | 2.0 | **值錯(舊值)** | "initiating its full-year 2021 net sales growth guidance to be approximately 25 to 30% compared to the prior year … includes approximately 2% of favorable impact from acquisitions"(新值對;舊值 2% 是併購影響,不是舊指引) |
| 12 | cash_flow | 25–35 | — | **對** | "reaffirmed its financial guidance for fiscal 2016 … adjusted EBITDA of $25 million to $35 million"(reaffirmed → 判 0 正確) |
| 13 | cash_flow | 6.5 | 3.3(前句) | **值錯(舊值)、方向錯** | "The Company also **issued** its full-year 2025 cash flow from operations guidance of approximately $6.5 billion"(首次發布不是上調;舊值取自別句) |
| 14 | eps | 7.5(單值) | — | **值錯(上界漏截)** | "reaffirming our 2017 full-year adjusted diluted EPS growth guidance of **7.5% to 9.5%**" |
| 15 | cash_flow | 293(單值) | — | **值錯、方向錯** | "raised the mid-point and narrowed the range … **from** between $293 million and $307 million **to** between $302 million and $314 million"(抽到**舊**區間下界) |
| 16 | eps | 15.10–15.60 | — | **對** | "reported EPS guidance raised $2.05 to the range of $15.10 to $15.60" |
| 17 | eps | 11.20–11.70 | — | **對** | "reaffirmed its full year 2020 earnings guidance range of $11.20 to $11.70 per diluted share" |
| 18 | eps | 2.00–2.15 | — | **對** | "we are raising the full-year adjusted earnings guidance to $2.00 to $2.15 per share" |
| 19 | cash_flow | 2.0 | — | **值錯** | "expects its full year adjusted EBITDA **2** to be between $236 million and $241 million"(抽到腳註上標「2」) |
| 20 | revenue | 175–185 | — | **對** | "we expect revenue to be in the range of $175 to $185 million" |
| 21 | revenue | 9.300–9.410 | — | **對** | "we expect net revenue to be in the range of $9.300 billion to $9.410 billion" |
| 22 | eps | 6.75–7.05 | — | **對** | "raising … our Adjusted EPS guidance to a range of $6.75 to $7.05" |
| 23 | revenue | 222.5–223.0 | 19.6(前句) | **值錯(舊值)** | "**Increased** fiscal year 2024 total revenue guidance range to $222.5 million to $223.0 million"(新值與方向對;舊值來自別句) |
| 24 | eps | 2.55–2.65 | — | **方向錯** | "the guidance range for full-year Adjusted Diluted Earnings Per Share was **raised and narrowed** to $2.55 - $2.65"(值對,但未判上調) |
| 25 | revenue | 2.36–2.56 | — | **值錯(指標)** | "Revised fiscal year 2016 **Class A earnings per share** guidance to $2.36 - $2.56"(是 EPS,不是收入) |
| 26 | eps | 0.90–1.40 | — | **對** | "Q3 Non-GAAP EPS was also a record at $1.66, above the guidance range of $0.90 to $1.40" |
| 27 | revenue | 4.9–5.3 | — | **對** | "Full year 2025 revenue guidance of $4.9 billion to $5.3 billion, reaffirm…" |
| 28 | revenue | 50.0 | — | **值錯** | "our revenues during the third quarter 2015 **decreased by** $50.0 million"(是變動額,不是指引) |
| 29 | revenue | 20.0 | — | **值錯** | "roughly $20 million … impact from cost inflation of materials, inbound freight…"(是成本影響,不是收入指引) |
| 30 | revenue | 4.50–4.80 | — | **對** | "introducing a fiscal year 2024 revenue guidance range of $4.50 billion to $4.80 billion"(首次指引 → 判 0 正確) |
| 31 | revenue | 5.75–6.05 | — | **值錯(指標)** | "both **GAAP EPS and Adjusted EPS** of $5.75 to $6.05"(是 EPS,不是收入) |
| 32 | revenue | 9.18–9.23 | — | **對** | "Initiates Fourth Quarter FY24 Revenue Guidance of $9.18 Billion to $9.23 Billion" |
| 33 | revenue | 340–350 | 310–320 | **對** | "increasing its full year 2018 total revenue guidance range to $340 to $350 million, up from $310 to $320 million"(新舊值與方向全對) |
| 34 | revenue | 1.09–1.11 | — | **對** | "now expects net sales to grow to between $1.09 billion to $1.11 billion" |
| 35 | cash_flow | 1.2–1.35 | 1.0(前句) | **值錯(舊值)** | "now expects its full-year free cash flow to be in a range of $1.2 billion to $1.35 billion"(新值對;舊值來自別句) |
| 36 | eps | 22.50–23.00 | — | **方向錯** | "…to realize our full-year guidance of $22.50 to $23.00 per share, **an increase of 16 to 19 percent**"(「increase」是相對**去年**,不是相對舊指引) |
| 37 | eps | 0.53–0.56 | — | **值錯** | "…**above the previously provided outlook** of $0.53 to $0.56"(抽到的是**上一次**指引,不是新指引) |
| 38 | eps | 7.10–7.25 | — | **對** | "we are also **raising** our adjusted EPS outlook …"(上調,判 1 正確) |
| 39 | eps | 2.43–2.47 | — | **對** | "We expect diluted EPS of $2.43 to $2.47 for the full year 2015" |
| 40 | revenue | 2.12 | — | **值錯(指標)** | "reports 2020 earnings of **$2.12 per share** supported by record fourth quarter sales…"(是 EPS,不是收入) |

**四十句小結**:對 19;值錯 13;方向錯 2;新值對而舊值/上界有誤 6。
**錯誤率(任何一欄有錯)= 21/40 = 52.5%**;**材料錯(值/指標錯 + 方向錯)= 15/40 = 37.5%**。

## 三、加抽 20 筆「收入上調」子集(會影響入池的那批)

種子 20260913,自 578 筆 `metric=revenue ∧ raise_flag=1` 抽 20 筆。

| # | 抽出值 | 舊值 | 判詞 | 依據 |
|---|---|---|---|---|
| 01 | 340–345 | — | **對** | "raising our outlook for net sales, now to be in the range of $340 million to $345 million" |
| 02 | 590–605 | 2.318–2.348(前句) | **值錯(舊值)** | "expects third quarter 2021 adjusted revenues to be $590 - $605 million"(新值對;舊值取自前一句的全年指引) |
| 03 | 39(單值) | 36 | **值錯(上界漏截)** | "constant currency revenue growth of approximately **39% to 41%** … compared to its previous outlook of 34% to 36%" |
| 04 | 145(單值) | — | **值錯(舊值缺)** | "Raising FY 2022 Total Revenue Guidance to $145 Million **From $130 Million Previously**"(單值 from 未抽) |
| 05 | 700(單值) | — | **值錯(上界漏截)** | "raising … revenue guidance for 2024 to **between $700 million and $710 million**" |
| 06 | 36–40 | — | **對** | "increasing its full-year 2022 net sales guidance to be approximately 36 to 40%" |
| 07 | 17.5 | — | **值錯** | "The increase in net sales guidance reflects … the Back to Nature acquisition, which is expected to contribute approximately $17.5 million"(是併購貢獻,不是指引) |
| 08 | 235–238 | — | **對** | "raising full year fiscal 2024 revenue guidance to be $235 to $238 million" |
| 09 | 21.0 | — | **值錯** | "Revenues in the East segment **increased by** $21.0 million in the fourth quarter 2015"(是分部收入變動額) |
| 10 | 127–130 | 125–128 | **對** | "Increased full year 2022 revenue guidance to a range of $127 million to $130 million, from its previous guidance range of $125 million to $128 million" |
| 11 | 965–980 | — | **對** | "raising the low end of its previous revenue guidance by $5 million to a revised range of $965 million to $980 million"(舊指引未在同句 → old_missing,判上調正確) |
| 12 | 157–177 | — | **對** | "raises its full year 2025 revenue outlook to be in a range of $157 to $177 million" |
| 13 | 1,210–1,225 | 1,170–1,185 | **對** | "Full year 2018 net sales guidance increased to $1,210 - $1,225 million, compared to prior guidance of $1,170 - $1,185 million" |
| 14 | 88(單值) | — | **值錯** | "Total revenues **increased 88% to $22.7 million** in the quarter"(是實際增幅,不是指引) |
| 15 | 3.75(單值) | — | **值錯、方向錯** | "raised its full year 2024 revenue growth outlook **from a range of 3.75% to 4.75% to a range o**…"(抽到**舊**區間下界) |
| 16 | 1.15(單值) | — | **值錯** | "we are proud to **raise** our full-year outlook for total written premium and revenue, and … a special dividend"(1.15 不是該指引值) |
| 17 | 80–82 | — | **方向錯** | "revenues of $83.0 million that was **higher than our outlook range of $80.0 million to $82.0 million** that we provided in May 2024"(抽到的是**舊**指引區間) |
| 18 | 6.0 | 5.0 | **對** | "increased its 2018 full year organic sales growth estimate to ~6% … from the previous guidance of ~5%" |
| 19 | 244–247 | 225–230 | **對** | "Revenue is now anticipated to be $244 - $247 million … an increase from previous guidance of $225 - $230 million" |
| 20 | 101(單值) | 92 | **值錯(指標)** | "**cost of coal sales** are now expected to be between $101.00 per ton and $107.00 per ton … up from the prior guidance range of $88.00 per ton to $92.00 per ton"(是**成本**,不是收入) |

**二十筆小結**:對 9;值錯 7;值錯(舊值/上界)4。
**錯誤率 = 11/20 = 55%**;**材料錯(會把非指引事件當成收入上調而放進池)= 7/20 = 35%**。

## 四、結論與處置

1. **兩次抽查的錯誤率都遠高於執行口徑第 5 項的 15% 門檻**(全體 52.5%、入池相關子集 55%)。
   按規格「>15% 就舉手」,本項**已舉手**,見 `執行紀錄——A3.md`。
2. 錯誤集中在三類,成因明確、不是隨機:
   - **指標張冠李戴**:同一句同時講收入與 EPS/成本/EBITDA 時,取數只看「離指標字眼最近的區間」,
     對「$101 per ton 的煤成本」「$5.75–6.05 的 EPS」這類仍會取錯(40 筆中 7 筆)。
   - **舊值取自別句**:「前句」「前句單值」兩條回退規則會把鄰句的數當成舊指引(40 筆中 4 筆),
     令上調判詞失去依據(但方向多數仍對)。
   - **上界/負號漏截**:"$700 million and $710 million"「negative $109 million to negative $106 million」
     這類寫法區間正則接不上,只取到單值(40 筆中 4 筆)。
3. **對本場考試的實際影響**:指引路徑只佔入口池一小部分——入口池 1,802 宗之中,
   「只靠指引」(指引)92 宗 + 「兩者」98 宗 = 190 宗(10.5%);其餘 1,612 宗(89.5%)靠加速訊號,
   與本解析器無關。按 35% 材料錯率推,池內約 **60–70 宗**(約 3.6%)是誤收;84 個樣本中約 **3 宗**。
4. **建議(待裁,不自行改規則)**:三條路——(a)照收,把 10.5% 的指引路徑標為已知有雜訊並在成績報表另列;
   (b)只剔「只靠指引」的 92 宗,保留「兩者」;(c)先收緊解析器(單值 from、區間正則、指標消歧)再重建入口池。
   本票**照原規則完成建池與鎖定**,以上三個選項原樣交裁。
