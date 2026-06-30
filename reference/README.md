# Reference — 只放指標,不複製內容

> Karst 不複製 distillation / 書 / Compass 的內容。這裡只記「東西在哪」。
> **2026-06-30 reorg:** Quant → 改名 `Reference`;書 → 移到 `ebooks`;
> `.agents` → 已移入 Karst。

---

## 外部系統(同層 `C:/projects/Investment/`)

| 系統 | 角色 | 位置 |
|---|---|---|
| Compass | WHY(質性 + 紀律 + regime + sector 溫度) | `../../Compass` |
| Tree(drawtree) | WHAT(可證偽假設 + risk/reward) | github.com/Draw-Tree/drawtree-protocol |
| **Reference**(原 Quant) | 實證原料倉 | `../../Reference` |
| **ebooks**(原 Investors) | 投資人書庫(蒸餾原料) | `../../ebooks` |
| Indicators | 指標數據 crawler(Python,待評估用途) | `../../Indicators` |

---

## 實證原料(在 Reference)

| 原料 | 位置 | 用途 |
|---|---|---|
| Backtest 蒸餾(55 影片)| `../../Reference/distillations/2026-06-24_backtest-everything-distillation.md` | Layer-1/2 參數來源 |
| 原始 transcripts | `../../Reference/raw_data/backtest_everything_transcripts/` | 參數複核(✅ verified 的依據)|
| Transcript 抓取 script | `../../Reference/scripts/fetch_transcripts.py`、`scrape_youtube_channel.py` | 持續更新 backtest everything 頻道 |
| ideas(設計筆記)| `../../Reference/ideas/` | 背景脈絡(注意 idea-07 已知錯誤)|

## 書庫(在 ebooks)

| 用途 | 位置 |
|---|---|
| 護城河 | `../../ebooks/Fundamental Value & Growth/Pat Dorsey/`、`Michael Porter/` |
| 成長動能 / RS / VCP | `../../ebooks/Discretionary Momentum/`(Minervini / O'Neil …)|
| 成長分類 | `../../ebooks/Fundamental Value & Growth/Peter Lynch/` |
| 蒸餾 pipeline 範本 | `../../ebooks/Behavioral & Existential Psychology/Mark Douglas/` |

---

## 複核狀態

| 項目 | 狀態 |
|---|---|
| transcript 01 `-aQCEO_MPU8`(QQQ LEAPS) | ✅ verified |
| 新影片 56/57 `AJ3hFgKUptE`/`FO2Yq7to0lc`(IV rank U-shape) | ✅ verified,已併入 layer1 §1 + INV-4b;distillation(僅 1–55)待補 |
| 新影片 58 `lgPf3-okyTY` | = dist §5.2 重傳(bear call theta wheel),無新資訊 |
| 其餘 transcripts | 📄 待複核(隨參數使用逐一回查)|
| distillation 853–1693 行 | ⏳ 未讀(建 Layer-2 完整版時讀)|
