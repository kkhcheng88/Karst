---
id: KARST-173
title: 免費路宇宙第四張(D-157):覆蓋率驗證——用單一價格庫(KARST-171)與面板 v3(KARST-172)重算 138 家十倍股在 t0 的市值、指數成員身份、淨現金狀態,對 KARST-162/166 的 t0 剖面與 D-155 淨現金篩選重量一次(零新抓);同時出小型股宇宙 v1 的倖存者口徑基礎率(每年 10 倍股比率、>50% 回撤比率),全部標倖存者口徑;判詞只用存在/不存在/量不出
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: null
deliverable: KARST-D02
---

## 工作內容

背景:KARST-162(十倍股起步剖面,D-150 修正起步市值中位 9.8 億美元)與 KARST-166(安全邊際,淨現金 AUC 0.648、現金跑道篩會殺 22% 真十倍股)都在 728 家宇宙與面板 v2 上量,只約四分一十倍股在 t0 有面板;D-152/D-157 裁免費路全部基礎率標倖存者口徑。前置:KARST-171 與 KARST-172 已落地(未落地不要開跑,票上留言等)。先讀:D-150、D-152、D-154、D-155、D-157;research/2026-09-03-十倍股安全邊際.md 與 experiments/2026-09-03-tenbagger-safety/ 的判準與腳本;research/2026-09-03-小型股宇宙v0盤點.md;data/universe/RULES.md;data/prices/daily/README.md;data/panel/ 的 v3 說明。判準先凍結(CRITERIA.md 獨立 commit):①十倍股定義與 t0 定義照 KARST-162 一字不改;②市值=t0 收市價 × 最近申報股數(申報日 ≤ t0);③淨現金=現金+短投−總負債 >0(申報日 ≤ t0);④指數成員身份照現有成分期表;⑤基礎率分母=universe_smallcap_v1 在每年 1 月 1 日有價有股數的實體;⑥四數(D-148/149):有面板覆蓋率、起步市值中位、淨現金比率(十倍股對全宇宙)、>50% 回撤比率。產物 experiments/2026-09-03-universe-coverage/(CRITERIA.md、腳本、out/)、research/2026-09-03-十倍股覆蓋率重量.md:誠實聲明首段(倖存者口徑、申報日可得、近似入位),與 162/166 舊數逐項並列(舊數、新數、差多少、為什麼),A-045 依結果更新 status(經 Edit,附 verifiedAt 與證據)。禁區同 KARST-171/172。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [ ] CRITERIA.md 凍結並獨立 commit 在任何數字之前;零新抓(只讀價格庫、面板 v3、年報快取)
- [ ] 報告:誠實聲明首段、四數、與 KARST-162/166 舊數逐項並列、判詞只用存在/不存在/量不出
- [ ] A-045 在 assumptions.jsonl 更新 status 附 verifiedAt 與證據(經 Edit)
- [ ] 生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
