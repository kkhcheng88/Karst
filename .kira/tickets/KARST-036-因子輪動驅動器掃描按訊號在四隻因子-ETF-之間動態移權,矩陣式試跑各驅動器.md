---
id: KARST-036
title: 因子輪動驅動器掃描:按訊號在四隻因子 ETF 之間動態移權,矩陣式試跑各驅動器
type: task
createdAt: 2026-08-28
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-029, KARST-031]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

因子混合策略自此不止固定權重:可以指定一個「驅動器」——由四隻因子 ETF 自身價格(或另加免費宏觀序列)算出的訊號,按換倉節奏把權重在四者之間移動——並以矩陣式一次過試跑多個驅動器 × 多組參數,交出一張成績表與穩健平原判讀,讓用戶看到「只用這四隻,靠什麼推動移權最有效」。用戶 2026-08-28 原話「I would like to know what is the best driver to move between 4 to get the best portfolio just with the 4」「I don't mind overfitting at first」。首批候選驅動器由 agent 按文獻提出(例:因子動量排名、相對強弱、逆波幅、大市趨勢開關),全部參數可掃描、不設預設;需要額外外部數據時在票上列明來源與是否免費。

## 驗收條件

- [ ] 至少四個驅動器各以同一套快照、同一期間、同一換倉節奏跑得出完整回測,成績表列齊八項指標與對固定權重最佳格的差距
- [ ] 每個驅動器連同其參數格出一份穩健平原報告,孤峰按 KARST-029 判準標出
- [ ] 驅動器是策略層可換件:換驅動器不改引擎、不改因子混合策略的目標比重路徑
- [ ] 所需外部數據(若有)列明來源、免費與否、知情時間處置

## 結果

## 留言
