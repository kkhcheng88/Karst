---
id: KARST-186
title: 隱含預期計算器抽取缺陷修復——A-047(AXTI 長期投資性質)與 A-048(LULU 現金被當 0)兩處淨負債取數規則釘死,對 KARST-184 六十家過閘名單重跑並比對前後差異
type: task
createdAt: 2026-09-08
risk: low
model: sonnet
fits: D-169 第 9 條(計算器分開輸出長期價值範圍與一年回報);KARST-184 舉手第四項——共用工具兩處抽取缺陷未改,建議另開票同修並重跑
dependsOn: []
claimedBy: calcfix186-sonnet
deliverable: KARST-D04
closed: 2026-09-11
---

## 工作內容

工具在 strategy/tools/implied_expectations.py,說明在 strategy/tools/README.md。兩個缺陷:(一)A-048:LULU 的現金標籤未被抽到而當 0,淨負債誇大 15.15 億——查 companyfacts 內 LULU 實際用的現金/等價物標籤(CashAndCashEquivalentsAtCarryingValue / CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents 等),把取數改成有序後備清單並在缺數時印警告而不是靜默當 0;(二)A-047:AXTI 的 LongTermInvestments 由 0 跳到 2.986 億,要讀 AXTI 最近一份 10-Q 附註(data/ 內 EDGAR 快照或 SEC 網站)判斷是可變現金融資產還是策略性股權投資;前者計入淨現金,後者不計,把判斷規則寫入 README 並在假設冊把 A-047、A-048 改為 holds 或 refuted 附證據。修完後對 research/2026-09-methodology/2026-09-08-①候選池走通/ 內六十家過閘名單重跑「三個數」,輸出前後差異表(每家淨負債差、基準每股值差、隱含增速差),標出結論由入選變不入選或反向的家數。不改五家的候選卡結論——只落差異表,由主 agent 判要不要重評。

## 驗收條件

- [x] 現金/投資取數改為有序後備清單,缺數印警告;A-047 與 A-048 在假設冊更新狀態附證據
- [x] 六十家重跑差異表落檔,標出結論翻轉的家數與名單
- [x] README 記下淨負債取數規則與 LongTermInvestments 的判斷規則
- [x] 不改候選卡與票 KARST-184 的結論;不 commit;含中文檔案只用 Read/Write/Edit

## 結果

**兩處缺陷都改了,對盤數的實際影響只落在一家(LULU),另外六家非候選公司的淨負債也被
低估過,但未觸發任何機械判準翻轉。**

1. **A-048(現金取數):`strategy/tools/implied_expectations.py` 的 `instant_series()` 由
   「第一個有資料的標籤就用」改成「有序後備清單——取第一個覆蓋到最近一季前後 200 日內的
   標籤」,全部候選標籤都太舊時退回合併結果並印警告,不再靜默當 0。修好後直接抽取 LULU
   現金 = 15.147 億,與 KARST-184 當時人手更正的 15.15 億幾乎完全吻合——**證明 KARST-184
   的 LULU 候選卡數字本身沒有錯,只是共用工具當時還沒修**。CASH_TAGS 加入
   `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` 等後備標籤。
2. **A-047(AXTI 長期投資性質):讀 AXTI 2026-06-30 10-Q(Note 2「Investments and Fair
   Value Measurements」)核實 2.986 億美元全部是國債(2.383 億)、公司債(0.574 億)、
   存款證(0.078 億),是可流通證券;原本擔心混入的原材料公司股權投資(1,410 萬)另外
   報在「Other assets」,不在 LongTermInvestments 這一格內——**假設成立,標籤本身沒有
   把兩者混在一起**。這一項對數字沒有影響,只把判斷規則(遇大幅波動或已知有合營持股時,
   要讀 10-Q 附註核組成,不能只憑標籤名字放行)寫入 README。
3. **假設冊:A-047 狀態由 unverified 改 holds(附 10-Q 出處與金額核對)。A-048 原本已被
   KARST-184 標為 overturned 附完整診斷,本票是把它診斷出的代碼缺陷實際修掉——狀態不用
   再改,診斷本身已經是最終判決。**
4. **六十家重跑(通用機械式假設,不含個股判斷,只用來分離取數缺陷的影響):**
   51 家淨負債前後一致(差額 <100 萬美元)。**9 家有實質差異**:QCOM(+90.1 億)、
   SEDG(+3.32 億)、VIAV(+2.42 億)、SANM(+2.15 億)、SAIA(+1.00 億)、
   AMKR(+1.57 億)、FSLR(+0.38 億)、ADTN(−0.01 億,微小)、**LULU(−15.15 億)**。
   **方向要看清楚:除 LULU 一家之外,其餘 8 家全部是淨負債被低估(有息負債漏計),
   不是像 A-048 那樣的現金漏計**——這支抽取程式在兩個方向都可能出錯,不是單一方向的
   系統性偏差。**機械式「基準每股值 > 現價」判準,60 家之中沒有一家翻轉方向**(9 家
   差額都不足以跨過現價那條線)。詳細差異表見
   `research/2026-09-methodology/2026-09-08-①候選池走通/2026-09-08-取數修復後六十家重跑差異.md`,
   原始數據見同目錄 `rerun_60_before_after.csv`。
5. **五家候選卡:沒有一家的三個數受本次修復影響。** LULU 見上(工具現在自動算出
   KARST-184 當時人手更正的同一個數);TDC、ON、ENPH、ARM 淨負債差額 <100 萬美元。
   **候選卡結論一律沒有改動,是否要重評交由主 agent 判斷。**

## 留言

raised: 六十家之中 QCOM、SEDG、VIAV、SANM、SAIA、AMKR 這 6 家不在候選五家之列,但淨負債
過去被低估的幅度不小(SEDG/VIAV/SANM 相對市值都有感)。這些公司若日後被抽入候選研究,
建議先確認用的是修復後的工具重新建帳,不要沿用任何舊快取或舊截圖的三個數。

raised: A-047 只在 AXTI 一個樣本上核實 LongTermInvestments 的性質,倉內其餘公司未逐家
抽查,一般性風險(標籤誤把非證券投資算進 LongTermInvestments)沒有排除;README 已寫明
「大額波動的長期投資格仍應覆核 10-Q 附註」這條規則,但沒有(也不在本票範圍內)去驗證
其餘 59 家是否乾淨。若之後有候選公司的長期投資格出現類似 AXTI 的大幅跳動,應照這條規則
另外核一次,不能假設本票的結論可以直接套用。
