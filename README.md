# Karst

> 經得起侵蝕的硬基岩。41,000+ 個 backtest 像水,把不 work 的策略沖掉;
> 留下來的硬核,就是這裡。

---

## 定位

Karst 是整套投資系統的 **執行 + 參數核(WHEN / HOW)**,以實證為唯一地基。

| 系統 | 角色 | 回答的問題 | 位置 |
|---|---|---|---|
| **Compass** | WHY | 質性大腦 + 紀律(該不該動、動哪個板塊) | `../Compass` |
| **Tree**(drawtree) | WHAT | 可證偽假設 + risk/reward(Bull/Base/Bear) | github.com/Draw-Tree/drawtree-protocol |
| **Karst** | WHEN / HOW | 釘死的參數 + timing + 系統性風控 | 本 repo |

**Karst 不負責找 edge**——那是 Compass + Tree 的事。Karst 是執行臂:拿一個
已通過驗證的標的,決定 **何時進出、用什麼結構表達、承擔多少風險**。

一個 commoditized 的策略(PMCC / CSP),只要 **只用在通過 Tree kill condition
的 thesis + Compass 判 Warm 的 sector + 對的 regime + 對的參數** 上,它就不再
commoditized。edge 是這個組合,不是任何單一零件。

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

## 結構

```
Karst/
├── README.md                    ← 本檔
├── params/
│   ├── layer1_options.md        ← 期權結構參數(PMCC / 方向性 LEAP / CSP / IC)
│   └── layer2_timing.md         ← 標的層 timing(4 訊號家族 + flow)
├── invariants/
│   └── systematic_rules.md      ← 系統性風控(Charter「堆 B」蒸餾,無人味)
├── lenses/                      ← 基本面/護城河鏡片(照 Mark Douglas pipeline 蒸餾)
│   └── README.md
└── reference/                   ← 只放指標,不複製內容
    └── README.md
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
