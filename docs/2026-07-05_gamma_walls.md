# Gamma Walls(逐 strike GEX)— 工具 + 理論 reference

> **Live 決策工具**(`backtest/experiments/exp_gamma_walls.py`):SPY/QQQ/板塊/Mag7 嘅支持/阻力「區」+
> **強度** + 企穩線(gamma flip)。**同 aggregate GEX(`results/2026-07-05_gex_test.md`,對 VIX 無增量,
> 唔建做脆弱閘)係兩回事** —— 呢個係 strike-level 嘅 level/zone 用途。**LIVE 快照,無歷史 → 自己回測唔到;
> 理論 + 研究撐 + 直接用**(有 forward-log 驗證路,見 §5)。用戶要求嘅工具。

## 1. 概念(街坊版)
- **支持區 = put wall**(下方 put gamma 最大 strike):買盤對沖較密、跌到易頂住。
- **阻力區 = call wall**(上方 call gamma 最大 strike):升到易頂住。
- **磁鐵 = 最大總 gamma strike**:價易被吸過去(月度到期日尤甚)。
- **企穩線 = gamma flip(零 gamma)**:🟢 現價之上 = 釘住區(正 gamma,牆較實、區間上落);
  🔴 現價之下 = 脆弱區(負 gamma,**跌穿支持會急跌加速,唔係反彈;升返上企穩線先轉穩**)。
- **強度 [████ 21% 強]** = 該 strike 佔嗰邊 gamma %。**強 ≥15% = 硬牆、8-15% 中、<8% 弱 = 紙牆易穿**。
  (用戶要求:唔係所有牆一樣強,睇「牆有幾高」。)

## 2. 計法(可 code,已實作)
per-1% dealer GEX per strike(SpotGamma/Perfiliev 慣例;莊家 long call / short put):
```
GEX_strike = sign · Γ_BS · OI · 100 · S² · 0.01      (sign: +call, −put)
Γ_BS = φ(d1)/(S·σ·√T),  d1=(ln(S/K)+(r+σ²/2)T)/(σ√T)
```
- **call wall** = 上方最大 call-side gamma strike;**put wall** = 下方最大 put-side;**磁鐵** = 最大總 gamma。
- **強度** = 該 strike gamma ÷ 嗰邊總 gamma。
- **企穩線** = 喺 spot grid(±15%,61 點)逐點**重算**每個期權 gamma 再加總,搵零交叉(gamma 跟 spot 變,
  唔可以喺靜態鏈直接讀)。
- **DTE 分開計**(gamma∝1/√T,近端 dominate):SPY/QQQ 出 **0DTE / 1週 / 1月** 三個 profile。

## 3. 證據分層(咩真、咩 folklore)
| | 證據 | 級別 |
|---|---|---|
| **Pin(磁鐵)** | Ni-Pearson-Poteshman 2005 JFE:OPEX 黐 strike,~16.5bps | ✅ 真但細,月度 OPEX 為主 |
| **企穩線上/下(波動 regime)** | Barbon-Buraschi「Gamma Fragility」2021;Baltussen 2021 JFE(負γ→放大/趨勢,正γ→回歸) | ✅ **最實**(regime 條件,唔係 drift) |
| **支持/阻力牆命中** | Vendor(非同儕):正γ 時 ~70-78% 留 range;跌穿 flip 2-4× 波動 | 🟡 vendor 數,order-of-magnitude |
| **「flip 上=睇好」站立方向 alpha** | raw GEX 控 VIX 後消失;只 ΔGEX 微弱(Jonsson-Nyberg 2025) | ❌ folklore |

## 4. 兩個用途(證據對齊)
1. **方向 = regime 讀數,唔係買賣訊號**:正γ=釘/回歸、負γ=放大/趨勢延續(真);「flip 上就買」係 folklore。
2. **支持/阻力 range by DTE(主用途)**:[put wall, call wall] = 預期區間,當「區」(±$2-5)唔係線;
   **只喺企穩線之上(正γ)先成立**;跌穿牆會**反轉成加速器**(升穿 call wall→squeeze、跌穿 put wall→插)。
   **睇強度**分硬牆/紙牆。

## 5. 可信度分層 + Caveats
| 類 | sign 假設 | 可信度 | 註 |
|---|---|---|---|
| **指數 ETF(SPY/QQQ)** | 最乾淨 | **最高(結構)** | 但 **0DTE ≈ 48% 成交,EOD-OI 捉唔到 → 週線係開市/多日結構圖,唔係日內** |
| **板塊 ETF** | 合理 | 中 | 當粗略 zone;薄嘅噪 |
| **個股(Mag7)** | **易反轉**(散戶買call/covered-call ETF/財報) | **最低** | **財報避**;當參考 |
- **無歷史 → 自己回測唔到**。**唯一驗證路 = forward-log**:每日記低 wall/flip/pin/強度,之後 score 未來
  1-5 日有冇 respect（合 forward-IC 紀律 [[validation-mirror-and-increment]])。**未有 log 前,一律當 context/zone,唔當訊號。**
- 牆唔 hold 嘅時候:企穩線之下、宏觀催化(FOMC/CPI/財報)、薄流動性、實現波動 > 引伸。

## 6. 對 Karst 用途
- **tier-1(SPY/QQQ)期權側嘅 level/zone + regime context**(Phase 0 附近)——揀 CSP/short-call strike、
  睇「而家係釘住定脆弱」。**當 zone/regime 讀數,唔當 alpha。**
- **板塊/Mag7** 參考,個股財報避。
- **下一步(可選)**:開 **forward-log**(每日跑工具存 snapshot)累積自己 hit-rate,先驗證再加重。
- 同大局一致:呢個係**風控/context 工具**,唔係 alpha;真 alpha 靠 Phase 3。

## 來源
Ni-Pearson-Poteshman 2005 JFE · Barbon-Buraschi 2021(SSRN 3725454)· Baltussen-Da-Lammers-Martens 2021 JFE ·
Garleanu-Pedersen-Poteshman 2009 RFS · Jonsson-Nyberg 2025 · SqueezeMetrics/Perfiliev(公式)·
SpotGamma docs · FlashAlpha(walls/0DTE)。
