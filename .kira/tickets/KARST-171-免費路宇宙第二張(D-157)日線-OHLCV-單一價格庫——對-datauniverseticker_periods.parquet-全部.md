---
id: KARST-171
title: 免費路宇宙第二張(D-157):日線 OHLCV 單一價格庫——對 data/universe/ticker_periods.parquet 全部 5,952 代號時段抓 yfinance 日線(40 個一批、1.2–2 秒退讓),以實體主鍵(entity_id=CIK)加代號時段為 join 鍵存入 data/prices/daily/ 單一價格庫,連 manifest 與失敗清單;順帶收入 154 家已抓收市價與 6 個未登記價格檔(D-153),並出 universe_smallcap_v1(剔 SIC 6221 信託型 ETP)
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: Claude Opus 5
deliverable: KARST-D02
closed: 2026-09-03
---

## 工作內容

背景:KARST-167 交付實體表 5,257 家、代號時段表 5,952 段(data/universe/、RULES.md 第八節記跑數後兩條規則修正);報告 research/2026-09-03-小型股宇宙v0盤點.md 估價格抓取 45–90 分鐘、300–600MB、1–3% 失敗,並實測 yfinance 200 個一批不退讓成功率只有 32%,40 個一批加 1.2–2 秒退讓 99.3%。先讀:D-134、D-152、D-153、D-157;data/universe/RULES.md;experiments/2026-09-03-price-registry-study/價格登記路線盤點.md(154 家收市價位置 experiments/2026-09-02-narrative-layers-v2/data/new_close.parquet、六個未登記價格檔清單);karst/data/freeze.py 的 ensure_entities/_ensure_ticker_period/resolve_entity_ids(生產線已有實體主鍵做法,只讀參考,不改生產碼)。做法:①先出 data/universe/universe_smallcap_v1.csv:v0 剔 SIC 6221 信託型 ETP,RULES.md 加一節記 v1 規則,其餘不動;②價格庫格式:data/prices/daily/<entity_id>.parquet 或單一分區 parquet(自選,寫進 README),欄位至少 entity_id、ticker、date、open、high、low、close、adj_close、volume、source、fetchedAt;每段只抓該代號時段 valid_from 至 valid_to 之間(缺 valid_to 抓到今日);同一實體多段代號合併成一條時間序列;③manifest.csv 每代號時段一行:entity_id、ticker、valid_from、valid_to、rows、first_date、last_date、status(ok/partial/fail)、error;失敗清單另出 failed.csv,連續失敗者重試一次後放棄,不無限重試;④154 家新增收市價與 6 個未登記檔:先查其代號時段登記,已登記者 yfinance 重抓全 OHLCV 後舊檔留原位不刪(只在 README 標為已被單一價格庫取代);未登記者列出報主 agent,不擅自補登記;⑤全庫 >5MB 不入 git(data/ 已 gitignore),只 git add -f README.md、manifest.csv、failed.csv、腳本;⑥生產庫 karst.sqlite 只讀,SHA256 首 16 位維持 b168e9f45b578cf9;⑦報告 research/2026-09-03-單一價格庫盤點.md:覆蓋率(多少段 ok/partial/fail)、日期範圍分佈、與生產庫重疊代號抽 20 個對帳收市價差異、誠實聲明(yfinance 無退市股、除權調整口徑、倖存者口徑)。禁區:不開任何交易介面、不裝付費數據源、不用 MCP 連接器;Chinese 檔案只經 Read/Write/Edit;PYTHONUTF8=1;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁的用四格 raise 加 docs 鍵。

## 驗收條件

- [x] data/universe/universe_smallcap_v1.csv 出,RULES.md 加 v1 規則一節(剔 SIC 6221)
- [x] data/prices/daily/ 單一價格庫落地,以 entity_id 加代號時段為鍵;README.md、manifest.csv、failed.csv 用 git add -f 入庫;>5MB 檔不入 git
- [x] 5,952 代號時段抓取完成率 ≥97%(ok+partial),40 個一批加退讓;失敗者重試一次後列 failed.csv
- [x] 154 家新增價與 6 個未登記檔處理結果寫進報告;research/2026-09-03-單一價格庫盤點.md 含覆蓋率、20 個對帳樣本、誠實聲明
- [x] 生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言

### agent:Claude Opus 5 · 2026-09-03 09:20
收檔。commit 5b26af8。

誠實聲明:抓了 5,952 個代號時段的 yfinance 日線開高低收量,落成 data/prices/daily/(16 個分片、20,647,659 列、462MB),主鍵 entity_id(CIK);出了小型股名單 v1;盤點了 154 家新增收市價與六個未登記價格檔;與生產快照抽 20 個代號逐日對帳。沒有寫入生產庫、沒有刪任何舊檔、沒有改 entities.parquet 與 ticker_periods.parquet 一列、沒有補登記任何未登記代號。

主要數字:完成率(ok+partial)99.95%——ok 5,879 段、partial 70 段、fail 3 段(SVA、FBYDP、ORIS,三家都不在小型股名單內)。5,262 個實體之中 5,260 個有價。抓取 8.1 分鐘(149 批、40 個一批、1.2-2 秒退讓),比 KARST-167 估的 45-90 分鐘快五倍以上;落地 462MB,在估的 300-600MB 之內。別名閘跑過:primary 5,263 段、alias 689 段,只取 primary 的列 (entity_id, date) 零重複。名單 v1:剔 SIC 6221 信託型 ETP 71 家,小型股 3,188 → 3,117;AIFC、AIB、UROY 三家人手核為營運公司留下,理由逐家寫入 RULES.md 第九節。

對帳差異:20 個樣本之中 18 個逐日差在 0.0002% 以內(float 捨入層次)。兩個例外 LMT(-0.615%)與 TAP(-1.152%)全期是一個常數比率、標準差 2e-07——查實是快照日(2026-08-28)與本票抓取日(2026-09-03)之間除息,Yahoo 把新一筆股息追溯乘回整條歷史。後果寫進 README 第五節:已調整價不是不變量,同一個代號兩次抓取必然對不上帳,所以價格庫是原料庫不是快照,要復現的運行照舊要經凍結模組。另有三個代號(AMD、NFLX、VST)最大差落在快照當日一格,是未定稿收市價,KARST-164 已量過同一件事。

154 家與六個未登記檔:154 家之中 150 家已登記且已被本庫以全 OHLCV 覆蓋(舊檔缺開高低量),4 個未登記(EA、GTBIF、NXG、SPCX);timing-sweep 584 個之中 569 個已覆蓋;tenbagger-scan 10 個全覆蓋;sector-safety 與 fear-greed 兩個檔全是 ETF(SPY、板塊 SPDR、IEF),本宇宙刻意不收,未取代;casecontrol 是月線版式不同,未取代。舊檔一個都沒有刪,只在 README 第六節標明已被本庫取代。

三個交主 agent 的規則缺口(本票不改規則,理由:改收錄規則屬宇宙名單票的範圍):
1. I3「至少一份年報」會漏掉未交過年報的新上市與剛重組公司——XOM 今日在證監會代號表指向 ExxonMobil Holdings Corp(CIK 0002115436,2026 年重組的新控股公司)、HONA 指向 Honeywell Aerospace、SPCX 指向 SpaceX,三家都在主要交易所但整家不在宇宙內。這條規則與十倍股線的目標直接相衝:D-154 已記「漏掉的正是新上市與外國申報那批」。我押它要在第四張票之前改,否則量到的覆蓋率會偏低而且會被誤讀成「免費路不行」。
2. E3「交易所欄空白即剔」誤剔 AEP(納斯達克上市的大型公用事業,submissions.exchanges 是空陣列)。抽 400 個「有代號但不在實體表」的 CIK:76 個交易所欄空白,其中 19 個是 operating 且交過年報,推算全體約 130 家;逐家看多數是場外殼股,但 AEP 證明會誤剔真正的主板公司。
3. E4 只剔帶連字號的權證代號(-W[SI]?$),納斯達克無連字號的 XXXXW 整批漏網——70 個 partial 之中 69 個就是它們(IVDAW、OXBRW、MNTSW 一類,最後一日同是 2026-07-17)。權證的價格與正股是兩回事。

中途產物 data/prices/_parts/(368MB)合併完成之後已刪,單一副本原則。生產庫全程 mode=ro 唯讀,開工與收工兩次核 SHA256 首 16 位都是 b168e9f45b578cf9。報告 research/2026-09-03-單一價格庫盤點.md。
