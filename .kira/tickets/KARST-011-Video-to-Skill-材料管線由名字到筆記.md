---
id: KARST-011
title: Video to Skill 材料管線:由名字到筆記
type: task
createdAt: 2026-08-26
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
epic: V1 藍圖
deliverable: KARST-D01
closed: 2026-08-27
---

## 工作內容

完成之後有什麼是之前做不到的:用戶只需給一個 KOL 交易員的名字,即可跑通「搜尋→片單候選(用戶剔選)→字幕抽取→代理抽取性質→筆記落檔 research/」全流程,不再需要逐條貼連結。本 session 已用零散腳本驗證每一步可行(yt-dlp 搜尋與字幕、json3 轉文字、代理抽取模板);此票把它們整理成倉內可重跑的腳本與步驟文件,並寫明三個限制的處理方式:無字幕片的跳過與記錄、自動字幕的數字回片核對要求、業績聲稱一律標「自述未核實」。片單篩選準則(訪談/系統披露類優先、行情評論類跳過)成文,且候選清單必須交用戶剔選、不代選。

## 驗收條件

- [x] 倉內有可重跑腳本:輸入名字或影片 id 清單,輸出字幕純文字檔
- [x] 管線步驟與篩選準則成文(含三個限制的處理方式)
- [x] 用一個新對象跑通一次全流程作驗收,筆記落 research/

## 結果

· 2026-08-26 12:00 零散腳本已整理成倉內可重跑工具,存 `tools/video-to-skill/`。`search.py` 名字→候選影片清單(CSV/MD),已用「施傅」實測,55 筆去重候選落 `research/_candidates/施傅/`;`captions.py` video id 清單→字幕純文字檔,無字幕的記入 `skipped.md`、不中止其餘影片,內建 429 節流(`--sleep-requests 2` + 每片間 `--sleep`);`json3_to_text.py` 搬自本 session scratchpad 的參考實作,同時可當 CLI 與模組被 `captions.py` 呼叫;`README.md` 寫步驟、篩選準則(訪談/系統披露類優先、行情評論類跳過)、三個限制(429、無字幕跳過、自動字幕數字回片核對)的處理方式、代理抽取提示模板(沿用 Eric 筆記章節形態)。第三條驗收(新對象跑全流程)只做到候選清單,見下方舉手留言,票不關檔。
· 2026-08-27 00:50 用新對象 Situational Awareness(Leopold Aschenbrenner)跑通全流程,完成第三條驗收。用戶從 33 條候選(`research/_candidates/Situational Awareness/candidates.md`)剔選 7 條訪談/系統披露/講策略類影片抽字幕,`captions.py` 加了 `--sub-langs` 語言優先順序參數(此次 en 優先於 zh-Hant,原本只支援中文優先寫死),7 條全部有英文自動字幕、0 條跳過。論文原文站 `situational-awareness.ai` 對 WebFetch 一律回 403,改用 WebSearch 取第三方摘要並與影片逐字稿交叉核對數字一致,筆記內已標明此段落是轉引不是原文直讀。筆記落 `research/2026-08-27-situational-awareness-video-to-skill.md`,按用戶指示只記投資論點與自述倉位/風險原則,不評爆倉,基金近況相關第三方標題全部歸入筆記末「事實核查待辦」一節,只列出處不下結論,註明關乎 D-017、交主線處理。KARST-011 三條驗收條件全數完成,票關檔。

## 留言

### agent:KARST-011-video-to-skill · 2026-08-26 23:02
**問題**：第三條驗收(用一個新對象跑通全流程)要用戶剔選候選片單,可以開始揀「施傅」的候選影片抽字幕嗎?

**前文後理**：腳本已整理好(search.py/captions.py/json3_to_text.py)並用「施傅」(本地知名交易員 KOL)實測 search.py:三條查詢「交易 訪談」「交易系統」「投資 心法」各取 20 筆,去重後 55 筆候選,已落 research/_candidates/施傅/candidates.md 與 candidates.csv。按票的指示,候選清單只出到這一步,下一步(抽字幕)需要用戶剔選、不代選。

**建議**：建議直接用「施傅」做這次驗收對象:候選清單裡已有幾條標題含「訪問」「系統」「心法」「揭秘」的片段(例:Jos_paSjN2Q 3大交易高手心得總結、9jFwQdDMKDQ 量化・即市交流、Q551t9LzRdQ 施傅黑歷史曝光),屬訪談/系統披露類,是這條管線最適合的材料;直播類(標題含 Live)建議跳過,多數只有即市評論、且通常無逐字稿。

**選項**：
- 甲（建議）：用「施傅」剔選 3-5 條候選片,交回 video id 清單,由我跑字幕抽取+代理抽取+落筆記,完成第三條驗收 —— 候選清單已經有質素較高的訪談類片段,不必重新搜尋
- 乙：换一個對象重新搜尋(例:張智威或其他),再出一份新候選清單 —— 如果對「施傅」這個人選有保留
- 丙：先不驗收第三條,票維持現狀,留待日後再議 —— 如果現階段暫不需要跑通示範

**要睇邊份稿**：
- research/_candidates/施傅/candidates.md

### agent:KARST-011-video-to-skill · 2026-08-27 00:34
**裁決**：示範對象改為 Situational Awareness(Leopold Aschenbrenner),不用「施傅」;用戶已從候選清單剔選 7 條片抽字幕(訪談/系統披露/講策略類),爆倉/清算/Citadel 類第三方片與中文轉述頻道全部跳過,論文原文改用 WebFetch/WebSearch 取代抽字幕。

**出處**：用戶 2026-08-27 剔選(經派工訊息轉達候選清單勾選結果與抽取範圍指示)

### human:Kaho · 2026-08-27 23:09
交付品「Karst v1 規格」（KARST-D01）已簽收。

**簽收人留言**：用戶 2026-08-27 於原生多選介面勾選簽收
