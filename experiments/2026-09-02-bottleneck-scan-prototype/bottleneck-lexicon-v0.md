# 樽頸語言判別清單 v0（bottleneck lexicon v0）

凍結日期：2026-09-02
凍結狀態：**在讀任何一份文本之前寫死**。掃描開始後本檔不得修改；要改就開 v1 並重跑全部文本。
用途：KARST-142 原型，判別一份公司申報文本（MD&A 一節）裡有沒有「實體經濟樽頸」語言。
非用途：不產生任何投資訊號、不排名、不入庫。

---

## 一、定義

**樽頸語言（bottleneck language）**：公司在自己的申報文本裡，描述**其產品或投入品的供給側受到實質限制**，
而且該限制**正在發生或已經發生**（不是假設、不是風險提示、不是已解除的回顧）。

樽頸的經濟含義是：需求大於當期可交付的供給。故判別重點在於**供給受限的證據**，
不是需求好壞本身。「訂單很強」不算樽頸；「訂單很強而我們交不出貨」才算。

---

## 二、六個維度（D1–D6）

每份文本對每個維度給 **0 或 1**：有至少一句合資格的實質陳述 = 1，否則 0。
總分 0–6。

### D1 交付週期拉長（lead time extension）
語意：交付前置期、報價到交付的時間變長；客戶要更早落單。
英文種子詞：lead time(s) extended / lengthened / elongated、longer lead times、
extended delivery schedules、delivery lead times increased。
合資格例：「lead times for certain components extended from 8 to 26 weeks」。
不合資格：「we may experience longer lead times」（假設語氣）。

### D2 產能受限／滿載（capacity constraint / full utilization）
語意：自身產能不足以應付需求；產線滿載；正在擴產以解除限制。
英文種子詞：capacity constraints、capacity constrained、at or near full capacity、
production limited by、manufacturing capacity was insufficient、
expanding capacity to meet demand、adding lines/shifts to increase output。
合資格例：「our manufacturing capacity was fully utilized throughout the year」。
不合資格：純粹資本開支計劃陳述，無「受限」語意的擴產（例行 capex）。

### D3 積壓訂單增加（backlog growth）
語意：未交付訂單額增加，或積壓覆蓋期拉長。
英文種子詞：backlog increased / grew / record backlog、
remaining performance obligations increased、orders exceeded shipments、
book-to-bill above 1（且文中作為供給跟不上的證據）。
合資格例：「backlog at year end was $1.2 billion, up 45%」。
不合資格：backlog 下降或持平；backlog 只在會計政策段落出現而無變動描述。

### D4 提價能力（pricing power realised）
語意：**已實施並取得**的漲價，或以價格作為配置稀缺供給的手段。
英文種子詞：price increases implemented / realized、pricing actions contributed to
revenue growth、higher average selling prices、surcharges。
合資格例：「price increases contributed 6 points to organic growth」。
不合資格：「we intend to raise prices」（未實施）；成本上升而未提到成功轉嫁。

### D5 供應受限（input supply constraint）
語意：關鍵投入品（零件、原材料、晶片、物流、產能外包）取得受限。
英文種子詞：supply constraints、component shortage(s)、allocation from suppliers、
unable to obtain sufficient、supply chain disruptions affected shipments、
sourced on the spot market at higher cost、freight capacity constraints。
合資格例：「semiconductor shortages limited our ability to fulfil orders」。
不合資格：一般性「supply chain risk」風險語言而無當期影響描述。

### D6 訂單見度延長（demand visibility extension）
語意：因為交付排期拉長，公司對未來收入的可見度延長（已售罄至某期、產能已被預訂）。
英文種子詞：sold out through、capacity is committed / reserved through、
visibility into 20XX、multi-year supply agreements to secure capacity、
customers placing orders further in advance。
合資格例：「our 2025 production is effectively sold out」。
不合資格：一般業績指引。

---

## 三、排除規則（避免假陽性）——**判別的核心**

一句陳述必須全部通過以下四關才記為命中：

- **R1 語氣關**：必須是**已發生／正在發生**的陳述（過去式或現在式敘述）。
  情態動詞（may、could、might、if）、條件句、前瞻聲明段落內的句子 → 不算。
- **R2 位置關**：只採 MD&A（Item 7 / Item 2）正文。
  風險因素（Item 1A）、法律程序、前瞻性陳述免責段落 → 不算。
- **R3 方向關**：必須是**限制加劇或持續**。
  明確描述限制**已緩解／正常化／回復**的句子（eased、normalized、improved availability、
  supply chain has recovered）→ 不算命中，並在標註表另記為「緩解語言」。
- **R4 實質關**：必須指向公司自己的營運，且有可辨識的對象（某產品線、某零件、某地區）。
  純樣板句、行業泛論、同業轉述 → 不算。

---

## 四、判定閾值（凍結）

- 總分 **≥ 3 / 6** → 判為「樽頸期文本」
- 總分 **≤ 2 / 6** → 判為「非樽頸期文本」

閾值 3 的理由：單一維度容易被會計語言污染（例如 D3 backlog 在正常年份也會增長），
兩個維度仍可能是巧合；三個以上維度同時出現才構成「供給受限」的一致敘事。
本閾值在看文本前定死，掃描後不得回頭調整。

---

## 五、三個要量的數（凍結定義）

- **命中率（hit rate）**：事後已知樽頸期文本中，被判為「樽頸期文本」的比例。
- **誤報率（false positive rate）**：事後已知正常期文本中，被判為「樽頸期文本」的比例。
- **每份成本**：該份文本的輸入 token 量（以字元數 ÷ 4 估算）與判讀時間。

---

## 六、樣本設計（凍結）

6 家公司 × 2 個時點 = 12 份 MD&A。
每家取「事後已知樽頸期」與「事後已知正常期」各一份年報（10-K）的 Item 7。

| 公司 | 樽頸期（事後已知） | 樽頸期理由 | 正常期（對照） |
|---|---|---|---|
| ENPH | FY2021 | 微逆變器晶片短缺、物流受限 | FY2019 |
| GNRC | FY2021 | 家用發電機需求爆發、產能追不上 | FY2019 |
| ROK | FY2022 | 工業自動化晶片配額、積壓創高 | FY2019 |
| POWL | FY2024 | 電氣設備積壓創高、交付排期拉長 | FY2019 |
| BE | FY2024 | 數據中心電力需求、產能擴張中 | FY2019 |
| ETN | FY2023 | 電力設備週期、積壓與交付期拉長 | FY2019 |

**已知侷限（寫在前面，不是事後辯解）**：全部對照期都是 FY2019，
故「樽頸狀態」與「年份」在本樣本裡共線。本原型不能分辨清單量到的是樽頸，
還是 2019 年與 2021–2024 年之間任何其他寫作習慣差異。這是 n=12 小樣本的必然代價，
判詞須連此侷限一併交代。
