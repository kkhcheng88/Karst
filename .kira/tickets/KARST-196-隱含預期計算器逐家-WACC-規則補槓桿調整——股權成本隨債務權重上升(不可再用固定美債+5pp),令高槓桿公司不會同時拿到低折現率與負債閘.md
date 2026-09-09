---
id: KARST-196
title: 隱含預期計算器逐家 WACC 規則補槓桿調整——股權成本隨債務權重上升(不可再用固定美債+5pp),令高槓桿公司不會同時拿到低折現率與負債閘通行證;對六十家重跑出前後差異
type: task
createdAt: 2026-09-09
risk: low
model: opus
fits: KARST-195 留言第二件:TROX/CLVT/LUMN/COLL 債務補上後債務權重跳到六成以上,KARST-193 規則機械地把 WACC 由 10.0% 拉低到 6.0–7.0%,估值被推高;COLL 是正本十二家之一、現時兩個「小額初始」候選之一,直接受影響;規則本身沒有下限,高槓桿又剛好過負債閘的公司會同時拿到便宜折現率與通行證
dependsOn: [KARST-195]
claimedBy: null
deliverable: KARST-D04
---

## 工作內容

對象 strategy/tools/implied_expectations.py 與 README.md,必須建基於 KARST-195 之後的版本(八處取數修復、新鮮度閘、收市價退回、_meta 四鍵),不得倒退;改前先備份到 ~/.claude/backups/。現行規則(KARST-190/193):股權成本 = 十年期美債 + 5pp 固定;債務成本 =(美債 + 2.0pp 示例信用差價)×(1 − 23%);按市值對帳面有息負債加權;四捨五入至 0.5%。缺陷:股權成本不隨槓桿變,債務權重越高 WACC 越低,方向與公司金融基本結論相反(槓桿升,股權風險升,WACC 大致持平,只差稅盾)。修法要求:(一)把 5pp 視為零負債(無槓桿)股權溢價,按 D/E 與稅率重槓桿——Hamada 式 levered premium = 5pp × (1 + (1 − t) × D/E),D/E 用市值對帳面有息負債(與現行權重同一口徑,含融資租賃);或等價地令 WACC 不得低於「無槓桿股權成本 − 稅盾」;二選一,README 寫明公式、出處與理由,不得只加一個任意數字下限;(二)D/E 極端值(如 KRMN 141 倍淨負債對現金流那類)要設合理上限並印警告,不讓溢價爆到無意義;(三)淨現金公司不受影響:D/E = 0 時溢價 = 5pp,LULU 基準每股值須與 KARST-193/195 逐位一致(156.77);(四)_meta 與 rate_inputs 加欄記無槓桿溢價、重槓桿後溢價、D/E、用了哪條路,JSON 只加欄不刪欄,四條折現率路徑(人手覆寫 / rate_inputs / discount_rate 批次值 / CASES 手填)舊呼叫方式仍可跑;(五)對 screen60_full.csv 六十家機械重跑,出前後差異表(WACC、基準每股值、一年回報、過不過底線),標翻轉家數與名單,特別列出 TROX、CLVT、LUMN、COLL 四家;落檔 research/2026-09-methodology/2026-09-09-①候選池全量/ 同目錄,檔名帶 KARST197;不改十四張卡文字;README 末更正紀錄;A-061 不動,如查出新假設崩塌照規矩入冊。

## 驗收條件

- [ ] 股權成本隨槓桿上升的公式落地,README 寫明公式、出處與理由;D/E = 0 時與 KARST-193/195 逐位一致(LULU 156.77)
- [ ] TROX、CLVT、LUMN、COLL 四家修後 WACC 不低於無槓桿口徑減稅盾,前後數字落檔;極端 D/E 有上限並印警告
- [ ] 六十家前後差異表落檔,標底線翻轉家數與名單;JSON 只加欄不刪欄、四條折現率路徑舊呼叫方式仍可跑
- [ ] 不改 karst/、library/、候選卡文字、其他票;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
