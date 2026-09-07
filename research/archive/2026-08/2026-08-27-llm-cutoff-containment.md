# LLM 訓練截止日與前視偏差圍堵：事實調研報告

- **查證日期**：2026-08-27（全份報告所有事實一律以此日為準）
- **性質**：純事實調研。本報告只陳述查得的事實與出處，不作決策、不作建議。
- **來源紀律**：每項事實均附來源 URL。查不到明確官方來源的，一律在文中標明「查無可靠來源」，不作推測填補。

---

## 一、可用模型截止日對照表

### 名詞說明

Anthropic 官方文件把截止日分成兩個數：

- **可靠知識截止（reliable knowledge cutoff）**：模型知識最完整、最可靠的日期。
- **訓練資料截止（training data cutoff）**：所用訓練資料的較闊範圍，通常比前者遲數個月。

出處：<https://platform.claude.com/docs/en/docs/about-claude/models/overview>（查證日 2026-08-27，原文：「Reliable knowledge cutoff: The date through which the model's knowledge is most extensive and reliable. Training data cutoff (under Show all details) is the broader range of data used.」）

就前視偏差而言，**保守應取訓練資料截止日**，因為那是資料實際觸及的最遲日期。OpenAI 與 Google 官方文件只公布單一個「knowledge cutoff」，沒有作此區分。

### 1.1 Anthropic（Claude）

| 廠商 | 模型 | 可靠知識截止 | 訓練資料截止 | API 現時是否可用 | 出處 |
|---|---|---|---|---|---|
| Anthropic | Claude Opus 5（`claude-opus-5`） | 2026-05 | 2026-05 | 可用（Active，退役不早於 2027-07-24） | [models/overview](https://platform.claude.com/docs/en/docs/about-claude/models/overview)、[model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) |
| Anthropic | Claude Fable 5（`claude-fable-5`） | 2026-01 | 2026-01 | 可用（Active，退役不早於 2027-06-09） | 同上 |
| Anthropic | Claude Sonnet 5（`claude-sonnet-5`） | 2026-01 | 2026-01 | 可用（Active，退役不早於 2027-06-30） | 同上 |
| Anthropic | Claude Opus 4.8（`claude-opus-4-8`） | 2026-01（支援頁措辭「trained on data up until January 2026」） | 未在本次查證的官方頁單獨列出 | 可用（Active，退役不早於 2027-05-28） | [support 8114494](https://support.claude.com/en/articles/8114494-how-up-to-date-is-claude-s-training-data)、[model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) |
| Anthropic | Claude Opus 4.7（`claude-opus-4-7`） | 2026-01（同上措辭） | 未單獨列出 | 可用（Active，退役不早於 2027-04-16） | 同上 |
| Anthropic | Claude Opus 4.6（`claude-opus-4-6`） | 2025-08（同上措辭） | 未單獨列出 | 可用（Active，退役不早於 2027-02-05） | 同上 |
| Anthropic | Claude Sonnet 4.6（`claude-sonnet-4-6`） | 2025-08（同上措辭） | 未單獨列出 | 可用（Active，退役不早於 2027-02-17） | 同上 |
| Anthropic | Claude Opus 4.5（`claude-opus-4-5-20251101`） | **2025-05** | **2025-08** | 可用（Active / legacy，退役不早於 2026-11-24） | [models/opus-4-5/overview](https://platform.claude.com/docs/en/models/opus-4-5/overview) |
| Anthropic | Claude Sonnet 4.5（`claude-sonnet-4-5-20250929`） | **2025-01** | **2025-07** | 可用（Active / legacy，退役不早於 2026-09-29） | [models/sonnet-4-5/overview](https://platform.claude.com/docs/en/models/sonnet-4-5/overview) |
| Anthropic | Claude Haiku 4.5（`claude-haiku-4-5-20251001`） | **2025-02** | **2025-07** | 可用（Active，退役不早於 2026-10-15） | [models/overview](https://platform.claude.com/docs/en/docs/about-claude/models/overview) |
| Anthropic | Claude Opus 3（`claude-3-opus-20240229`） | 2023-08（支援頁措辭「trained on data up until August 2023」） | 未列出 | **已退役 2026-01-05** | [support 8114494](https://support.claude.com/en/articles/8114494-how-up-to-date-is-claude-s-training-data)、[model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) |
| Anthropic | Claude Opus 4.1、Claude Opus 4、Claude Sonnet 4、Claude Sonnet 3.7、Claude Haiku 3.5、Claude Haiku 3、Claude Sonnet 3.5、Claude 2 / 2.1 / 1.x | — | — | **全部已退役**（Opus 4.1 退役 2026-08-05；Opus 4 / Sonnet 4 退役 2026-06-15；Haiku 3 退役 2026-04-20；Sonnet 3.7、Haiku 3.5 退役 2026-02-19） | [model-deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) |

**Anthropic 線的關鍵事實**：現役 Claude 模型當中，**訓練資料截止日最早的是 Claude Sonnet 4.5 與 Claude Haiku 4.5，同為 2025-07**。截止日更早的 Claude 3 世代（Opus 3 為 2023-08）已全部退役，官方文件明言「Requests to retired models will fail」。

Anthropic 在同一頁列明退役政策的取捨：「Researchers lose access to models for ongoing and comparative studies」，並承諾長期保存模型權重，但沒有承諾重新開放（出處同上，查證日 2026-08-27）。

### 1.2 OpenAI

| 廠商 | 模型 | 知識截止日 | API 現時是否可用 | 出處 |
|---|---|---|---|---|
| OpenAI | GPT-5.6 Sol（`gpt-5.6-sol`，旗艦） | 2026-02-16 | 可用 | [models/gpt-5.6-sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) |
| OpenAI | GPT-5.6 Terra（`gpt-5.6-terra`） | 2026-02-16 | 可用 | [api/docs/models](https://developers.openai.com/api/docs/models) |
| OpenAI | GPT-5.6 Luna（`gpt-5.6-luna`，輕量） | 2026-02-16 | 可用 | 同上 |
| OpenAI | GPT-5（`gpt-5-2025-08-07`） | 2024-09-30 | 可用，但該快照列明 **2026-12-11 停用** | [models/gpt-5](https://developers.openai.com/api/docs/models/gpt-5)、[deprecations](https://developers.openai.com/api/docs/deprecations) |
| OpenAI | o3（`o3-2025-04-16`） | 2024-06-01 | 可用，但該快照列明 **2026-12-11 停用** | [models/o3](https://developers.openai.com/api/docs/models/o3)、[deprecations](https://developers.openai.com/api/docs/deprecations) |
| OpenAI | GPT-4.1（`gpt-4.1`） | 2024-06-01 | 可用（官方模型頁與停用頁均未列 API 停用日；2026-02-13 只在 ChatGPT 下架） | [models/gpt-4.1](https://developers.openai.com/api/docs/models/gpt-4.1)、[deprecations](https://developers.openai.com/api/docs/deprecations) |
| OpenAI | GPT-4o（`gpt-4o`） | **2023-10-01** | 可用（官方模型頁與停用頁均未列 API 停用日） | [models/gpt-4o](https://developers.openai.com/api/docs/models/gpt-4o) |
| OpenAI | GPT-4 Turbo（`gpt-4-turbo`） | 2023-12-01 | 可用，但列明 **2026-10-23 停用** | [models/gpt-4-turbo](https://developers.openai.com/api/docs/models/gpt-4-turbo)、[deprecations](https://developers.openai.com/api/docs/deprecations) |
| OpenAI | GPT-3.5 Turbo（`gpt-3.5-turbo`） | **2021-09-01** | 可用，但列明 **2026-10-23 停用** | [models/gpt-3.5-turbo](https://developers.openai.com/api/docs/models/gpt-3.5-turbo)、[deprecations](https://developers.openai.com/api/docs/deprecations) |
| OpenAI | `gpt-4`、`o1`、`o1-pro`、`o3-mini`、`o4-mini`（含微調版本） | 本次未在官方頁核到逐一截止日 | 列明 **2026-10-23 停用** | [deprecations](https://developers.openai.com/api/docs/deprecations) |

**GPT-5.1 / 5.2 / 5.4 / 5.5 的截止日**：官方牌價頁仍列出這幾個模型的價錢，但本次查證未在官方模型頁核到它們的知識截止日 —— **查無可靠來源**，不作推測。

### 1.3 Google（Gemini）

| 廠商 | 模型 | 知識截止日 | API 現時是否可用 | 出處 |
|---|---|---|---|---|
| Google | Gemini 3 系列（含 `gemini-3.1-pro-preview`、`gemini-3.1-flash-lite`、`gemini-3-flash-preview` 等） | 2025-01（官方 FAQ 原文：「Gemini 3 models have a knowledge cutoff of January 2025.」） | 可用 | [gemini-api/docs/gemini-3](https://ai.google.dev/gemini-api/docs/gemini-3) |
| Google | Gemini 3.7 Flash / 3.6 Flash / 3.5 Flash / 3.5 Flash-Lite | 個別模型頁未列截止日；官方 Gemini 3 開發者指南以「Gemini 3 models」統稱 2025-01 | 可用（Stable） | [gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)、[gemini-3 FAQ](https://ai.google.dev/gemini-api/docs/gemini-3) |
| Google | Gemini 2.5 Pro（`gemini-2.5-pro`） | 2025-01 | 可用（Stable） | [models/gemini-2.5-pro](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-pro) |
| Google | Gemini 2.5 Flash（`gemini-2.5-flash`） | 2025-01 | 可用（Stable） | [models/gemini-2.5-flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash) |
| Google | Gemini 2.0 Flash / 2.0 Flash-Lite | 未列 | **已下架（Shut down）** | [gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) |
| Google | Gemini 3 Pro Preview（`gemini-3-pro-preview`） | — | 已於 2026-03-09 轉去 `gemini-3.1-pro-preview` | [gemini-api/docs/changelog](https://ai.google.dev/gemini-api/docs/changelog) |

**Google 線的關鍵事實**：現時 Gemini API 上，由 2.5 世代到 3.x 世代，官方公布的知識截止日**一律是 2025-01**。沒有任何一個仍在線的 Gemini 模型截止日早於 2025-01。

### 1.4 開源／開放權重模型家族

| 廠商 | 模型 | 訓練資料截止日 | 現時是否可取得 | 出處 |
|---|---|---|---|---|
| Meta | Llama 2（7B / 13B / 70B，base） | **2022-09**（原文：「The pretraining data has a cutoff of September 2022, but some tuning data is more recent, up to July 2023.」） | 權重可下載自行部署 | [llama2 MODEL_CARD.md](https://github.com/meta-llama/llama-models/blob/main/models/llama2/MODEL_CARD.md) |
| Meta | Llama 2 Chat（微調版） | 微調資料最遲至 **2023-07**（同一句） | 權重可下載 | 同上 |
| Meta | Llama 3.1（8B / 70B / 405B） | **2023-12**（原文：「The pretraining data has a cutoff of December 2023.」） | 權重可下載 | [llama3_1 MODEL_CARD.md](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md) |
| Meta | Llama 3.3（70B Instruct，2024-12-06 發布） | **2023-12**（同一句） | 權重可下載 | [llama3_3 MODEL_CARD.md](https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md) |
| Meta | Llama 4 Scout / Maverick | **2024-08**（原文：「The pretraining data has a cutoff of August 2024.」） | 權重可下載 | [llama4 MODEL_CARD.md](https://github.com/meta-llama/llama-models/blob/main/models/llama4/MODEL_CARD.md) |
| Mistral | Mistral Large 3（`mistral-large-2512`，2025-12-02 發布） | **查無可靠來源** —— 官方模型文件頁未列訓練／知識截止日 | API 可用；開放權重 | [docs.mistral.ai/models/mistral-large-3-25-12](https://docs.mistral.ai/models/mistral-large-3-25-12) |
| Alibaba | Qwen3 系列 | **查無可靠來源** —— 官方 GitHub 討論串中，社群向維護者查詢截止日，維護者轉問內部後至今無官方答覆 | 權重可下載 | [QwenLM/Qwen3 discussion #1093](https://github.com/QwenLM/Qwen3/discussions/1093) |

---

## 二、各段回測期的覆蓋能力

### 判斷準則

要對時點 T 出判斷而不「已知結局」，所用模型的**訓練資料截止日必須早於 T**。以下按此準則排列。

### 2.1 2023 年（2023-01 至 2023-12）

| 途徑 | 覆蓋範圍 | 事實狀況 |
|---|---|---|
| OpenAI `gpt-3.5-turbo`（截止 2021-09） | **2023 全年覆蓋** | 官方文件列明 **2026-10-23 停用**，距查證日不足兩個月 |
| OpenAI `gpt-4o`（截止 2023-10） | 只覆蓋 2023-11 起 | 覆蓋不到 2023 年 1 月至 10 月 |
| OpenAI `gpt-4-turbo`（截止 2023-12） | 完全覆蓋不到 2023 年 | 且 2026-10-23 停用 |
| Anthropic 全線現役模型（最早截止 2025-07） | **完全覆蓋不到** | 截止日早於 2023 的 Claude 模型（Opus 3，2023-08）已於 2026-01-05 退役 |
| Google 全線現役模型（最早截止 2025-01） | **完全覆蓋不到** | — |
| Meta Llama 2 base（截止 2022-09） | 2023 全年覆蓋 | 需自行部署；官方權重仍可下載 |
| Meta Llama 2 Chat（微調至 2023-07） | 只安全覆蓋 2023-08 起 | 微調資料本身已觸及 2023 上半年 |

**結論（2023 段）**：截至 2026-08-27，官方 API 上能覆蓋 2023 年全年的模型只有 `gpt-3.5-turbo` 一個，而它 2026-10-23 停用。**該日之後，四家主要廠商的官方 API 將再無任何模型能覆蓋 2023 年 1 月至 10 月**；屆時只剩自行部署開放權重（Llama 2 base）一條路。

### 2.2 2024 年（2024-01 至 2024-12）

| 途徑 | 覆蓋範圍 |
|---|---|
| OpenAI `gpt-3.5-turbo`（2021-09） | 全年覆蓋（2026-10-23 停用） |
| OpenAI `gpt-4o`（2023-10） | **全年覆蓋**，官方未列停用日 |
| OpenAI `gpt-4-turbo`（2023-12） | 全年覆蓋（2026-10-23 停用） |
| OpenAI `gpt-4.1`、`o3`（2024-06） | 只覆蓋 2024-07 起 |
| OpenAI `gpt-5`（2024-09-30） | 只覆蓋 2024-10 起（快照 2026-12-11 停用） |
| Meta Llama 3.1 / 3.3（2023-12） | 全年覆蓋，自行部署 |
| Anthropic、Google 全線 | **完全覆蓋不到** |

**結論（2024 段）**：`gpt-4o` 是目前官方 API 上唯一既能全年覆蓋 2024、又未列停用日的選項。開源方面 Llama 3.1 / 3.3 同樣全年覆蓋。Anthropic 與 Google 完全無法覆蓋 2024 年任何一個時點。

### 2.3 2025 年（2025-01 至 2025-12）

| 途徑 | 覆蓋範圍 |
|---|---|
| OpenAI `gpt-4o`（2023-10）、`gpt-4.1` / `o3`（2024-06）、`gpt-5`（2024-09） | **全年覆蓋** |
| Meta Llama 4（2024-08） | 全年覆蓋，自行部署 |
| Google Gemini 2.5 / 3.x（2025-01） | 只覆蓋 2025-02 起 |
| Anthropic Sonnet 4.5 / Haiku 4.5（訓練截止 2025-07） | 只覆蓋 2025-08 起 |
| Anthropic Opus 4.5（訓練截止 2025-08） | 只覆蓋 2025-09 起 |

**結論（2025 段）**：多個仍在線的模型可全年覆蓋 2025。但**若限定用 Anthropic，覆蓋不到 2025 年 1 月至 7 月**（按訓練資料截止日計）。若改用 Anthropic 的「可靠知識截止」（Sonnet 4.5 為 2025-01、Haiku 4.5 為 2025-02）則看似覆蓋更闊，但官方明言訓練資料範圍更闊，取可靠知識截止日等於承受一段已知有資料觸及的灰色地帶。

### 2.4 覆蓋不到的部分（明確列出）

1. **2023 年 1 月至 10 月**：2026-10-23 之後，官方 API 全無可用模型。
2. **2023 至 2024 全期**：Anthropic 與 Google 的官方 API 完全無法覆蓋，一個模型都沒有。
3. **2025 年 1 月至 7 月**：Anthropic 官方 API 完全無法覆蓋。
4. **單一模型跑通 2023–2025 三段**：現時只有 `gpt-3.5-turbo` 一個做得到，而它 2026-10-23 停用。其後若要三段用同一個模型，只剩自行部署 Llama 2 base（截止 2022-09）。
5. **舊模型持續可用性本身沒有保證**：Anthropic 在停用頁明言會為新模型騰出容量而退役舊模型；OpenAI 停用頁列出 2026-09 至 2026-12 之間多批模型停用。任何以「現時可用」為前提的安排，都受制於廠商日後的退役排程。

---

## 三、四種圍堵做法：效果與局限

### （a）遮蔽／替換實體名稱（匿名化）

**效果**

Glasserman 與 Lin 的〈Assessing Look-Ahead Bias in Stock Return Predictions Generated By GPT Sentiment Analysis〉（arXiv:2309.17322，2023-09-29）把新聞標題中的公司識別資訊移除，再比較原文與匿名版驅動的多空策略。原文摘要指出，偏差有兩種形態：一是前視偏差（模型知道該篇新聞之後的股價走勢），二是「分心效應」（對該公司的一般知識干擾了對文本情緒的量度）。實測結果是：**在訓練窗內（in-sample），匿名化標題的表現反而更好**，說明分心效應的影響大於前視偏差；而且這個傾向在大市值公司（模型對其一般知識更多）身上特別強。作者因此認為匿名化程序「潛在地對樣本外實作、以及去偏回測，都有用」。
出處：<https://arxiv.org/abs/2309.17322>（查證日 2026-08-27）

**局限**

1. **資訊損失可能大過它防的偏差。** Wu、Yang、Ying、Zhou 的〈Anonymization and Information Loss〉（arXiv:2511.15364，2025-11-19）以財報電話會議逐字稿做測試，結論是匿名化雖然有效掩蓋公司身份，但**顯著削弱模型的文本理解力**，令模型抽取有意義經濟訊號的能力下降；當數字與物件實體被移除時退化最嚴重，在語言不確定性高、公司特定細節多的文本中更嚴重。該文明言：匿名化引致的資訊損失，「比前視偏差的影響更普遍、更嚴重」。
出處：<https://arxiv.org/abs/2511.15364>（查證日 2026-08-27）

2. **只處理輸入，處理不到模型參數內的記憶。** 匿名化改的是餵進去的文本；模型權重裡已經記住的歷史結局不受影響。這一層被 Li、Wang、Ma 命名為「參數層前視偏差（parametric look-ahead bias）」。
出處：<https://arxiv.org/abs/2605.24564>（查證日 2026-08-27）

3. **可被重新識別。** 有研究顯示 LLM agent 能透過上下文線索與公開證據交叉比對，把匿名化的檔案還原到具體對象，削弱了資料連結攻擊原本的實務門檻。相關文獻包括〈From Weak Cues to Real Identities: Evaluating Inference-Driven De-Anonymization in LLM Agents〉（arXiv:2603.18382）與〈Stronger Re-identification Attacks through Reasoning and Aggregation〉（arXiv:2510.09184）。需注意：這兩篇的場景是個人身份重新識別，**未有針對「上市公司在財經文本中被重新識別」做直接量測** —— 就股票這個具體場景的重新識別率，本次**查無直接可靠來源**。
出處：<https://arxiv.org/html/2603.18382v2>、<https://arxiv.org/pdf/2510.09184>（查證日 2026-08-27）

### （b）只餵時點之前發布的文本（嚴格按發布日期過濾語料）

**效果**

這是資料層面的標準做法。Zhang 與 Zhang 的〈A Review of Large Language Models for Stock Price Forecasting from a Hedge-Fund Perspective〉（2026-04-10，IEEE Conference on Artificial Intelligence 2026 接收）在資料洩漏一節明言：「Mitigating leakage requires careful, event-centric preprocessing and time-respecting evaluation protocols, such as constructing event-level features, assigning all posts from the same event to a single fold, and using forward-only (rolling/expanding) splits with strict timestamp cutoffs.」
出處：<https://arxiv.org/html/2605.05211v1>（查證日 2026-08-27）

Zhang、Li、Peng、Chen 的〈When Alpha Disappears: A One-Switch Benchmark for Decision-Time Leakage in Financial Backtests〉（arXiv:2605.23959，2026-05-12）量化了這一層的價值：他們在固定資料面板、walk-forward 切分、模型族、預測期、組合規則與成本假設的前提下，逐項切換一個評估慣例，量度該慣例造成的績效膨脹。跨兩個股票資料集、六個模型族、2016–2024 年的測試顯示，**膨脹是高度選擇性的**：同日開盤執行並使用開盤後的日內資訊、以及置中的時間特徵，造成「大而穩定」的預測與交易指標上升；而全域正規化、含未來資訊的圖結構、同日收市執行，在多數設定下洩漏效應薄弱。
出處：<https://arxiv.org/abs/2605.23959>（查證日 2026-08-27）

**局限**

1. **管不到參數層記憶。** 同（a）第 2 點：即使餵進去的每一個字都在時點之前發布，模型權重裡的記憶依然存在。

2. **用搜尋引擎日期過濾器執行，不可靠。** El Lahib 等人的〈Temporal Leakage in Search-Engine Date-Filtered Web Retrieval〉（arXiv:2602.00758，2026-01-31 提交，2026-04-20 修訂）稽核了 Google 與 DuckDuckGo 的日期過濾器：**Google 有 71% 的題目、DuckDuckGo 有 81% 的題目，至少有一頁檢索結果含重大截止日後洩漏；直接揭示答案的分別是 41% 與 55%**。四種重複出現的成因是：文章事後更新、相關內容模組、不可靠的中繼資料時戳、以及「某事不存在」本身構成的訊號。使用受污染文件令 Brier 分數由 0.24（乾淨文件）「改善」到 0.10 —— 即憑空多出來的準確度。
出處：<https://arxiv.org/abs/2602.00758>（查證日 2026-08-27）

3. **用 prompt 叫模型「不要用截止日之後的知識」無效。** Liu 等人的〈ExAnte: A Benchmark for Ex-Ante Inference in Large Language Models〉（arXiv:2505.19533，2025-05-26）以股票預測、維基事件預測、科學出版預測與問答四類任務量度「洩漏率」，結論是「LLMs struggle to consistently adhere to temporal cutoffs across common prompting strategies and tasks」——**明確下達時間界限的 prompt 並不足夠**，模型仍常輸出受截止日後事件影響的內容。
出處：<https://arxiv.org/abs/2505.19533>（查證日 2026-08-27）

4. **語料完全 point-in-time 化，工程成本高。** Kelly、Malamud、Schwab、Xu 的做法（見（c））顯示，要把預訓練語料徹底按日期切乾淨，需要有出版時戳索引的語料庫（他們用 FineWeb），而其餘微調資料集仍要另行整理。
出處：<https://arxiv.org/abs/2607.11889>（查證日 2026-08-27）

### （c）刻意用訓練截止日更早的舊模型

**效果**

這是唯一直接消除參數層前視偏差的做法。Gao、Jiang、Yan 的〈Detecting Lookahead Bias in LLM Forecasts〉（arXiv:2512.23847，2025-12-29 提交，2026-06-12 修訂）提供了它為何有效的直接證據：他們用「只給日期的回憶查詢」估算模型已內化該公司該日期實際結果的機率，稱為 Lookahead Propensity（LAP）。實測顯示 **LAP 在訓練期內維持高位，過了訓練截止日後跌至接近零**；而 LLM 預測的準確度優勢，在高 LAP 的公司—日期組合上被放大，過了截止日後則失去顯著性。
出處：<https://arxiv.org/abs/2512.23847>（查證日 2026-08-27）

這條路的極致版是 Kelly、Malamud、Schwab、Xu 的〈Scaling Point-in-Time Language Models〉（arXiv:2607.11889，2026-04-24 提交，2026-07-17 修訂）：訓練「只用該日曆日期之前已存在的文本」的模型，以最多 40 億參數的 decoder-only transformer、1 萬億個按時序過濾的 token，建出 2013–2024 年**逐月的 checkpoint**。原文開篇即指：「Large language models trained on unrestricted internet corpora inevitably embed information from the future, introducing lookahead bias that compromises the validity of backtests and causal inference in finance and the social sciences.」
出處：<https://arxiv.org/abs/2607.11889>（查證日 2026-08-27）

**局限**

1. **名義截止日不等於實際截止日。** Cheng、Marone、Weller、Lawrie、Khashabi、Van Durme 的〈Dated Data: Tracing Knowledge Cutoffs in Large Language Models〉（arXiv:2403.12958，2024-03-19）提出「有效截止日（effective cutoff）」概念，並發現**有效截止日經常與廠商公布的截止日大幅偏離**，而且按子資源與主題各有不同。兩個成因：一是 CommonCrawl 的時間偏差（新 dump 內含大量舊資料），二是去重機制處理語意重複與詞面近重複時的不完整。
出處：<https://arxiv.org/abs/2403.12958>（查證日 2026-08-27）

2. **舊模型能力較弱。** Kelly 等人報告其 point-in-time 模型「approach the performance of leading open-weight models of comparable size (e.g., Gemma-3-4B and LLaMA-7B) trained on temporally unrestricted data, although a performance gap remains on several tasks」—— 即使靠擴大規模收窄，差距依然存在。
出處：<https://arxiv.org/abs/2607.11889>（查證日 2026-08-27）

3. **商業 API 會下架舊模型。** 見本報告第一、二節：Anthropic 已退役 Claude Opus 3 等全部 Claude 3 世代；OpenAI 官方停用頁列明 `gpt-3.5-turbo`、`gpt-4`、`gpt-4-turbo`、`o1`、`o3-mini`、`o4-mini` 於 2026-10-23 停用，`gpt-5-2025-08-07`、`o3-2025-04-16` 於 2026-12-11 停用。**一個以「用舊模型」為基礎的長期安排，最終只能靠自行部署開放權重維持**。
出處：<https://platform.claude.com/docs/en/about-claude/model-deprecations>、<https://developers.openai.com/api/docs/deprecations>（查證日 2026-08-27）

4. **靠近截止日的一段仍然不乾淨。** Zhang 與 Stadie 的〈Temporal Leakage in LLM Backtesting: Measurement, Validation, and Adjusted Scores〉（arXiv:2608.02985，2026-08-04）指出問題是結構性的：模型對接近其訓練截止日的期間本來就知道得更多，因此**被動回測無法區分「近期效應」、「真正的資料洩漏」與「真本事」**。他們並發現標準污染檢查失效：「Four flagship models fail it on questions they cannot have memorized: every scored question resolved after their cutoffs.」（四個旗艦模型在它們不可能記得的題目上都「不合格」——每一條計分題都在其截止日之後才有結果。）他們提出的解法是引入回測以外的資訊：以已知截止日作時間邊界、加上配對的乾淨對照，計算「洩漏調整分數」。
出處：<https://arxiv.org/abs/2608.02985>（查證日 2026-08-27）

5. **舊模型也可能不是同一個「人」。** 若「人物判官」的判斷風格依賴於較新模型的推理能力或指令跟隨能力，換用舊模型等於同時改變了被測對象。本次查證未找到直接量度「同一 persona prompt 在不同世代模型上判斷風格漂移」的文獻 —— **查無可靠來源**。

### （d）只做前向驗證，不做歷史回測

**效果**

結構上完全繞開參數層污染，是文獻中最乾淨的做法。Lopez-Lira 與 Tang 的〈Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models〉（arXiv:2304.07619，2023-04-15 提交，2025-10-28 最新修訂；SSRN 4412788）核心結果正是用**截止日之後的新聞標題**做的：「Using post-knowledge-cutoff headlines, GPT-4 captures initial market responses, achieving approximately 90% portfolio-day hit rates for the non-tradable initial reaction.」
出處：<https://arxiv.org/abs/2304.07619>、<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4412788>（查證日 2026-08-27）

Gao 等人的 LAP 研究提供了它為何乾淨的量化理由：LAP 過了截止日跌至近零，同時 LLM 預測在高 LAP 樣本上的準確度優勢亦消失（見（c））。

**局限**

1. **樣本期短、統計檢定力低。** Zhang 與 Zhang 的 hedge-fund 視角綜述批評：依賴自建資料集的研究「有時只以數週至數月的資料報告結果，會降低統計檢定力、加劇樣本期與市況依賴偏差，並削弱所報績效對真實部署的可信度」，並主張評估應覆蓋**至少一個完整的牛熊市況週期**，而非短而順境的窗口。
出處：<https://arxiv.org/html/2605.05211v1>（查證日 2026-08-27）

2. **要等時間，而且時鐘會被重設。** 前向樣本由模型截止日起算。以本報告第一節的事實計：`gpt-5.6-sol` 截止日 2026-02-16，至查證日 2026-08-27 只有約 6 個月的乾淨前向樣本。每次換用更新的模型，前向樣本就要由該模型的截止日重新起算。

3. **不能免除管線層面的洩漏。** 〈When Alpha Disappears〉所量度的「決策時點洩漏」（同日開盤執行並用開盤後資訊、置中的時間特徵等）是回測協定本身的問題，前向驗證同樣會犯，只是換了個名稱叫「實盤執行假設不成立」。
出處：<https://arxiv.org/abs/2605.23959>（查證日 2026-08-27）

4. **無法回答「這個判官在 2008 或 2020 會怎樣做」這一類問題。** 前向驗證按定義不覆蓋歷史市況。這一點屬定義推論，非文獻引述。

### （e）補充：四種做法以外，文獻已有的量測與緩解工具

以下不屬題目所列四種做法，但屬同一問題領域，列出備查：

| 工具／方法 | 做什麼 | 出處 |
|---|---|---|
| **LAP（Lookahead Propensity）** | 以「只給日期的回憶查詢」估算模型已內化某公司某日結果的機率，作為污染診斷統計量；作者定位為「cost-efficient, diagnostic tool」 | [arXiv:2512.23847](https://arxiv.org/abs/2512.23847) |
| **FinCAD** | 推論期（inference-time）的 Context-Aware Decoding 改良，不需重訓即壓抑模型對歷史結局的記憶。實測：在 5 個 7–14B 模型、5 隻大型股上，把已記憶日期的樣本內回測報酬削減最多 −67.1%，同時 2025 年樣本外報酬與基準相差在 8,000 美元內、Sharpe 相差 0.10 內，通用推理能力損失在 1.7 個百分點內；在 11 個模型的排行榜上，把樣本內／樣本外的 Spearman 相關由 +0.779 提升至 +0.846 | [arXiv:2605.24564](https://arxiv.org/abs/2605.24564) |
| **Shapley-DCLR + TimeSPEC** | 以 claim 層級量度「決策依據中有多少比例來自受污染的截止日後資訊」，並以時序過濾檢索加 claim 監督把預測錨定在截止日前證據。作者報告檢索與監督兩者缺一不可 | [arXiv:2602.17234](https://arxiv.org/abs/2602.17234) |
| **洩漏調整分數（leakage-adjusted score）** | 以配對乾淨對照組作參照點，把回測分數的洩漏部分扣減；作者以「在孿生模型中植入已知份量的洩漏」驗證能回收注入量，並在未受污染題目上得出零結果 | [arXiv:2608.02985](https://arxiv.org/abs/2608.02985) |
| **Structural Validity Framework 與評估清單** | Kong 等十位作者的立場論文，識別金融 LLM 應用的五種偏差：前視偏差、倖存者偏差、敘事偏差、目標偏差、成本偏差。他們覆核 2023–2025 年的 164 篇論文，發現**沒有任何一種偏差在超過 28% 的研究中被討論** | [arXiv:2602.14233](https://arxiv.org/abs/2602.14233) |

**關於一項未能核實的數字**：搜尋結果摘要曾出現「日期過濾檢索可把洩漏放大 4.7 倍」的說法。本次直接查閱 arXiv:2608.02985 與 arXiv:2602.17234 全文／摘要頁，**均未能核到此數字**。故本報告不採用該數字。

---

## 四、每次判斷的成本量級估算

### 4.1 假設

- 輸入：每次判斷 3,000–5,000 token
- 輸出：每次判斷 1,000 token
- 不用批次折扣、不用 prompt caching、不計伺服器端工具（如網頁搜尋）額外收費
- 牌價一律取查證日 2026-08-27 的官方公開牌價

### 4.2 牌價（每百萬 token，美元）

| 廠商 | 模型 | 輸入 | 輸出 | 出處 |
|---|---|---|---|---|
| Anthropic | Claude Fable 5 | $10 | $50 | [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Anthropic | Claude Opus 5 | $5 | $25 | 同上 |
| Anthropic | Claude Opus 4.5 | $5 | $25 | 同上 |
| Anthropic | Claude Sonnet 5 | $2 | $10 | 同上 |
| Anthropic | Claude Sonnet 4.5 | $3 | $15 | 同上 |
| Anthropic | Claude Haiku 4.5 | $1 | $5 | 同上 |
| OpenAI | gpt-5.6-sol | $4 | $20 | [OpenAI Pricing](https://developers.openai.com/api/docs/pricing) |
| OpenAI | gpt-5.6-terra | $2 | $12 | 同上 |
| OpenAI | gpt-5.6-luna | $0.20 | $1.20 | 同上 |
| OpenAI | gpt-5 | $1.25 | $10 | 同上 |
| OpenAI | gpt-4.1 | $2 | $8 | 同上 |
| OpenAI | gpt-4o | $2.50 | $10 | 同上 |
| OpenAI | o3 | $2 | $8 | 同上 |
| OpenAI | gpt-3.5-turbo | $0.50 | $1.50 | 同上 |

### 4.3 每次判斷成本（美元）

計法：輸入 token 數 × 輸入牌價 ÷ 1,000,000 ＋ 輸出 token 數 × 輸出牌價 ÷ 1,000,000

| 模型 | 輸入 3,000 + 輸出 1,000 | 輸入 5,000 + 輸出 1,000 |
|---|---|---|
| Claude Fable 5 | $0.0800 | $0.1000 |
| Claude Opus 5 | $0.0400 | $0.0500 |
| Claude Opus 4.5 | $0.0400 | $0.0500 |
| Claude Sonnet 4.5 | $0.0240 | $0.0300 |
| Claude Sonnet 5 | $0.0160 | $0.0200 |
| Claude Haiku 4.5 | $0.0080 | $0.0100 |
| gpt-5.6-sol | $0.0320 | $0.0400 |
| gpt-5.6-terra | $0.0180 | $0.0220 |
| gpt-4o | $0.0175 | $0.0225 |
| gpt-4.1 | $0.0140 | $0.0180 |
| o3 | $0.0140 | $0.0180 |
| gpt-5 | $0.0138 | $0.0163 |
| gpt-3.5-turbo | $0.0030 | $0.0040 |
| gpt-5.6-luna | $0.0018 | $0.0022 |

**量級**：以輸入 4,000 + 輸出 1,000 的中位假設計，每次判斷約在 **US$0.002 至 US$0.09** 之間，視乎模型；主流中階模型（Sonnet 5、gpt-5.6-terra、gpt-4o、gpt-4.1）落在 **每次約 US$0.015–0.02** 這一格，即**每 1,000 次判斷約 15 至 20 美元**。

### 4.4 規模推算（輸入 4,000 + 輸出 1,000）

| 模型 | 1,000 次 | 10,000 次 | 100,000 次 |
|---|---|---|---|
| Claude Opus 5 | $45 | $450 | $45,000 |
| gpt-5.6-sol | $36 | $360 | $36,000 |
| Claude Sonnet 5 | $18 | $180 | $18,000 |
| gpt-4o | $20 | $200 | $20,000 |
| gpt-4.1 / o3 | $16 | $160 | $16,000 |
| Claude Haiku 4.5 | $9 | $90 | $9,000 |
| gpt-3.5-turbo | $3.50 | $35 | $3,500 |
| gpt-5.6-luna | $2 | $20 | $2,000 |

參考量級：若一段回測期覆蓋 100 隻股票、每月一個判斷時點、跑三年，即 100 × 12 × 3 = 3,600 次判斷。

### 4.5 令上表偏低或偏高的因素（全部有官方出處）

**令實際成本偏高的因素：**

1. **推理／思考 token 計入輸出。** Claude Opus 5 與 Sonnet 5 的預設 effort 是 `high`，Claude Fable 5 的 adaptive thinking 是「always on」。輸出 1,000 token 的假設在開啟思考的模型上會被明顯低估。
出處：<https://platform.claude.com/docs/en/docs/about-claude/models/overview>

2. **新 tokenizer 令同一段文字的 token 數增加約三成。** Anthropic 官方牌價頁註明：「Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer... This tokenizer produces approximately 30% more tokens for the same text.」即同一份 prompt 餵給 Claude Opus 5 / Sonnet 5 / Fable 5，實際 token 數會高於餵給 Sonnet 4.6 及更早的模型。
出處：<https://platform.claude.com/docs/en/about-claude/pricing>

3. **工具使用有額外 token 開銷。** 僅是宣告工具就會加入 286–804 個 system prompt token（視模型與 tool_choice）；網頁搜尋另按每 1,000 次搜尋 10 美元收費。
出處：同上

**令實際成本偏低的因素：**

4. **批次 API 五折。** Anthropic Batch API 對輸入與輸出均打五折；OpenAI 亦有批次折扣。回測是典型的非即時工作量，適用。
出處：<https://platform.claude.com/docs/en/about-claude/pricing>、<https://developers.openai.com/api/docs/pricing>

5. **Prompt caching 命中價為基礎輸入價的 10%。** 「人物判官」的角色設定與判斷框架若在大量判斷之間重用，該部分輸入的成本可降至一成（5 分鐘快取寫入為 1.25 倍、1 小時為 2 倍；官方指 5 分鐘快取在一次讀取後即回本）。OpenAI 方面 `gpt-5.6-sol` 的快取輸入價為 $0.40/MTok（基礎價的 10%）。
出處：<https://platform.claude.com/docs/en/about-claude/pricing>、<https://developers.openai.com/api/docs/models/gpt-5.6-sol>

**未估算的部分：**

6. **自行部署開放權重模型（Llama 2 / 3.1 / 3.3 / 4）沒有 per-token 牌價**，成本結構改為 GPU 租用或自置硬件加運維。本報告未對此作估算 —— 屬**未估算項**，非查無來源。

---

## 五、對 KARST-017 的事實層面提示

以下只列事實與由前四節事實直接得出的算術結果，不含建議措辭、不代任何人作決定。

### 關於「用更早截止日的模型」這條路的事實

1. 截至 2026-08-27，官方 API 上能覆蓋 2023 年全年的模型只有 `gpt-3.5-turbo`（截止 2021-09）。其牌價 $0.50 / $1.50 每百萬 token，換算成每次判斷（輸入 3,000–5,000、輸出 1,000）約 **US$0.0030–0.0040**，是本報告所列最便宜的一格之一。官方停用頁列明它 **2026-10-23 停用**。
2. 該日之後，官方 API 上截止日最早而未列停用日的是 `gpt-4o`（截止 2023-10-01），每次判斷約 **US$0.0175–0.0225**。它覆蓋不到 2023 年 1 月至 10 月。
3. Anthropic 全線現役模型的訓練資料截止日最早為 **2025-07**（Sonnet 4.5、Haiku 4.5）。這代表：只用 Anthropic 的話，2023 年、2024 年全期，以及 2025 年 1 月至 7 月，事實上覆蓋不到。
4. Google 全線現役 Gemini 模型（2.5 至 3.x）公布的知識截止日一律是 **2025-01**，同樣覆蓋不到 2023 與 2024。
5. 若要求「不受廠商退役排程影響」且「覆蓋 2023 年全年」，事實上只剩自行部署開放權重一條路：Llama 2 base 預訓練截止 2022-09（其 chat 版微調資料至 2023-07）。成本結構由 per-token 牌價轉為 GPU 時數，本報告未估算。
6. 成本方向：以每次判斷計，截止日越早的模型現時**反而越便宜**（`gpt-3.5-turbo` 每次約 US$0.003，對比旗艦 Claude Opus 5 每次約 US$0.045、gpt-5.6-sol 每次約 US$0.036，相差一個數量級）。但若改為自行部署，成本改為固定的算力開支，與判斷次數的關係跟牌價模式不同。
7. 舊模型的能力代價有文獻量度：point-in-time 模型「approach the performance of」同尺寸的 Gemma-3-4B、LLaMA-7B，「although a performance gap remains on several tasks」（arXiv:2607.11889）。
8. 名義截止日與實際截止日可能有落差（arXiv:2403.12958），故「模型截止日早於 T」不等同「模型對 T 之後完全無知」。
9. 就算換用舊模型，靠近其截止日的一段仍然分不清「近期效應／洩漏／真本事」（arXiv:2608.02985）。

### 關於其他三條路的事實

10. **資料層過濾（只餵時點前文本）不消除參數層記憶**；以搜尋引擎日期過濾器執行時，Google 有 71%、DuckDuckGo 有 81% 的題目至少一頁結果含重大截止日後洩漏（arXiv:2602.00758）。
11. **用 prompt 指示模型忽略截止日後知識，實測無效**（arXiv:2505.19533）。
12. **匿名化的資訊損失，在財報電話會議文本上被量度為比它防的前視偏差「更普遍、更嚴重」**（arXiv:2511.15364）；但在新聞標題上，匿名化反而提升樣本內策略表現（arXiv:2309.17322）。兩者結論方向不同，文本類型不同。
13. **前向驗證的乾淨樣本期，由所用模型的截止日起算**。以 `gpt-5.6-sol`（截止 2026-02-16）為例，至 2026-08-27 只有約 6 個月。每換一次更新的模型，這個時鐘重設一次。
14. 有現成可搬的量測工具四款：LAP 診斷（arXiv:2512.23847）、FinCAD 推論期抑制（arXiv:2605.24564）、Shapley-DCLR + TimeSPEC（arXiv:2602.17234）、洩漏調整分數（arXiv:2608.02985）。FinCAD 的公開實測範圍是 5 個 7–14B 開放權重模型、5 隻大型股。
15. 這個問題在文獻中屬普遍未處理狀態：覆核 2023–2025 年 164 篇金融 LLM 論文，沒有任何一種偏差在超過 28% 的研究中被討論（arXiv:2602.14233）。

### 事實上互相衝突的兩點（不作調和）

16. 第 6 點（越舊越平）與第 7 點（越舊能力越弱）在成本與能力兩軸上指向相反方向。第 3、4 點（Anthropic 與 Google 完全覆蓋不到 2023–2024）令「留在現用廠商」與「覆蓋 2023–2024 回測期」在事實上不能同時成立。以上僅陳述，不作取捨。

---

## 附錄：查無可靠來源的項目

以下項目本次未能取得明確官方或可信來源，一律不作推測填補：

| 項目 | 狀況 |
|---|---|
| Qwen3 系列官方訓練／知識截止日 | 官方 GitHub 討論串（QwenLM/Qwen3 #1093）中，社群向維護者查詢，維護者轉問內部後至今無官方答覆。**查無可靠來源** |
| Mistral Large 3（`mistral-large-2512`）官方截止日 | 官方文件頁 docs.mistral.ai 未列訓練／知識截止日。**查無可靠來源** |
| OpenAI `gpt-5.1` / `gpt-5.2` / `gpt-5.4` / `gpt-5.5` 的知識截止日 | 官方牌價頁列有價錢，但本次未在官方模型頁核到截止日。**查無可靠來源** |
| Anthropic Opus 4.8 / 4.7 / 4.6 與 Sonnet 4.6 的「訓練資料截止日」（相對於「可靠知識截止日」） | 官方支援頁只給單一個「trained on data up until」日期；本次未在官方頁核到這幾個模型兩個日期的分列值。**部分查無來源** |
| Gemini 3.5 / 3.6 / 3.7 Flash 的個別模型頁截止日 | 個別模型頁未列；只有 Gemini 3 開發者指南 FAQ 以「Gemini 3 models」統稱 2025-01。**間接來源** |
| 「日期過濾檢索把洩漏放大 4.7 倍」 | 搜尋結果摘要提及，但直接查閱 arXiv:2608.02985 與 arXiv:2602.17234 均未能核到。**不採用** |
| 上市公司在財經文本中被 LLM 重新識別的比率 | 現有重新識別文獻（arXiv:2603.18382、arXiv:2510.09184）場景為個人身份，非上市公司。**查無直接來源** |
| 同一 persona prompt 在不同世代模型上的判斷風格漂移量度 | **查無可靠來源** |
| 自行部署開放權重模型的每次判斷成本 | 無 per-token 牌價，需按 GPU 時數估算。**本報告未估算**（非查無來源） |

---

*報告完。所有事實查證日期：2026-08-27。*
