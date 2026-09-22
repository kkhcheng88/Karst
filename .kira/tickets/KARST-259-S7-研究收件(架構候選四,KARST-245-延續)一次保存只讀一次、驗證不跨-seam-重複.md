---
id: KARST-259
title: S7 研究收件(架構候選四,KARST-245 延續):一次保存只讀一次、驗證不跨 seam 重複
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程:service 收件段與 agents/research.py
dependsOn: [KARST-258]
claimedBy: Opus-S7
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依執行計劃 §三 7 及架構評審候選四。現況一次保存跨四個 module,packet.json 讀三次、中途改寫一次,驗證指紋憑證因驗證跨 seam 重複而存在;另有 ImportError 退路與注入 intake 簽名不一致。收件收攏為一個 module,經 S6 證據倉讀寫。已保存研究版本與計算回執的讀回結果不變。程式只住 karst/。

## 驗收條件

- [x] 一次保存 packet 只讀一次
- [x] ImportError 退路移除,注入 intake 簽名一致
- [x] 既有研究收件、版本讀回、HTTP 測試全部通過
- [x] 以既有 fixture 保存同一研究,版本 ID 與回執與重構前相同

## 結果

· 2026-09-23 03:24 研究收件收攏為 `karst/agents/research.py` 的 `save()`,`service.save_research` 只轉交
- 經 `CompanyBundle` 讀一次 `working()`,補查請求在記憶體登記,`_build` 補工程欄位並 `check_packet`／`check_research` 各一次,算計算回執,store 在交易內追加版本;請求有增加且版本存入(非衝突)後才寫回 packet。
- 實測一次保存讀 packet:重構前 4 次(另中途改寫一次),重構後 1 次;`check_packet` 1 次。
- 移除:`ImportError` 退路、注入 `intake=` 參數(簽名不一致問題隨之消失)、驗證指紋憑證 `Verified`／`fingerprint` 及 `_verify`、`_selected`、`_register_requests`。
- 版本 ID 不變的證明:重構前以舊路徑、固定時鐘對契約 0.3.0 與 0.4.0 fixture 各保存首版與更新版,記下版本 ID 與計算回執 digest,寫成 `test_version_inputs.SameVersionsTests` 的常數;重構後同樣輸入逐字相同,重試冪等、各層 `assessed_at` 沿用規則不變。
- 行為改善:衝突或拒收時證據倉的 packet 保持原樣(舊路徑在驗證前已改寫)。
- 全套測試 453 passed、1 skipped、1 failed(`test_reader` 符號連結 WinError 1314,本機權限,與本票無關)。
- KARST-262 落點:範圍控制以一個新參數交給 `save()`,只在 `_build` 建層與沿用 `assessed_at` 處執行;呼叫方只傳範圍,規則不散到 MCP、API adapter 或管線。
- 詞彙表補「研究收件 / research intake」;`karst/README.md` 對應段落已改寫。

## 留言

### agent:Opus-S7 · 2026-09-23 03:24

完成並關票。只在 worktree 分支提交,未 push、未合併。
