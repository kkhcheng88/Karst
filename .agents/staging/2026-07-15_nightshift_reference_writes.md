# 夜班 2026-07-15 — 待日間過檔到 Reference tree 嘅寫入

> 夜班 headless run 寫唔到工作目錄外(`C:\projects\Investment\Reference\` 被權限擋,符合 `nightshift-permission-boundary` 記憶)。
> 以下內容夜班已蒸餾完成,請日間 session 人手過檔。

---

## 動作 1|append 落 `..\Reference\distillations\2026-06-24_backtest-everything-distillation.md` 檔尾

（貼喺現有 Addendum 2026-07-11 之後、檔案最尾）

```markdown

---

## Addendum 2026-07-15 — transcripts 65-66（Credit Spread vs Iron Condor,10,000 trades;65/66 同片重複上傳）

### Bull Put vs Iron Condor 對決（65/66:「10,000 trades、one clear winner」）

Claim:SPY、2018-2023、30 DTE、50% PT、無止損,三個 delta（10/16/20）head-to-head,唯一變數係結構。
- **Iron condor**:10Δ +$18,186（77% win、PF 1.52）;16Δ +$8,172;20Δ +$1,024（68% win）。只有 10Δ 賺到有意義嘅錢。
- **Bull put credit spread**:10Δ +$21,943（82% win、PF 1.71）;16Δ +$14,271（78% win）;20Δ +$9,255（75% win）。**每個 delta 都贏對應 IC**。
- **Bear call credit spread**:10Δ −$3,157;16Δ −$5,030;20Δ −$7,231。**每個 delta 都蝕**。
- 核心論點:IC = bull put（贏家)+ bear call（輸家);IC 利潤 ≈ bull put − bear call drag。Delta 越闊,IC 越跑輸（10Δ gap $3.6k → 20Δ gap $7.8k）。
- **資本效率反駁**:同資本開兩張 bull put（+$40,186)vs 一張 IC（+$18,186)= **多賺 $25,300**。
- BS POP 偏差:10Δ 理論 90% 到期作廢;實際 bull put 贏 82%（高於預期)、bear call 贏 73%（低於預期),9pp gap 來自市場上升 drift。原話結論:「on SPY, QQQ, or any stock, bull puts win」;IC 只喺真正無方向 bias 嘅 range 市 / 商品 / 外匯先合理。

**Karst 判讀（佐證既有結論,不改工具箱;資本效率建議唔採納):**
1. **直接佐證 §25 #7 + #21**:「bull put 勝 bear call、因市場上升 drift」同「BS POP 錯 10-16pp、bull put overperform / bear call underperform」—— 此片以 head-to-head 固定 delta 再現同一機制,樣本再擴。Verdict = **佐證**（非新事實,增信既有立場）。
2. **Multiple-testing 相對乾淨（增信)**:固定 delta 逐個對打、無「掃 N 配置揀最靚」嘅選擇偏差（對比 Addendum 07-08 A 段 0DTE「48 配置揀 3 個 100% win」要重扣);此片方法較 robust,折扣較細。惟仍係樣本內、單一路徑。
3. **「開兩張 bull put」資本效率建議 = 唔採納（危險簡化):**片方將「同 buying power 開兩張 bull put」報做 +$25,300 純增益,但呢個係**加倍同向方向曝險** —— 真 crash 兩張 bull put 同時被擊穿、尾部相關性 = 1。IC 個 bear-call 邊雖然樣本內蝕錢,結構上係(弱)上行對沖;移除佢 = 賣埋最後一層保護去搏 directional theta。單一大致上升路徑（2018-2023 只含一次見底即回嘅 bear)先令「雙 bull put」睇落免費午餐。此建議與用戶「MaxDD 貼 SPY」風險胃納相沖時要以風控為先,**不納入**。
4. **Survivorship / regime 條件性（需標注):**僅 SPY、2018-2023 單一(大致上升)regime。「bear call 每 delta 都蝕」係 **structural-drift-conditional** —— 片方自己都承認 range 市 / 商品 / 外匯 IC 才合理。喺持續 range/chop 或 secular bear,bear-call 邊會有貢獻,呢個負面結論唔應外推成「bear call 永遠蝕」。同 §25 #8「只有 medium VIX (15-25) IC 先 work」一致:IC 係 regime 工具唔係全天候工具。
5. **用戶鐵律不受挑戰（方向一致):**bull put / IC @ 10-20Δ、30 DTE = **非**短 DTE OTM（30 DTE、有 room to move),與「唔做短 DTE OTM」不衝突。惟 Karst 現役工具係 **CSP（cash-secured、單邊、現金全額),唔係 defined-risk bull put spread;兩者方向順風邏輯相同(§25 #13 CSP@10-20Δ QQQ 98.6% win 同源),但 spread 用 buying-power reduction 換 defined risk = 另一風險/資本 profile。**不新增 bull put spread 入四工具**;此片只佐證「賣方要企順 drift 嘅邊」嘅既有原則。
6. **資料誠信瑕疵（標注,不影響核心):**65、66 為同一講稿重複上載(第四次出現同類 re-upload,同 §24.8 影片 14/15、Addendum 07-08 59/60、07-11 63/64)。兩片內部數字互相矛盾且自我矛盾(bull put 10Δ 報 $21,943 又報 $21,743;IC 10Δ 報 $18,186 又報 $18,586;bull put 20Δ $9,255 vs $9,555;bear call 10Δ −$3,157 vs −$3,557)—— ASR + 講稿口誤,量級一致故核心結論不受影響,全部按原引保留、不採信到小數位。

*(Fetch 記錄:夜班 headless run 2026-07-15,65/66 蒸餾完成;待日間 session 過檔。)*
```

## 動作 2|喺 `..\Reference\raw_data\backtest_everything_transcripts\_PENDING_ANALYSIS.md` 剔以下兩項

```
- [x] 65_xE90se6PRRw.txt — Credit Spreads vs Iron Condors: 10,000 Trades. One
- [x] 66_1TiYPwEG1IQ.txt — Credit Spreads vs Iron Condors: 10,000 Trades. One
```

（夜班冇剔——寫入被權限擋,而且蒸餾未經人手覆核。）
