# 估值模組 Spec:Expectations-Gap(可實施版)【Fable 5,2026-07-12】

> **回應用戶指令**:「俾建議 + 可實施方案 on 估值」。本檔 = 設計 spec + 今日已實跑嘅 v0 證據。
> **v0 已落地**:`backtest/experiments/exp_expectations_gap_v0.py`(28/28 隻計齊,defeatbeta-first,
> 非 USD 報表自動 FX)→ `backtest/results/2026-07-12_expectations_gap_v0.md`(全表+主題 rollup
> +五專評+9 caveat)。呢個唔係紙上談兵,今日已經有第一張真數表。
> **哲學定位**:唔係 Graham 深值(同 KARS_MEMORY「school mismatch」決策一致)——係 Mauboussin
> expectations investing 翻譯成 supercycle 語言:**唔問「平唔平」,問「現價 embed 咗幾多預期;
> 如果超級週期永遠唔嚟,mid-cycle 正常盈利力值返幾多」**。

---

## 1. 三個核心讀數(v0 已實作)

| 讀數 | 公式 | 答乜嘢問題 |
|---|---|---|
| **E_norm 正常化盈利力** | median(EBIT margin,全部可用季)× TTM revenue;NOPAT = ×(1−21%) | 呢盤生意「唔發夢」嘅正常賺錢能力 |
| **P_base(supercycle-free coverage)** | NOPAT_norm × 14 ÷ EV(10×/18× 敏感度並列) | 現價有幾多成係「無聊正常生意」冚得住?≥0.8「supercycle 白送」/ 0.4-0.8「買緊部分希望」/ <0.4「大部分係希望」/ E_norm≤0「N/A-binary(option framing 硬性)」 |
| **g_implied(市場隱含增長)** | 解 EV = NOPAT_norm×(1+g)⁵×14÷1.10⁵ | 現價要求公司做到幾勁?一個「45%/年×5年」嘅數,比「PE 98th percentile」直觀一百倍 |

## 2. v0 實跑結果(2026-07-12,證明呢把尺同 PE 分位唔係同一把)

**15 個 theme 分類**:8 個「大部分係希望」/ 3 個「買緊部分希望」/ 3 個 N/A-binary
(space / rare-earth / semicap——成個主題冇正常化盈利可錨,option framing 係唯一誠實表達)
/ **1 個「supercycle 白送」:FSLR 0.83x,g_implied 僅 14.1%**。

**呢把尺捉到 PE 分位捉唔到嘅嘢(四個實例)**:
1. **USAC「最平」要打折**——P_base 0.53x,唔係全場最高(AVT 0.89 / FSLR 0.83 / LPX 0.75 都
   高過佢);而且 net debt $2.98B vs 市值 $3.84B,**佢個「平」一大半係槓桿股權切片嘅假象**。
   PE 2nd percentile 睇唔到資本結構;P_base 用 EV 睇到。→ USAC 嘅 solvency gate 檢查升級為必做。
2. **GEV 0.01x**——正盈利名入面最誇張:現價要求 **155.8%/年 × 5 年**。ai-power-grid theme
   note 講「priced ahead of ramp」,而家有咗個實數講到底 priced 到幾盡。
3. **ASML 0.20x(g_implied 51.2%/年)、ATI 0.25x(45.3%/年)**——「真.壟斷但 fully priced」
   由形容詞變成數字;呢兩個 theme 嘅注碼紀律(watch 級)而家有量化根據。
4. **MU 0.21x 係上限讀數**——TTM revenue $90B 喺週期頂,E_norm 未平滑 revenue 項,真 P_base
   更低。**教訓:週期頂嘅 E_norm 會俾 TTM revenue 抬高,呢個 bias 要每次明寫**(v0 有 worked
   example)。

## 3. 接線規格(production 化三步,全部細工作量)

### 3a. `thesis/valuation.py`(由 exp 版升格,~半日)
- 輸入:themes.yaml active themes 嘅 top 1-3 表達 ticker;輸出:`thesis/valuation_report.json`
  (每 ticker:P_base@10/14/18×、g_implied、分類、數據季數、bias flag)。
- **週期位置修正(v1 加,v0 冇)**:E_norm 嘅 revenue 項由 TTM 改做「TTM 同 3 年平均取中位」
  ——減週期頂抬高 bias(MU 案例);v0→v1 嘅唯一公式改動。
- 排程:**季度**(財報季後跑一次);唔使日更(估值唔係日內訊號)。

### 3b. Admission / sizing 接口(規則,唔係 code)
- Admission checklist 加一行:「expectations-gap:P_base + g_implied vs thesis 聲稱路徑,
  結論 正/中/負 + citation」。
- **Sizing 閘(% NAV 制)**:分類「大部分係希望」(P_base<0.4)且 g_implied > thesis 自己
  聲稱嘅增長 → 該 theme 注碼上限鎖 watch 級(0.5% NAV),**無論 confidence 幾高**;
  N/A-binary → 只准 option-framing 微注(≤0.5% NAV)。呢個就係「安全邊際」喺呢個系統嘅
  正確形態:唔係唔准買貴嘢,係唔准喺冇預期落差嘅地方擺大注。
- Dashboard ROW 2 加 exp-gap 欄(dashboard 設計書已預留)。

### 3c. 驗證(BT-5,先於 sizing 閘生效)
用 magnifier 案例庫做 ex-ante 判別力測試:MU 2016 / MU 2023 / FSLR IPO / STP IPO /
WOLF / SMCI,各用**當時可得數據**計 P_base + g_implied——問:呢把尺喺贏家入場點係咪
顯示「白送/部分希望」、喺輸家/爆煲名係咪顯示「大部分係希望」?六個案例全中先接 sizing 閘;
中一半 = 只做 dashboard 顯示,唔接注碼。**判官預先寫死,唔准事後搬龍門。**

## 4. 誠實邊界(v0 報告 9 條 caveat 嘅撮要)
- 14× baseline 係假設非真理(10×/18× range 讀);margin 非平穩;defeatbeta 深度僅 13-16 可用季
  (遠短於理想 28+,SNDK/ASTS/USAR 不足 12 季);TWD/EUR 報表用 spot FX 轉換係近似。
- **呢把尺唔係擇時工具**——佢答「而家個價 embed 咗乜」,唔答「幾時 re-rate」。擇時繼續由
  cycle_stage + constraint-language + 擁擠讀數負責。三樣嘢夾埋先係完整入場紀律:
  **結構真(4-KPI/rubric)× 預期未 price(本模組)× 週期位置啱(cycle_stage)**。
