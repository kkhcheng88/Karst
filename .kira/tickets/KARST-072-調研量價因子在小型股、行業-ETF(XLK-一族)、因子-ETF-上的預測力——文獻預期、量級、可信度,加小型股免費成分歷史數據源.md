---
id: KARST-072
title: 調研:量價因子在小型股、行業 ETF(XLK 一族)、因子 ETF 上的預測力——文獻預期、量級、可信度,加小型股免費成分歷史數據源
type: research
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-069]
claimedBy: null
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 裁決(原話「Next I want to test 1) The small stocks, and XLK and related series of industrial ETF, and the 4 S&P factor ETF」),並明令實測前先講文獻結論(原話「before we run any academic stuff ourselves, let me know the research insight here」)。本票答四件:(1) 小型股:技術/量價因子在美股小型股的橫斷面預測力是否明顯強於大型股(文獻與量級,例如 Hou Xue Zhang 2020 異常在小型股集中、微型股流動性限制),以及免費可得的小型股成分歷史來源(標普 600 / 羅素 2000 歷史成分,授權、覆蓋年份、退市覆蓋),yfinance 對小型股退市代號的覆蓋限制;(2) 行業 ETF(SPDR 十一隻:XLK、XLF、XLE、XLV、XLI、XLY、XLP、XLU、XLB、XLRE、XLC):行業輪動用技術訊號的文獻(動量、相對強弱、均線)與量級;要點:十一隻的橫斷面太窄,預測力應改量「時間序列預測力」(每隻 ETF 自己的因子值對自己未來回報),說明兩種量法的分別與各自出處;(3) 四隻因子 ETF(QUAL、VLUE、MTUM、USMV,D-031 已定 MSCI 套):因子擇時(factor timing)文獻——Asness 2016 對 Arnott 2016 的爭論、Bender 等;技術訊號擇時因子 ETF 的證據與量級;(4) 結語:三個宇宙各自「預期見到多強訊號、用哪種量法、可信度」一張表,供主 agent 在實測前向用戶交代。輸出 research/2026-08-29-factor-power-smallcap-sector-etf.md,每條有 URL/DOI。不動程式、不動庫。

## 驗收條件

- [x] 研究檔落檔,四節各有出處;小型股數據源列授權與覆蓋年份
- [x] 結語一張表:三個宇宙 × 預期量級 × 量法 × 可信度
- [x] 不動程式、不動庫

## 結果

研究檔:`research/2026-08-29-factor-power-smallcap-sector-etf.md`。四件工作內容各一句:
(1) 小型股——技術異常在小型股/微型股集中(Hou Xue Zhang 2020、Fama French 2008),流動性
限制會打折(Novy-Marx & Velikov 2016);免費成分歷史比標普 500 更弱,查不到現成含退市股的
標普 600/羅素 2000 數據集,只能靠 Wikipedia 變動表自行重建或接受「只含現行成分」的簡化。
(2) 十一隻行業 ETF——橫斷面太窄不能用 KARST-066 那種逐日跨資產 IC,應改用時間序列預測力
(Moskowitz Ooi Pedersen 2012 出處),行業動量文獻(Moskowitz & Grinblatt 1999)機構級支持
方向,但窗口偏長(月度以上),預期日線量價因子短窗口訊號偏弱。(3) 四隻因子 ETF——Asness
2016 與 Arnott 2016 有公開機構級爭論,整體證據偏向「擇時難、不穩定」(Bender et al. 2018,
查證後作者所屬機構應為 State Street Global Advisors,非票面猜測的 MSCI),樣本量小,預期
三個宇宙中訊號最弱、可信度最低。(4) 結語表已落檔於研究檔第四節,精簡版:小型股(量級最高、
用橫斷面 IC、可信度中高、預期比標普 500 多測到達標因子但少於起步十二隻)、行業 ETF(量級
中等偏長窗口、用時間序列預測力、可信度中等、預期短窗口弱長窗口略好)、因子 ETF(量級最低、
量法接近時間序列擇時、可信度中低、預期測不出穩定訊號)。

## 留言
