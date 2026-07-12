# Expectations Investing（Mauboussin & Rappaport）—— Supercycle Magnifier 模型蒸餾（2026-07-11）

> 對應 `docs/2026-07-09_magnifier_model_plan.md` 步驟 C 第二本書（Chancellor 之後）。目的:蒸餾
> Michael Mauboussin & Alfred Rappaport 嘅 *Expectations Investing*（2021 二版）,睇佢嘅
> expectations-investing 框架可唔可以填補計劃入面「未解決」嘅問題,尤其 feature #3(距底部幾遠,
> 唔用 trailing P/E)嘅量化方法。
>
> **方法**:PDF(262 頁,`C:\projects\Investment\ebooks\Fundamental Value & Growth\Michael
> Mauboussin\Expectations Investing.pdf`)用 PyMuPDF 全文抽取到
> `thesis/.raw/expectations_investing_fulltext.txt`(gitignored,可用
> `backtest/experiments/_extract_expectations_investing.py` 重新產生)。全書 12 章分 4 段(Ch.1-3 /
> Ch.4-5 / Ch.6-7 / Ch.8-12)逐字讀完並帶頁碼引用核對 —— 兩段由 subagent 平行讀(Ch.1-3、Ch.8-12,
> 已核實),兩段(Ch.4-5、Ch.6-7)因協調流程問題改由主 agent 直接逐行讀源文件核實。全部引用嘅頁碼
> 係書本身印刷嘅內頁碼(唔係 PDF 檔案頁碼),可以直接去 §4 對照表用 PDF 頁碼複查。
>
> **本文唔設計 scorecard**(D/E 步驟由用戶面談做);淨係蒸餾書入面嘅框架同引句。

## 0. 一句結論

呢本書冇提供一條「攞嚟即用」、專門標籤做「週期股 trailing P/E 替代公式」嘅方法 —— 呢個 gap
同 `docs/2026-07-09_magnifier_literature.md` §4/§9 已經誠實承認嘅「冇專門期刊論文」一致,兩個
獨立源頭都印證咗呢個係真.地基較薄嘅一環。但佢嘅核心機制(把股價倒轉解讀成隱含嘅 sales
growth/margin/investment/cost of capital/forecast period,一次都唔掂 trailing EPS 或 P/E)
**結構性咁完全避開咗** trailing-P/E 喺蝕錢/週期股度失效嘅問題 —— 呢個唔係為週期股度身訂造,
而係佢由頭到尾嘅估值方法論本來就唔靠 EPS。喺呢個地基上面,書入面**三個可以直接攞嚟做 feature #3
(距底部量化)嘅具體數值槓桿**:①threshold margin / value pool spread 可以跨週期年份運算(Ch.3-4);
②market-implied forecast period(= competitive advantage period / fade rate)相對同業嘅比較
(Ch.5);③real options 估值俾蝕錢/pre-revenue 嘅 supercycle node(Ch.8)。另外三個重要發現:
**operating leverage(feature #1)有正式框架同工作實例**(Ch.3);**case 庫「週期頂前槓桿式擴產/併購
= 死亡 marker」呢個發現被書入面三個獨立角度交叉印證**(game theory sidebar、實例、引用文獻,Ch.4/9/12);
**crowding/情緒(feature #5)冇對應 analyst-dispersion 框架,但有三個更嚴謹嘅price-revealed 替代品**
(imputed option value 佔價比重、market-implied forecast period 相對同業、explicit probability-weighted
expected value)。

---

## 1. 直接填補計劃「未解決」問題 —— Feature #3(距底部幾遠,唔用 trailing P/E)

### 1.1 根源機制:PIE 全 DCF 模型由頭到尾唔掂 EPS(Ch.1-2)

書開宗明義批評三個「普遍誤解」之一係「P/E 倍數決定價值」(p.10)。核心批評(p.15,標題
"Belief: Price-Earnings Multiples Determine Value / Reality: Price-Earnings Multiples Are a
Function of Value"):

> "Since we have the denominator (earnings per share, or E), the only unknown is the appropriate
> share price, or P. We are therefore left with a useless tautology: To estimate value, we
> require an estimate of value... The price-earnings multiple does not determine value but
> rather derives from value. Price-earnings analysis is not an analytical shortcut. It is an
> economic cul-de-sac."

替代方法(p.8-9、21,Ch.5 詳細展開):唔係由基本因預測現金流推值,而係**倒轉**——由觀察到嘅
股價出發,solve backward 揾出令呢個價成立嘅 operating assumptions(value drivers)。呢個做法
從根源避開咗 trailing-P/E 問題,因為佢由頭到尾嘅輸入係 sales growth %、operating margin %、
incremental investment rate %、cash tax rate、cost of capital、forecast period —— **一個蝕錢
週期股嘅 trough margin 只係一個負數,係合法輸入,唔似 P/E 咁除完變無意義**。呢個唔係書為
cyclical 度身訂造嘅方法,而係佢成套方法論本來就唔靠 EPS 嘅副產品 —— 但正正因為咁,先啱用喺
magnifier 嘅 trough 買入時機。

補充(Appendix, p.16-18,同 p.53 呼應):盈利增長 ≠ 價值增長 —— 只有新投資回報**高於**資金成本,
價值先會升;等於資金成本,價值持平;**低於**資金成本,即使盈利表面上升,價值仍然下跌
("good news / bad news / no news" 框架)。對 magnifier 而言可測試:trough 之後 volume 回升
只有喺 incremental margin 跑贏資金成本先真係創造價值,呢個係一個可測試、唔靠 P/E 嘅條件。

### 1.2 Threshold margin + value pool analysis(Ch.3-4)—— 可跨週期年份運算嘅估值錨

**Threshold margin**(p.53-55)定義:令 shareholder value added = 0 嘅 operating margin
(由 DCF/資金成本反解)。工作實例(Table 3.2, p.54):假設 margin 15% → 加咗 $12.69 value;
threshold margin 14.08% → 加咗 $0.00 value。四條原則(p.54-55):value-added 幅度同「預期
margin 對 threshold margin 嘅 spread」成正比;incremental investment rate 越高,threshold
margin 越高(sales growth 對 value 嘅貢獻越細)。

**Value pool analysis**(Fig.4.2, p.63):橫軸 = 規模(sales/assets),縱軸 = **operating margin
減 threshold margin** 嘅 spread。書明確話:「In stable industries, the changes in value creation
are modest from year to year, whereas substantial shifts in value suggest limited competitive
advantages」(p.63)。

**★ 對 Karst 嘅可用性**:threshold margin 由 DCF/資金成本數學反解出嚟,本質上係**價格隱含**
(price-implied)、對資金結構敏感嘅估值錨,唔係 naive trailing average。可以喺歷史週期年份
(trough 年 vs peak 年 vs 現時)逐年計 candidate 嘅 threshold-margin spread,直接做「距底部幾遠」
嘅量化輸入 —— 距底部近 = spread 貼近或低於 threshold(甚至負);正常化/mid-cycle margin 相對
threshold 嘅 spread 幾大 = 距頂幾遠。呢個唔靠 trailing P/E,靠 margin 軌跡 + 資金成本。

### 1.3 Market-implied forecast period(= competitive advantage period / fade rate)(Ch.5)

定義(p.91):市場隱含畀公司「賺超過資金成本回報」嘅年期。書明確話呢個名同「value growth
duration」「competitive advantage period」「fade rate」係同一件事。美股一般 5-15 年,強競爭力
公司可以到 30 年,弱嘅可以低到 0 年。計法:延長 DCF 顯式預測期,直到 present value 等於現價
為止(Domino's 案例,Table 5.1:解出 8 年)。

Sidebar(p.115,"WHAT ABOUT THE COST OF CAPITAL AND THE MARKET-IMPLIED FORECAST PERIOD?")
提供直接操作指引:

> "If a company's market-implied forecast period is substantially longer or shorter than that of
> its industry peers... a relatively short market-implied forecast period may signal a buying
> opportunity and a long period may signal a selling opportunity."

仲有一個隱藏效應:若隱含年期一年之後**維持不變**(冇縮短),本質上等於市場悄悄調高咗期望
(投資者「贏咗」額外一年嘅超額回報) —— 呢個係一個可以逐季追蹤嘅 momentum 訊號。

**★ 對 Karst 嘅可用性**:呢個係全書最可以直接搬過去用嘅單一數字。對 magnifier candidate,喺
trough 度(供給受限/定價權剛開始成形,但盈利仲蝕緊)去 solve 市場隱含 forecast period —— 如果
呢個數字相對「正常化後應該有嘅同業/歷史週期」水平明顯偏短甚至趨零,而你自己嘅結構分析
(§2.5 護城河 + operating leverage)支持一個長好多嘅期望,呢個差距本身就係 expectations gap,
即 feature #3 想搵嘅「距超級週期起點有幾遠」嘅另一把尺 —— 唔靠 trailing 盈利,靠 DCF 反解。

### 1.4 Real options 估值(Ch.8)—— 蝕錢/pre-revenue supercycle node 嘅估值方法

五個輸入(Table 8.1,Black-Scholes 邏輯):S(項目現值)、X(行使投資成本)、σ(項目波動率)、
T(可延遲年期)、r(無風險利率)。書明確講:「We need not estimate a risk-adjusted discount
rate...because σ fully accounts for project risk」(p.136) —— 即完全唔靠 cost of capital
去調整風險,靠波動率。查表工具(Table 8.2)取代人手 Black-Scholes 計算。

三個明確結論(p.139-140):option value 隨 S/X、波動率、到期時間上升;**即使 S 遠低於 X(標準
NPV 判「唔值」),real option value 依然可以有意義**(distribution-expansion 例子:S=$30M,
X=$40M,傳統 NPV 唔通過,但 σ=50%/T=2yr 時 option value 仍有 $5.4M,即 S 嘅 18.2%);option
value 恆低於 S。波動率參考:大型股 35-45%,必需品 30-35%,IT 40-50%,**生科/年輕科技 50-100%**
(p.140)——呢個係一個現成、可以套用喺 pre-revenue SMR 型早期節點嘅波動率區間假設。

**★ 對 Karst 嘅可用性**:呢個直接對應計劃 §3b「SMR/次世代核 = EARLY,pre-revenue,最大
magnitude(10x option)但 binary」呢個判斷 —— real options 就係量化「binary option」嘅正式
工具,S<<X 都可以有意義嘅正估值,完全避開 DCF/P/E 兩個對負盈利名都失效嘅工具。仲有一個重要
風險提示:**reflexivity**(Soros,p.148-150)——股價本身唔係被動讀數,而係主動輸入:股價
插水 → equity financing/股票支付併購/股權留人都變難 → fundamentals 惡化 → 股價再插水。
對 pre-revenue 節點嚟講,real-option value 本身係脆弱嘅:股價崩盤可以令公司冇資本去行使
呢個 option,同底層機會本身好唔好無關 —— 呢個係倉位管理嘅硬約束,唔止係估值輸入。

另外書提供第二個獨立嘅 crowding/expectations-gap 量度:**imputed real-options value**
= 現價 − DCF 對現有業務嘅估值(用**固定**、analyst-consensus 嘅預測期,唔係反解嘅,以免
把 option value 誤植入基本盤,p.144)。2×2 矩陣(potential real-options value × imputed
real-options value)分四格:「毋須分析」/「買入候選」(高 potential/低 imputed)/「賣出候選」
(低 potential/高 imputed)/「要全面分析」(p.143-144)。

### 1.5 對 Feature #3 嘅淨判斷

書冇俾一條標籤做「週期股 trailing P/E 替代公式」嘅現成方法 —— 呢個確認咗
`2026-07-09_magnifier_literature.md` §4/§9 已經標注嘅地基較薄弱缺口係真嘅,唔係搜尋唔夠力。
但 PIE/DCF 反解機制**結構上就係**一個替代品(由頭到尾唔掂 EPS),而且提供**三條可以直接落地
嘅數值槓桿**:①threshold margin / value pool spread(可跨週期年份運算,§1.2);②
market-implied forecast period 相對同業(§1.3);③real options S/X 比率(蝕錢/pre-revenue
節點專用,§1.4)。三條槓桿嘅共通輸入係「normalized/mid-cycle margin + 資金成本」,唔係
「trailing 盈利」——呢個方向同計劃 §0 嘅 paradigm 校正(用 normalized/mid-cycle earnings、
距底部有幾遠,唔用 trailing PE percentile)完全一致,可以話係**方法論層面嘅實質支持**,
但要留意:呢啲槓桿本身唔係「週期股專用」工具,套用去 magnifier 案例需要人手判斷(揀邊年做
threshold margin 嘅基準年、點樣定義「正常化」margin)——書冇代做呢一步,呢個仍然要 D/E 步驟
(scorecard 設計,用戶面談)自己拆解。

---

## 2. 補充框架(唔直接答問題,但對模型有用)

### 2.1 Value driver 全套分解("expectations infrastructure")(Ch.3)—— 對應 Q2

三層結構:**Value Triggers → Value Factors → Operating Value Drivers**(Fig.3.1, p.46)。

- **Value triggers**(p.45,「引發 expectations revisions 嘅三大基石」):Sales、Operating
  costs、Investments。
- **Value factors**(六個,p.46-52):
  1. **Volume**(p.47)—— 銷量。
  2. **Price and Mix**(p.47-48)—— 售價變動 + 高/低毛利產品組合轉移(Goodyear 例子:
     2011-15 銷售跌 28%、銷量跌 8%,但靠 mix shift 去高階輪胎,營業利潤反升 ~50%、margin
     擴 6pt)。
  3. **Operating Leverage**(p.48-49)—— preproduction costs(產能/固定支出)壓低初期 margin,
     其後銷售增長攤薄固定成本,margin 隨之擴張(工作實例:margin 15% → 16.55% → 17.95%,
     Table 3.1)。**直接對應 feature #1**。
  4. **Economies of Scale**(p.49-51)—— 單位成本隨量增而跌(採購/生產/物流/學習曲線),明確
     同 operating leverage 分開(scale = 量帶來效率;leverage = 固定 preproduction 成本攤分)。
  5. **Cost Efficiencies**(p.51)—— 非規模相關嘅成本削減(流程重構/技術/外判)。
  6. **Investment Efficiencies**(p.52)—— 用更少資本產生相同銷售/利潤(McDonald's 模組化
     店舖設計、Mondelez 現金週轉週期改善)。
- **Operating value drivers**(量化輸出):Sales growth rate、Operating profit margin、
  Incremental investment rate,加上外生嘅 cash tax rate 同 cost of capital(Fig.2.1, p.24)。

Table 4.1(p.59)把每個 value factor 對應成具體盡職調查問題(行業增長、市佔率、churn、
價格/mix 變動、投資週期位置、規模經濟、流程重構、技術、營運資金管理)。

### 2.2 「Turbo trigger」三步識別法(Ch.6)—— Q2 落地方法論

基礎(Fig.6.2, p.98):兩個資料集(歷史表現、PIE)過兩個工具(expectations infrastructure、
競爭策略分析)。核心概念「turbo trigger」= 對 shareholder value 影響最大嘅 value trigger,
先揪出佢先分配分析精力(p.97)。

三步(p.99,Essential Ideas p.117 重申):

1. 估計 sales trigger 嘅高/低值,經四個 value factor(volume/price-mix/operating
   leverage/economies of scale)計出對應 margin,再計出對應 shareholder value 範圍
   (p.98-99, 113-114)。
2. 揀出真正 turbo trigger —— 測試 cost 或 investment 要偏離幾多先追得上 sales 嘅 value
   衝擊;若偏離幅度唔現實,sales 就係 turbo trigger(Domino's 案例:cost efficiencies
   要 ±400bp 先追得上 sales 對 17.5% PIE margin 嘅影響,判斷唔現實,確認 sales 係 turbo
   trigger,p.100, 115)。
3. 用 leading indicators 精煉高/低估計 —— 「measurable, current accomplishments that
   significantly affect the turbo trigger」(p.101-102),例:franchisee 盈利、同店銷售、
   顧客留存率、產品上市時間。「Two or three key leading indicators typically account for
   a substantial percentage of the variability in the turbo trigger」(p.102)。

**Expectations gap 嘅操作定義**是 PIE 同你高/低情景之間嘅股價 % 變動,唔係質性標籤
(Domino's:PIE sales growth 7% → $418;low 3% → $290(−30.6%);high 11% → $586
(+40.2%),p.115)。呢個 % delta 就係帶入 Ch.7 conviction sizing 嘅操作單位。

兩個明確標注嘅估計陷阱(p.102-104):**overprecision**(分析員/經理人劃嘅高低範圍普遍太窄
——引用一項研究:證券分析員嘅 90% 信心區間只有 64% 命中率,基金經理更差,得 50%)同
**confirmation bias**(讀 PIE 要保持中立,唔好帶自己觀點)。

### 2.3 Expected value / margin-of-safety × 收斂速度嘅 conviction sizing(Ch.7)

把 trigger 分析轉成 expected value(機率加權情景 payoff,p.119-120),同現價比較。兩個
conviction 情境(Tables 7.1-7.3):**高 value variability** 情況下,即使 consensus 情景機率
最高,寬幅波幅本身都可以觸發買/賣訊號;**低 value variability**(business model 穩定)情況下,
一定要賭贏 consensus 先有明確優勢。

買賣規則(p.125):expected value > 現價 = 有機會賺超額回報;優勢大小取決於①margin of
safety(現價相對 expected value 嘅折讓 %)②收斂速度(市場幾快 revise 期望)。**Table 7.7**
(全書最嚴謹嘅 conviction sizing 工具):現價 = expected value 嘅 80%、2 年收斂 → 年化超額
回報 ~12.5pp;60%、1 年收斂 → 70.7%;100%(即冇折讓)→ 0%(假設資金成本 6%)。

賣出三個理由(p.127):已達 expected value 且冇殘餘上升空間、有更好機會、期望被下修。行為
陷阱:escalation/sunk-cost trap、house-money effect、loss aversion(~2.5 倍)、confirmation
trap。稅務章節(p.129-130)提醒:換馬要計入資本利得稅,有時持有一隻已合理估值嘅股票好過賣咗
換另一隻只係輕微低估嘅。

**對 Q4(crowding 量化)嘅淨判斷**:書嘅答案係 expected-value 情景加權**本身**——分析員要
明確俾 low/consensus/high 三個機率;細嘅 consensus-weighted gap = 「已 priced in」/擠迫;
只有喺 non-consensus 加權下先睇到嘅寬 gap = 真.逆向注碼。Ch.6-7 全書冇 % 睇好分析員或
crowding index 呢類度量 —— 替代品係呢套機率加權機器,更嚴謹但要求分析員明確承諾一個機率
分布,唔係讀一個現成調查統計。

### 2.4 Operating leverage(Ch.3、Ch.9)—— 對應 Feature #1

除咗 §2.1 嘅定義同工作實例,Ch.9(Table 9.1, p.157)把生意分三類:**physical**(有形資產
主導,投資觸發 = 產能,可擴展性低)、**service**(人力主導,同樣低可擴展性)、**knowledge**
(人力主導但產品可複製,投資觸發 = 產品過時而非產能,可擴展性高)。

Operating leverage 機制(p.161):preproduction costs「invariably sunk」,隨銷量增長被攤薄。
書自己舉嘅例子正正係**太陽能板製造**(physical capacity business,p.161)—— 產能建咗喺低價
期,需求潮湧到填滿產能,margin 非線性擴張,幾乎係 magnifier 放大機制嘅字面描述。Knowledge/
藥廠業係極端版本:開發一隻藥 $1.4-2.6B,但「marginal cost of the two billionth pill is
cents on the dollar」(p.161-162)。

**關鍵限制**:operating leverage 明確被定性做**transitory**(暫時性)—— physical/service
公司產能滿咗就要再加,knowledge 公司要不斷出新品避免過時(p.162)。同時直接呼應 case 庫死亡
marker:「Companies that compete in cyclical industries...tend to overspend at cyclical peaks
and underspend at cyclical troughs」(p.167,舉 Paccar 做紀律反例),仲引述一項零售商研究:
剋制擴張嘅公司跑贏 ——「curing the addiction to growth」(p.167)。

### 2.5 競爭策略 / 護城河喺週期下行時仲存唔存在(Ch.4)—— 對應 Q3

**Five forces 框架**(p.64-71,Porter):substitution threat、buyer power、supplier power、
barriers to entry、rivalry。最關鍵一句直接解釋咗案例庫「贏家護城河獨立於商品價格」呢個
發現嘅**結構性原因**:

> "The variability of demand for the industry's goods or services is also important...Variable
> demand is especially relevant for industries with high fixed costs because of the risk of too
> much investment even at the peak level of demand. That excess capacity can lead to intense
> competition at the bottom of the cycle." (p.70)

即係:大多數商品型/週期型公司嘅「護城河」喺 trough 消失,唔係偶然,而係產業結構嘅必然
結果——高固定成本 + 高需求波動 = peak 期過度投資 → trough 期產能過剩 → rivalry 白熱化。
真正撐得過 trough 嘅贏家,一定係喺 Equation 4.1(Value created = Willingness to pay −
Opportunity cost,p.73-74)入面有**真.差異化**(高 willingness-to-pay)或**真.相對成本
優勢**,唔係單純「騎住商品價格上升」。

**可操作測試**(呼應 §1.2):value pool analysis(Fig.4.2)可以**逐年**運算,睇 candidate
嘅 operating-margin-minus-threshold-margin spread 喺週期下行(商品價格回落)時仲維唔維持
正數 —— 維持正數 = 真護城河(FSLR 型);spread 塌到零/負 = 純商品 beta(案例庫嗰堆太陽能
同業)。呢個直接把案例庫嘅質性發現轉成可以量化嘅逐年運算。

**Asset specificity**(p.68-69)補充一個微觀機制:「A firm whose assets are valuable only in
a specific market will fight vigorously to maintain its position」—— 資產專屬性越高,公司
喺下行期越有誘因死守市場,呢個可以做護城河耐久性嘅輔助訊號。

**★ 「Anticipating Competitor Moves」sidebar(p.73)—— 獨立由 game theory 角度印證案例庫
死亡 marker #2**:

> "Another illustration is the decision to add capacity at a cyclical peak. If a company adds
> capacity and its competitors do not, it earns significant incremental profits. If it forgoes
> the investment and its competitors add the capacity, the competitors earn the incremental
> profits. If all the players add capacity, however, no one benefits and the next cyclical
> downturn is more painful for all."

呢個同案例庫 §3c 發現 #2(「輸家喺週期頂前做槓桿式產能擴張/併購」= 死亡 marker)方向完全一致,
但係**由 game theory 邏輯獨立推導**,唔係靠事後歷史數據歸納 —— 屬於第三個獨立角度(見 §3)。

Disruptive innovation model(Christensen,p.71-73)同 information economics/aggregator-platform
框架(p.78-82)對 magnifier 主題相關度較低(偏軟件/平台生意),略去唔詳述。

### 2.6 資本紀律訊號(Ch.10-11)—— 呼應案例庫死亡 marker

**M&A**(Ch.10):Value created = PV(synergies) − premium(p.174)。交易類型成功率:
opportunistic(弱賣家→強買家)~90% 成功;operational 中上;transitional 風險較高;
**transformational(買家跳去唔同行業)「rarely succeed」**(p.183)—— 清晰印證咗
「併購 = 死亡訊號」嘅先驗判斷。融資方式係可讀訊號:現金支付 = 管理層對 synergy 有信心;
股票支付 = 管理層對 synergy 有疑慮**兼**相信自己股票已經被高估(p.184)。

**Buybacks**(Ch.11)黃金法則(p.194):「A company should repurchase its shares only when its
stock is trading below its expected value and no better investment opportunities are
available.」買股法方式分強弱訊號:公開市場購回最弱,Dutch auction/固定價格要約最強
(p.196-199)。

**Ch.12(p.215)**——書自己引述嘅獨立實證,同 `2026-07-09_magnifier_literature.md` §2 已收錄
嘅 Cooper-Gulen-Schill(2008)資產增長文獻家族屬於同一結論方向:

> "Issuing stock tends to be associated with poor subsequent total shareholder returns, and
> buying back stock leads to above-average returns... high asset growth rates are a strong
> predictor of future low abnormal returns and vice versa."

三個獨立角度(game theory sidebar §2.5、Paccar 實例 §2.4、呢條引用文獻)交叉印證同一個
結論,大大加強咗案例庫死亡 marker 嘅信心 —— 唔係單一數據集嘅巧合。

### 2.7 Chapter 12 完整 Sources-of-Opportunity 分類法 —— 對應 Q4

八個來源(p.207-220):①機率校準(避免用模糊詞語表達機率——受訪者對「real possibility」嘅
機率解讀由 25% 去到 85%,p.209)②宏觀衝擊(Tetlock:專家預測員幾乎唔跑贏亂猜,但仍過度自信,
p.210)③管理層變動(Thorndike《Outsiders》CEO 嘅共通點:資本配置紀律、獨立思考、低媒體
曝光,p.212)④拆股/派息/回購/發股(§2.6 已展開)⑤訴訟 ⑥監管/關稅衝擊(監管有時反而鞏固
在位者護城河,例:GDPR 對 Google,p.217)⑦分拆(平均創造價值,p.218-219)⑧極端股價變動
(base-rate 研究,25 年 5,400 個 -10% 十日跌幅同 6,800 個 +10% 升幅,按 momentum/valuation/
quality 分類:「buy signals were more common for stocks with poor momentum but attractive
valuations, and sell signals were more common for stocks that had positive momentum and a
valuation that reflected high expectations」,p.220)——呢個 momentum×valuation base-rate
sort 同 magnifier trough 買入時機(預期近期 momentum 差)嘅方向吻合,可以做一個現成、可量化
嘅輔助濾網。

**淨判斷**:全書冇搵到專門 analyst-dispersion/estimate-revision/herding 度量框架。書提供嘅
更嚴謹替代品全部係 **price-revealed**(唔係 survey-based):①imputed real-options value
佔現價比重(§1.4)②market-implied forecast period 相對同業(§1.3)③explicit
probability-weighted expected value gap,consensus vs non-consensus 加權(§2.3)④
momentum×valuation base-rate sort(呢節)⑤管理層資本配置行為本身做「內部人信念」訊號
(現金併購/公開市場回購 = 唔覺得貴;股票支付併購/發股 = 覺得貴,§2.6)。

---

## 3. 同現有發現嘅對照

**冇搵到直接矛盾。** 三組值得注意嘅呼應/張力:

1. **強交叉印證案例庫死亡 marker #2**(週期頂前槓桿式擴產/併購):§2.5 嘅 game theory
   sidebar(p.73)、§2.4 嘅 Paccar 紀律反例(p.167)、§2.6 嘅資產增長引用(p.215)—— 三個
   獨立角度(理論推導、實例、書自己引嘅文獻)全部指向同一結論,同案例庫嘅歷史歸納(9 個
   週期一致)以及 `2026-07-09_magnifier_literature.md` §2 嘅 Cooper-Gulen-Schill/Titman-
   Wei-Xie 資產增長文獻家族一齊構成四重獨立印證。呢個係全次蒸餾入面信心最高嘅單一發現。

2. **解釋咗「護城河喺下行期消失」嘅結構性原因**(§2.5):Porter 五力入面「高固定成本 +
   高需求波動 → peak 過度投資 → trough 產能過剩 → rivalry 白熱化」呢條邏輯鏈,補上咗案例庫
   §3c 發現 #1(FSLR vs 太陽能同業)背後「點解」嘅一層 —— 並提供咗一個可操作測試(value
   pool spread 逐年運算),把質性發現轉做可量化運算。冇矛盾,係補強。

3. **Feature #1(operating leverage)嘅文獻定性一致**:`literature.md` §3 已經指出 Novy-Marx
   OL 溢價「真但細」(Sharpe 0.40-0.50,同 HML 相若),呢本書嘅 operating leverage 討論
   (§2.4)純粹機制性/質性,冇俾任何量化 bps/Sharpe 數字——呢個唔矛盾,反而一致:書本身冇
   宣稱 OL 係一個獨立可以直接買嘅 alpha 訊號,而係一個要同 sales growth trigger 交乘先有
   意義嘅**放大器**(§2.1-2.2 turbo trigger 邏輯),同 model plan 「10x = 營運槓桿 ×
   需求超級週期 × ...」嘅乘數設計完全吻合。

4. **一個方法論張力(唔係矛盾,係唔同哲學)**:書嘅 crowding 度量(§2.3、§2.7)本質上係
   **主觀**——分析員自己揀機率分布嚟做 expected value。相對之下,`literature.md` §6
   已收錄嘅 MAX effect(Bali-Cakici-Whitelaw)/idiosyncratic skewness(Boyer-Mitton-Vorkink)
   係**客觀、可回測、純價格歷史推導**嘅濾網。兩者唔衝突,但定位唔同:書嘅框架屬於基本面/
   判斷驅動嘅一層,學術文獻嘅濾網屬於機械式硬閘門。對 Karst scorecard 設計嘅啟示(留俾
   D/E 步驟,唔喺呢度落實):MAX/skewness 呢類客觀濾網應該做機械 gate,書嘅 expected-value
   框架應該做喺 gate 之上嘅人手判斷層(同 repo 現有嘅 NHITL 定位—— `karst-role-nhitl-
   decision-support` memory ——一致)。

**未解/風險**:第 4 主題(週期股估值倒轉)依然冇一條專門文獻或書本方法可以直接引用 —— 呢個
確認咗 `literature.md` 已標注嘅地基薄弱唔係搜索不足,而係真.缺口。§1.5 已經講明,呢啲槓桿
(threshold margin、market-implied forecast period、real options)套用去 magnifier trough
案例嗰陣,「揀邊年做基準」「點樣定義正常化 margin」呢啲判斷仍然要人手做,書冇提供自動化答案。

---

## 4. 附錄:章節 ↔ 抽取文字檔行號對照(供日後重讀)

| 章 | 標題 | 書內頁碼 | PDF 頁碼 | 文字檔行號(約) |
|---|---|---|---|---|
| 1 | The Case for Expectations Investing | p.1 | 19 | ~365 |
| 2 | How the Market Values Stocks | p.21 | 39 | 1093 |
| 3 | The Expectations Infrastructure | p.44 | 62 | 2026 |
| 4 | Analyzing Competitive Strategy | p.57 | 75 | 2549 |
| 5 | How to Estimate Price-Implied Expectations | p.87 | 105 | 3704 |
| 6 | Identifying Expectations Opportunities | p.97 | 115 | 4158 |
| 7 | Buy, Sell, or Hold? | p.118 | 136 | 5042 |
| 8 | Beyond Discounted Cash Flow | p.132 | 150 | 5610 |
| 9 | Across the Economic Landscape | p.152 | 170 | 6381 |
| 10 | Mergers and Acquisitions | p.171 | 189 | 7146 |
| 11 | Share Buybacks | p.190 | 208 | 8105 |
| 12 | Sources of Expectations Opportunities | p.207 | 225 | 8840 |
| — | Notes | p.221 | 239 | 9408 |

原始抽取檔:`C:\projects\Investment\Karst\thesis\.raw\expectations_investing_fulltext.txt`
(gitignored,可用 `backtest/experiments/_extract_expectations_investing.py` 對住原 PDF
重新產生)。
