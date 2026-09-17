---
id: KARST-247
title: V 估值能力:契約 0.4 方法分派、日期化多階段 FCFF、前瞻 P/E 與 EV 倍數(完整橋接)、敏感度與反推共用計算器並留回執、adapter 可呼叫計算
type: task
createdAt: 2026-09-18
risk: high
model: opus
fits: 一程做得完:calculations 方法分派 + 契約 0.4 + service/adapter 接線 + 頁面欄位;不做全行業方法庫
dependsOn: []
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依 strategy/specs/估值與視覺TA升級-ClaudeCode執行指令-v1.md §1(V1)實作,沿用 calculations / service.calculate / 收件 / 發布,做方法分派不建新引擎。契約新版本(0.4.0,0.2/0.3 舊發布照讀)支援帶 method 判別的 valuation 輸入與結果;首批方法:日期化多階段 FCFF DCF(估值日、各期現金流日期、期中/期末、stub、擴張末期與正常化終值分開)、前瞻 P/E、EV/EBIT 或 EV/EBITDA(完整股權橋接:現金、負債、非營運資產、少數股東、贖回權、可轉債/認股權、稀釋股數同一範圍;SBC 不漏不雙扣;未支持的複雜權益明列缺口);SOTP 以組合表達。經營 driver 帶期間、單位、來源引用。主模型、替代視角、敏感度、反推共用同一計算器並保留輸入/輸出/版本回執;反推列固定假設、求解變數、邊界、無解/多解。頁面分內在值、期限價格、TA 目標並可展開計算依據。API adapter 加可呼叫的計算工具(重用 service.calculate,不寫第二份算式)。程式只住 karst/,代號由參數傳入(D-180)。

## 驗收條件

- [ ] 舊年度慣例回歸:CF=[15,-30,60,175,260,327]、cash=748.848、debt=84.233、shares=66.5、其他資本項=0、r=9%、g=3.5% 得每股 73.03084457399436;百萬與 absolute 尺度換算後每股一致、EV/equity 單位正確
- [ ] 日期化 DCF 以獨立手算的 stub 例子驗過去/未來、期中/期末與終值日期
- [ ] 同一研究版本保存 DCF 加倍數兩種計算;改一項 driver 可追到每股結果;EV 與股權倍數不混用橋接
- [ ] 主研究/覆核在運行時真的呼叫計算工具,敏感度對到相同情境與回執(schema 通過不算)
- [ ] 舊研究(0.2/0.3)可取回重發布;不改 BE/AXTI 原發布;全套測試通過;生產碼零代號

## 結果

## 留言
