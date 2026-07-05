# Karst

> 經得起侵蝕的硬基岩。41,000+ 個 backtest 像水,把不 work 的策略沖掉;
> 留下來的硬核,就是這裡。

---

## 定位

Karst 是一套**獨立、自足的全自動 agentic 投資決策系統**,以實證為唯一地基。
目標:依系統策略,全自動產出**最佳投資決策**(NHITL — 無人介入是達成手段,不是目的)。

Karst **自己找 edge、也自己跑決策管線**:由上而下的每日掃描(市場閘 → 板塊/RS →
個股 → 質性 thesis → 擇時 → sizing),**自建 Phase 3 質性層,edge 不外包**。系統回答:
**現在該不該有 exposure、多少信念、什麼結構、什麼時機、承擔多少風險。**

同層外部 repo(`../Compass`、drawtree、`../Reference`、`../ebooks`)**只是參考素材,
不是功能依賴**;Karst 不依賴它們運作。

一個 commoditized 的策略(CSP / covered call),只要**只用在通過可證偽 kill condition
的 thesis + 對的 sector + 對的 regime + 對的參數**上,它就不再 commoditized。
edge 是這個組合,不是任何單一零件。

---

## 鐵律:每個數字都要有出處

Karst 不信任二手蒸餾。每一條參數都帶 tag:

| Tag | 意義 |
|---|---|
| ✅ **verified** | 已對原始 transcript 逐字確認 |
| 📄 **distilled** | 來自 distillation,尚未回 transcript 複核 |
| ⚠️ **open** | 來源間有衝突 / 待回測解決 |

> **由來:** idea-07 曾把 standalone LEAP 的「0.30 delta」誤植進 PMCC long leg
> ——那會在「價格漲到 short strike 之上、long strike 之下」的區間造成無上限虧損。
> 教訓:distillation 會出錯,參數必須能溯源到 transcript。

---

## 結構(2026-07-03 更新;**新 session 從 `STATUS.md` 開始**)

```
Karst/
├── STATUS.md                    ← 單一入口:現在在哪/下一步/東西在哪
├── ARCHITECTURE.md              ← 跨 Phase 系統地圖(single source of truth)
├── AGENTS.md / HANDOFF.md       ← agent 入口 / 最近 session 詳細交接
├── docs/                        ← 審查文件 + ROADMAP_AGENTIC.md(已核准實施計畫)
├── backtest/
│   ├── (核心庫: data/engine/metrics/signals/regime/scorecard/options_engine/bsm)
│   ├── scan.py                  ← 每日掃描前門
│   ├── spine/                   ← Phase 0/1/4 掃描引擎
│   ├── experiments/             ← 37 個回測實驗(見其 README.md 索引)
│   └── results/                 ← 回測結論(dated .md)
├── thesis/                      ← Phase 3 質性層(9 主題 + forward-IC)
├── web/                         ← 唯讀 dashboard(compute/serve 分離)
├── params/                      ← 期權/timing 參數(帶 tag;PMCC 已於 v3.1 移除)
├── invariants/ lenses/ reference/  ← 風控鐵律 / 鏡片 / 外部原料指標
└── .agents/                     ← KARS_MEMORY(長期記憶)+ USER
```

---

## 兩條關注點分離(設計原則)

1. **標的評估 ≠ 期權結構。** 主引擎(`layer2_timing`)只回答「現在該不該對這個
   標的有 exposure」,用 MA + 4 家族,對所有標的通用。期權怎麼表達(IV rank /
   skew / VIX gate)是 `layer1_options` 的執行閘,只在進出場當下啟動。

2. **系統性風險 ≠ 人類心理。** Karst 是 no-human-in-the-loop 的執行層。Charter 裡
   「因為悶 / FOMO / 報復」那類 operator 心理教訓 **不寫進系統**(系統不會悶);
   只保留可機器檢查的系統性 invariant。詳見 `invariants/`。

---

## 不放什麼

- ❌ 不複製 distillation / 書 / Compass 的內容 → `reference/` 只放指標
- ❌ 不寫進人類心理教訓 → 只留系統性 invariant
- ❌ 不在沒有出處的情況下釘死任何數字
