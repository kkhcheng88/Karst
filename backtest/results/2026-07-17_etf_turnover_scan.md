# ETF 全市場成交掃描 -- 盲點發現 + 擁擠軸輸入 (2026-07-17)

腳本: `backtest/experiments/exp_etf_turnover_scan.py`｜數據源: `backtest/data.py load()`(yfinance-first)+ yfinance `.info`(AUM/上市日)。

## 0. 方法論

- 掃描宇宙:147 隻美國上市 ETF(hardcode,見腳本 `UNIVERSE`,分 broad/sector/thematic_*/factor/international/commodity 等類別)。**刻意排除**槓桿/反向產品(2x/3x Bull/Bear/Daily)——呢啲嘅成交量係衍生品交易活動,唔係主題資金流訊號,混入會污染盲點表同擁擠表。
- 流動性門檻:60 日平均日成交金額 ≥ **$5M** 先算「夠 turnover」。呢個門檻對齊 themes.yaml 現有 ai-power-grid UTES/GRID 衛星倉位先例(~$11-15M/日已夠用戶用 $10-15k 倉位)——低於呢個量級,單一交易已經郁到價,倉位天生受限,同 thesis 本身好唔好無關。敏感度:若門檻收緊到 $10M,C 表(死場)會多幾隻邊緣名;若放寬到 $2M,A 表(盲點)可能多幾隻細價主題 ETF,但雜訊(bid-ask 闊、追蹤誤差大)同步上升。
- 盲點門檻:成交 ≥ **$20M**/日 **且** 唔喺 `universe.yaml`(現時只有 ['QQQ', 'SPMO', 'SPY'])**亦**唔係 `themes.yaml` 任何 theme 嘅 `thesis_etf`(現有 12 隻:['CHPX', 'DRAM', 'FOTO', 'GRID', 'MAGS', 'NASA', 'QQQ', 'REMX', 'SMH', 'URA', 'UTES', 'XLE'])。
- 新上市定義:成立 ≤ **24 個月**。上市日優先用 yfinance `.info.fundInceptionDate`,拎唔到就退而求其次用價量歷史第一個交易日做 proxy(保守;真上市日可能更早,唔會令「新」被高估)。
- 失敗誠實列出(yfinance 落唔到數據),唔靜靜跳過:(全部成功,147 隻全部落到數)
- **重要caveat(人手覆核時發現,寫入呢度免得誤導)**:`backtest/spine/universe.yaml` 嘅
  `known_set` 判斷只查咗 `tickers:` 清單 + `themes.yaml` 嘅 `thesis_etf`——但 universe.yaml
  仲有一層 `sectors:` 區塊,MEMORY/PHOTONICS/ADV_PACKAGING/TPU_SILICON/SEMICAP 五個 sector
  嘅 `parent_proxy` 已經寫死 `[SOXX, SMH]` 做溫度計算基準。即係話下面表 A 出現嘅 **SOXX**
  其實已經喺系統入面用緊(做溫度 proxy,唔係做可交易 tradeable 候選)——唔算「完全冇睇過」,
  只係冇喺 `tickers:`/`thesis_etf` 呢兩層度、腳本嘅機械 known_set 定義揸唔到呢層。表 A 保留
  SOXX 但下面判詞會講返呢個 nuance,唔當佢係真盲點。

## A. 盲點表 -- 成交夠大但唔喺 universe/thesis_etf 入面

門檻:60d 平均日成交 ≥ $20M,且唔喺已知集合(['CHPX', 'DRAM', 'FOTO', 'GRID', 'MAGS', 'NASA', 'QQQ', 'REMX', 'SMH', 'SPMO', 'SPY', 'URA', 'UTES', 'XLE'])。

| Ticker | 類別 | 60d 均量$ | 252d 均量$ | 激增比 | 63d 報酬 | 距52週高 | AUM | 上市 |
|---|---|---|---|---|---|---|---|---|
| IWM | broad | $7.53B | $9.33B | 0.81x | +9.4% | -2.0% | $82.97B | 314mo |
| VOO | broad | $5.49B | $5.51B | 1.00x | +7.0% | -1.4% | $1670.88B | 308mo |
| SOXX | thematic_semi | $5.32B | $2.86B | 1.86x | +31.2% | -19.5% | $47.82B | 300mo |
| DIA | broad | $2.35B | $2.74B | 0.86x | +8.1% | -1.2% | $44.06B | 342mo |
| XLK | sector | $2.23B | $2.36B | 0.95x | +17.7% | -10.7% | $123.91B | 331mo |
| RSP | broad | $2.04B | $2.84B | 0.72x | +7.3% | -0.3% | $93.66B | 279mo |
| EEM | international | $1.89B | $1.83B | 1.03x | +2.9% | -10.1% | $30.32B | 279mo |
| GDX | thematic_metals | $1.88B | $2.05B | 0.91x | -26.9% | -38.3% | $22.75B | 242mo |
| XLF | sector | $1.87B | $2.21B | 0.85x | +8.4% | -0.0% | $51.35B | 331mo |
| XLV | sector | $1.60B | $1.86B | 0.86x | +9.3% | -1.8% | $40.60B | 331mo |
| EFA | international | $1.41B | $1.69B | 0.83x | +0.3% | -1.9% | $77.22B | 299mo |
| XLI | sector | $1.41B | $1.73B | 0.81x | +4.9% | -3.3% | $33.96B | 331mo |
| XBI | thematic_biotech | $1.25B | $1.14B | 1.10x | +10.8% | -8.0% | $10.73B | 245mo |
| VTI | broad | $1.24B | $1.51B | 0.83x | +7.1% | -1.2% | $2297.94B | 308mo |
| KRE | sector_sub | $1.03B | $1.10B | 0.94x | +12.5% | +0.0% | $4.74B | 241mo |
| XLP | sector | $990.0M | $1.27B | 0.78x | +5.6% | -4.9% | $13.65B | 331mo |
| XLY | sector | $938.7M | $1.24B | 0.76x | -0.9% | -5.9% | $22.59B | 331mo |
| XLU | sector | $912.7M | $1.00B | 0.91x | -1.6% | -5.1% | $23.11B | 331mo |
| KWEB | international | $703.3M | $776.6M | 0.91x | -7.3% | -36.0% | $4.91B | 155mo |
| XLC | sector | $686.9M | $718.0M | 0.96x | -4.2% | -6.3% | $22.26B | 97mo |
| IWF | broad | $644.8M | $848.1M | 0.76x | +3.0% | -6.2% | $128.90B | 314mo |
| GDXJ | thematic_metals | $632.3M | $632.2M | 1.00x | -28.5% | -40.7% | $7.08B | 200mo |
| XOP | thematic_energy | $605.2M | $562.4M | 1.08x | +1.3% | -11.6% | $2.91B | 241mo |
| XLB | sector | $580.7M | $657.5M | 0.88x | -1.3% | -5.5% | $8.17B | 331mo |
| VGT | sector | $569.6M | $430.9M | 1.32x | +16.2% | -9.4% | $169.25B | 268mo |
| EWJ | international | $532.8M | $612.0M | 0.87x | +2.9% | -5.4% | $22.31B | 364mo |
| IWD | broad | $523.8M | $687.3M | 0.76x | +11.2% | +0.0% | $79.74B | 314mo |
| VWO | international | $503.0M | $546.1M | 0.92x | +1.1% | -4.1% | $163.32B | 241mo |
| MTUM | factor | $469.2M | $269.5M | 1.74x | +11.8% | -12.5% | $29.05B | 159mo |
| MDY | broad | $463.8M | $558.4M | 0.83x | +6.0% | -1.8% | $28.05B | 374mo |
| XRT | sector_sub | $439.2M | $445.6M | 0.99x | +7.6% | -0.7% | $381.4M | 241mo |
| QUAL | factor | $380.8M | $366.4M | 1.04x | +7.7% | +0.0% | $45.92B | 156mo |
| COPX | thematic_materials | $315.9M | $262.3M | 1.20x | -13.4% | -22.1% | $7.15B | 195mo |
| VNQ | sector | $313.0M | $332.2M | 0.94x | +5.8% | +0.0% | $71.35B | 271mo |
| INDA | international | $302.5M | $349.3M | 0.87x | -2.6% | -12.0% | $6.87B | 173mo |
| VLUE | factor | $289.8M | $154.8M | 1.87x | +22.6% | -7.4% | $10.58B | 159mo |
| XHB | thematic_housing | $287.0M | $263.9M | 1.09x | +7.2% | -9.2% | $1.63B | 245mo |
| IBB | thematic_biotech | $274.0M | $289.4M | 0.95x | +7.1% | -4.9% | $9.09B | 305mo |
| SOXQ | thematic_semi | $269.4M | $97.2M | 2.77x | +27.8% | -19.3% | $2.77B | 61mo |
| IWB | broad | $266.6M | $416.5M | 0.64x | +6.9% | -1.2% | $48.33B | 314mo |
| XME | thematic_materials | $252.9M | $258.4M | 0.98x | -14.5% | -25.5% | $4.38B | 241mo |
| XLRE | sector | $230.1M | $298.4M | 0.77x | +4.4% | -0.1% | $8.10B | 129mo |
| ITB | thematic_housing | $219.4M | $261.1M | 0.84x | +6.0% | -15.0% | $2.60B | 242mo |
| USMV | factor | $213.8M | $219.6M | 0.97x | +3.1% | -1.5% | $23.01B | 177mo |
| ITA | thematic_defense | $194.5M | $193.0M | 1.01x | -1.7% | -8.2% | $14.44B | 242mo |
| SPLV | factor | $184.3M | $228.8M | 0.81x | +3.7% | -1.0% | $7.06B | 182mo |
| OIH | thematic_energy | $158.9M | $157.6M | 1.01x | -6.6% | -17.0% | $1.99B | 175mo |
| AIQ | thematic_ai | $158.5M | $104.7M | 1.51x | +12.1% | -15.8% | $10.41B | 98mo |
| SIL | thematic_metals | $138.0M | $214.5M | 0.64x | -26.6% | -39.3% | $4.21B | 195mo |
| SPHQ | factor | $138.0M | $123.6M | 1.12x | +7.3% | -5.4% | $20.36B | 247mo |
| CIBR | thematic_cyber | $135.4M | $93.9M | 1.44x | +42.0% | -3.3% | $13.84B | 132mo |
| KBE | sector_sub | $133.9M | $120.1M | 1.11x | +12.3% | +0.0% | $1.48B | 248mo |
| SILJ | thematic_metals | $131.5M | $206.2M | 0.64x | -25.5% | -41.0% | $3.40B | 164mo |
| ICLN | thematic_clean | $126.2M | $83.0M | 1.52x | -6.2% | -22.9% | $2.91B | 217mo |
| LABU | thematic_biotech | $121.1M | $107.9M | 1.12x | +24.2% | -22.9% | $677.8M | 134mo |
| SHLD | thematic_defense | $120.1M | $106.3M | 1.13x | -19.9% | -23.4% | $6.85B | 34mo |
| VDE | sector | $116.1M | $106.4M | 1.09x | +1.6% | -9.0% | $11.08B | 261mo |
| ARKG | thematic_biotech | $116.0M | $91.1M | 1.27x | +32.0% | -9.3% | $1.73B | 140mo |
| QTUM | thematic_quantum | $112.6M | $66.7M | 1.69x | +15.6% | -15.5% | $6.26B | 94mo |
| PAVE | thematic_infra | $109.1M | $72.7M | 1.50x | +4.7% | -5.7% | $14.57B | 112mo |
| TAN | thematic_clean | $90.6M | $61.0M | 1.49x | -2.4% | -27.0% | $1.72B | 219mo |
| UNG | thematic_energy | $90.1M | $158.8M | 0.57x | -1.6% | -38.4% | $418.9M | 231mo |
| XSD | thematic_semi | $81.9M | $31.5M | 2.60x | +28.0% | -22.5% | $3.48B | 245mo |
| UFO | thematic_space | $75.5M | $28.8M | 2.62x | -16.6% | -35.8% | $850.6M | 87mo |
| VFH | sector | $74.0M | $81.0M | 0.91x | +8.3% | +0.0% | $13.81B | 269mo |
| CQQQ | international | $73.8M | $70.0M | 1.05x | +8.3% | -12.4% | $3.42B | 199mo |
| VHT | sector | $72.6M | $70.0M | 1.04x | +9.8% | -2.2% | $20.39B | 269mo |
| FTXL | thematic_semi | $70.8M | $33.0M | 2.14x | +26.4% | -23.2% | $2.75B | 118mo |
| PSI | thematic_semi | $70.7M | $24.7M | 2.86x | +26.7% | -23.1% | $3.10B | 253mo |
| NLR | thematic_power | $63.2M | $78.9M | 0.80x | -28.1% | -36.6% | $4.21B | 227mo |
| IRBO | thematic_ai | $62.1M | $33.8M | 1.84x | +41.8% | -10.2% | $788.1M | 97mo |
| XAR | thematic_defense | $61.2M | $56.0M | 1.09x | -6.1% | -11.7% | $6.47B | 178mo |
| VOX | sector | $52.7M | $44.0M | 1.20x | -2.3% | -4.3% | $5.93B | 256mo |
| PICK | thematic_materials | $48.0M | $33.3M | 1.44x | -9.5% | -17.8% | $2.20B | 173mo |
| SKYY | thematic_misc | $47.7M | $33.9M | 1.41x | +19.8% | -12.2% | $2.72B | 180mo |
| ARKX | thematic_space | $45.5M | $24.9M | 1.83x | -6.5% | -18.7% | $933.6M | 64mo |
| VPU | sector | $42.7M | $42.8M | 1.00x | -1.7% | -4.8% | $10.76B | 267mo |
| PPA | thematic_defense | $40.8M | $38.2M | 1.07x | -4.6% | -9.3% | $8.32B | 249mo |
| URNM | thematic_power | $39.5M | $47.5M | 0.83x | -29.5% | -42.1% | $1.90B | 79mo |
| WGMI | thematic_crypto | $39.4M | $31.3M | 1.26x | +2.0% | -33.1% | $343.6M | 53mo |
| BOTZ | thematic_ai | $38.9M | $30.9M | 1.26x | -3.5% | -14.9% | $3.52B | 118mo |
| BUG | thematic_cyber | $38.4M | $22.1M | 1.74x | +62.2% | -3.2% | $1.20B | 81mo |
| DBA | commodity | $38.4M | $19.9M | 1.93x | +1.6% | -3.9% | $1.15B | 234mo |
| VDC | sector | $37.1M | $34.5M | 1.08x | +3.9% | -5.1% | $9.19B | 269mo |
| LIT | thematic_ev | $36.8M | $27.2M | 1.36x | -13.6% | -24.9% | $1.77B | 192mo |
| DBC | commodity | $35.1M | $23.4M | 1.50x | -1.5% | -10.2% | $1.58B | 245mo |
| PBW | thematic_clean | $34.8M | $29.8M | 1.17x | -4.9% | -29.3% | $484.9M | 256mo |
| WCLD | thematic_misc | $32.1M | $22.4M | 1.43x | +30.9% | -5.6% | $245.2M | 82mo |
| VIS | sector | $29.6M | $25.5M | 1.16x | +4.0% | -4.0% | $9.03B | 242mo |
| FCG | thematic_energy | $25.7M | $23.7M | 1.08x | -5.0% | -15.9% | $589.7M | 230mo |
| PPH | thematic_biotech | $25.4M | $40.3M | 0.63x | +6.2% | -1.7% | $879.5M | 175mo |
| ARKQ | thematic_ai | $25.3M | $28.5M | 0.89x | -6.6% | -18.0% | $2.21B | 141mo |
| VCR | sector | $24.1M | $19.0M | 1.27x | +1.8% | -3.7% | $6.83B | 252mo |
| IFRA | thematic_infra | $23.7M | $16.6M | 1.43x | +4.4% | -3.7% | $4.62B | 99mo |
| MOO | commodity | $23.4M | $17.3M | 1.35x | -2.0% | -4.8% | $943.9M | 226mo |
| BLOK | thematic_crypto | $20.1M | $22.9M | 0.88x | +2.1% | -19.3% | $1.16B | 102mo |
| ROBO | thematic_ai | $20.0M | $12.2M | 1.65x | +3.8% | -12.2% | $2.05B | 153mo |

## B. 擁擠訊號表 -- 17 個 theme 對口主題 ETF 嘅「新上市/成交激增」讀數

D = themes.yaml 已登記 thesis_etf;C = 本掃描找到嘅同類候選(未登記,僅供參考,唔自動加入 thesis)。中招定義:激增比 > 1.5x **或** 上市 ≤ 24 個月。

| Theme | ETF | D/C | 60d 均量$ | 激增比 | 上市 | AUM | 中招? |
|---|---|---|---|---|---|---|---|
| memory-supercycle | DRAM | D | $2.86B | 1.18x | 3mo | $25.91B | **是** |
| photonics-optical | FOTO | D | $25.0M | 1.00x | 2mo | $167.0M | **是** |
| ai-power-grid | URA | D | $185.2M | 0.80x | 188mo | $6.00B | 否 |
| ai-power-grid | GRID | D | $146.3M | 1.69x | 200mo | $12.08B | **是** |
| ai-power-grid | UTES | D | $14.1M | 0.80x | 130mo | $1.40B | 否 |
| ai-power-grid | NLR | C | $63.2M | 0.80x | 227mo | $4.21B | 否 |
| ai-power-grid | URNM | C | $39.5M | 0.83x | 79mo | $1.90B | 否 |
| ai-power-grid | URNJ | C | $8.2M | 0.74x | 41mo | $326.9M | 否 |
| ai-power-grid | NUKZ | C | $8.3M | 0.78x | 30mo | $837.0M | 否 |
| ai-power-grid | IDU | C | $18.8M | 0.96x | 313mo | $1.39B | 否 |
| ai-power-grid | FUTY | C | $19.5M | 1.23x | 153mo | $2.35B | 否 |
| advanced-packaging | XSD | C | $81.9M | 2.60x | 245mo | $3.48B | **是** |
| advanced-packaging | SOXX | C | $5.32B | 1.86x | 300mo | $47.82B | **是** |
| advanced-packaging | PSI | C | $70.7M | 2.86x | 253mo | $3.10B | **是** |
| space-satellite | NASA | D | $225.5M | 1.19x | 4mo | N/A | **是** |
| space-satellite | ARKX | C | $45.5M | 1.83x | 64mo | $933.6M | **是** |
| space-satellite | UFO | C | $75.5M | 2.62x | 87mo | $850.6M | **是** |
| rare-earth-materials | REMX | D | $96.7M | 1.02x | 189mo | $2.69B | 否 |
| rare-earth-materials | XME | C | $252.9M | 0.98x | 241mo | $4.38B | 否 |
| rare-earth-materials | PICK | C | $48.0M | 1.44x | 173mo | $2.20B | 否 |
| tpu-custom-silicon | CHPX | D | $11.4M | 2.93x | 9mo | $265.2M | **是** |
| tpu-custom-silicon | SMH | C | $6.34B | 1.71x | 175mo | $77.20B | **是** |
| tpu-custom-silicon | SOXX | C | $5.32B | 1.86x | 300mo | $47.82B | **是** |
| tpu-custom-silicon | XSD | C | $81.9M | 2.60x | 245mo | $3.48B | **是** |
| oil-gas-energy | XLE | D | $2.04B | 1.00x | 331mo | $35.72B | 否 |
| oil-gas-energy | XOP | C | $605.2M | 1.08x | 241mo | $2.91B | 否 |
| oil-gas-energy | OIH | C | $158.9M | 1.01x | 175mo | $1.99B | 否 |
| oil-gas-energy | FCG | C | $25.7M | 1.08x | 230mo | $589.7M | 否 |
| semicap-equipment | SMH | C | $6.34B | 1.71x | 175mo | $77.20B | **是** |
| semicap-equipment | SOXX | C | $5.32B | 1.86x | 300mo | $47.82B | **是** |
| semicap-equipment | XSD | C | $81.9M | 2.60x | 245mo | $3.48B | **是** |
| semicap-equipment | PSI | C | $70.7M | 2.86x | 253mo | $3.10B | **是** |
| aerospace-specialty-alloys | ITA | C | $194.5M | 1.01x | 242mo | $14.44B | 否 |
| aerospace-specialty-alloys | PPA | C | $40.8M | 1.07x | 249mo | $8.32B | 否 |
| aerospace-specialty-alloys | XAR | C | $61.2M | 1.09x | 178mo | $6.47B | 否 |
| aerospace-specialty-alloys | PICK | C | $48.0M | 1.44x | 173mo | $2.20B | 否 |
| euv-lithography-monopoly | SMH | C | $6.34B | 1.71x | 175mo | $77.20B | **是** |
| euv-lithography-monopoly | SOXX | C | $5.32B | 1.86x | 300mo | $47.82B | **是** |
| euv-lithography-monopoly | XSD | C | $81.9M | 2.60x | 245mo | $3.48B | **是** |
| us-solar-manufacturing | TAN | C | $90.6M | 1.49x | 219mo | $1.72B | 否 |
| us-solar-manufacturing | ICLN | C | $126.2M | 1.52x | 217mo | $2.91B | **是** |
| us-solar-manufacturing | QCLN | C | $15.1M | 2.16x | 233mo | $836.7M | **是** |
| gas-compression-equipment | FCG | C | $25.7M | 1.08x | 230mo | $589.7M | 否 |
| gas-compression-equipment | XOP | C | $605.2M | 1.08x | 241mo | $2.91B | 否 |
| gas-compression-equipment | OIH | C | $158.9M | 1.01x | 175mo | $1.99B | 否 |
| specialty-siding-pricing-power | ITB | C | $219.4M | 0.84x | 242mo | $2.60B | 否 |
| specialty-siding-pricing-power | XHB | C | $287.0M | 1.09x | 245mo | $1.63B | 否 |
| glp1-biologics-packaging | XBI | C | $1.25B | 1.10x | 245mo | $10.73B | 否 |
| glp1-biologics-packaging | IHE | C | $16.7M | 1.94x | 242mo | $1.14B | **是** |
| glp1-biologics-packaging | PPH | C | $25.4M | 0.63x | 175mo | $879.5M | 否 |
| glp1-biologics-packaging | XPH | C | $4.8M | 1.20x | 241mo | $428.4M | 否 |
| glp1-biologics-packaging | IBB | C | $274.0M | 0.95x | 305mo | $9.09B | 否 |
| mag7-hyperscaler | MAGS | D | $274.9M | 1.23x | 39mo | $3.60B | 否 |
| mag7-hyperscaler | QQQ | D | $30.45B | 0.92x | 328mo | $490.10B | 否 |
| semiconductor-cycle | SMH | D | $6.34B | 1.71x | 175mo | $77.20B | **是** |
| semiconductor-cycle | QQQ | D | $30.45B | 0.92x | 328mo | $490.10B | 否 |

> ### ⚠️ 把關註記(gatekeeper,2026-07-17):「激增」兩個字要拆開讀先用得
> 成交金額係**冇方向**嘅——佢量「活動」,唔量「流入」。本表嘅 60d/252d 激增比,好大部分
> 發生喺半導體/太空板塊**暴跌週**(SOXX 激增 1.86x 同時距高位 -19.5%;UFO 2.62x / -35.8%)——
> 呢啲成交入面幾多係恐慌沽貨、幾多係新錢接貨,呢個指標分唔到。DESIGN §1 嘅擁擠軸想量
> 「錢湧緊入嚟」;跌市放量方向上隨時係**退**擁擠(投降)。所以:
> - **新上市訊號(DRAM 3個月/$25.9B AUM、NASA 4個月、FOTO 2個月、CHPX 9個月)先係乾淨嘅
>   擁擠讀數**——發行商肯開新主題 ETF = 零售需求已經成型,呢個先係 §1 原意,而且 DRAM
>   嗰個規模(3個月做到 $25.9B)係教科書級晚期訊號,同 memory-supercycle red-team 嘅
>   LTA 中彈互相印證。
> - **激增比要配埋價格方向先用得**:升市放量 = 累積(擁擠↑);跌市放量 = 派發/投降(擁擠↓
>   或至少唔係↑)。若擁擠軸將來接呢個輸入,規格應該係「激增 × 價格趨勢同向」先計分,
>   唔係 raw 激增比。表 B 嘅「中招」欄照保留(誠實反映機械規則輸出),但**唔好未經呢個
>   修正就攞去改任何 theme 嘅 crowding 讀數**。

**中招 theme 清單(擁擠軸若接入呢個輸入,讀數會變嘅——見上方把關註記,新上市訊號先係乾淨嗰批):**

- **memory-supercycle**: DRAM(新上市)
- **photonics-optical**: FOTO(新上市)
- **ai-power-grid**: GRID(激增)
- **advanced-packaging**: XSD(激增), SOXX(激增), PSI(激增)
- **space-satellite**: NASA(新上市), ARKX(激增), UFO(激增)
- **tpu-custom-silicon**: CHPX(新上市+激增), SMH(激增), SOXX(激增), XSD(激增)
- **semicap-equipment**: SMH(激增), SOXX(激增), XSD(激增), PSI(激增)
- **euv-lithography-monopoly**: SMH(激增), SOXX(激增), XSD(激增)
- **us-solar-manufacturing**: ICLN(激增), QCLN(激增)
- **glp1-biologics-packaging**: IHE(激增)
- **semiconductor-cycle**: SMH(激增)

## C. 死場表 -- 主題 ETF 有概念冇資金(60d 均量$ < 門檻)

| Ticker | 對應 Theme | D/C | 60d 均量$ | AUM | 上市 |
|---|---|---|---|---|---|
| XPH | glp1-biologics-packaging | C | $4.8M | $428.4M | 241mo |

## 判詞

### (i) 我哋真係漏咗啲乜

表 A 機械排序(純以 60d 成交金額由大到細)頭 5 位全部係大盤/寬基指數 ETF——呢啲本身就係
「人盡皆知」嘅基準工具,唔係用戶問嘅「主題型漏網」。老實列出(唔跳過)之後,逐隻判斷值唔值得跟進:

- **IWM**($7.53B/日,iShares Russell 2000 小型股大盤):純廣度指數,唔係主題型,唔對應任何
  現有 theme。**唔值得跟進**——已經有 SPY/QQQ 做核心 gate,加小型股廣度純屬另一條 beta 軸,
  同 17 個 theme 嘅 thesis 邏輯無關。
- **VOO**($5.49B/日,Vanguard S&P 500):同 SPY 幾乎同一件嘢(追蹤同一指數),AUM 仲大過 SPY
  好多但只係基金份額分流,唔係新資訊。**唔值得跟進**——已有 SPY 做 tier-1 核心。
- **SOXX**($5.32B/日,iShares 半導體):**真正值得覆核嘅一隻**——見上方 caveat,佢已經係
  universe.yaml `sectors:` 區塊 5 個 semi 相關 sector(MEMORY/PHOTONICS/ADV_PACKAGING/
  TPU_SILICON/SEMICAP)嘅 `parent_proxy` 溫度計算基準,只係未被列為任何 theme 嘅正式
  `thesis_etf`。值得跟進方向:諮詢用戶 SOXX 應唔應該喺 semicap-equipment/euv-lithography-
  monopoly(現時「未搵到窄 ETF」)度正式升格做 thesis_etf,而唔係淨係做溫度計算嘅背景角色。
- **DIA**($2.35B/日,道瓊工業):傳統寬基指數,權重股集中喺舊經濟藍籌,同 AI-capex/主題型
  邏輯脫節。**唔值得跟進**。
- **XLK**($2.23B/日,科技 Sector SPDR):同 QQQ/SMH 高度重疊(Mag7+半導體佔大頭),已經有
  mag7-hyperscaler(MAGS/QQQ)+ semiconductor-cycle(SMH/QQQ)兩個 core-monitor theme 覆蓋
  呢條軸。**邊際值得跟進但優先級低**——XLK 係 QQQ 嘅超集(含金融股豁免嘅純科技版),可以做
  QQQ 兩因子分解(MAGS+SMH 解釋 94%)嘅交叉驗證,但唔係新資訊。

**真正主題型嘅發現(排除大盤/純 sector SPDR 之後,由表 A 揀出嘅 5 隻)**:

- **XBI**($1.25B/日,生技,thematic_biotech):同表 B glp1-biologics-packaging 嘅 C 候選
  完全重疊(見下表,XBI 已經被腳本獨立列做嗰個 theme 嘅候選 ETF)——兩條分析路徑撞埋同一隻名,
  加強咗「XBI 值得正式評估做 glp1-biologics-packaging thesis_etf」呢個判斷嘅可信度。**值得跟進**。
- **GDX**($1.88B/日,金礦股 VanEck):成交大、AUM $22.75B,但同現有 17 個 theme 全部無關
  (金礦股邏輯 = 金價+開採成本,唔喺 ai-capex/供應鏈瓶頸框架入面)。**唔算漏——係真.正交**,
  除非用戶想開一條獨立嘅「貴金屬/通脹對沖」thesis,否則呢隻淨係做觀察,唔跟進。
- **QTUM**($112.6M/日,量子運算,thematic_quantum):17 個 theme 入面**冇任何一個**對應到
  量子運算——呢個先係最切合用戶原話「完全冇睇過」嘅個案(唔似 XBI/SOXX 咁其實有鄰近 theme 接住)。
  **值得跟進**——建議下季 discovery radar 覆核吓量子運算供應鏈(IonQ/Rigetti 呢啲名)值唔值得
  升做第 18 個 theme,而唔係淨係睇 ETF。
- **KWEB**($703.3M/日,中國互聯網,international):同 themes.yaml 2026-07-11 「中國依賴」
  caveat 直接相關——但 KWEB 本身係 China-domiciled 實體嘅籃(阿里/騰訊等),屬於 caveat 講嘅
  「本身係中國實體」類別,**唔值得跟進做 thesis**(用戶已定調呢類要提高懷疑門檻,加上國際名
  本來就出咗 Karst 兩層輸出範圍——tier options/long-only 都係美股框架)。
- **XOP**($605.2M/日,油氣勘探生產,thematic_energy):同表 B oil-gas-energy/gas-compression-
  equipment 兩個 theme 嘅 C 候選重疊(見下表)——同 XBI 一樣,雙路徑撞埋同一隻名,值得評估
  會唔會比現有 XLE 更純(XLE 含中下游、XOP 純上游 E&P,同 oil-gas-energy thesis 嘅「上游供給
  紀律」敘事可能更貼)。**值得跟進**。

### (ii) 擁擠軸點讀

見上表 B 中招清單。表 C 死場方向相反——有主題概念但資金未跟,係「太早」而非「太擠」嘅訊號,兩者唔應該用同一把尺判斷 timing。

### (iii) 定期跑頻率建議

建議**季度**跑一次(同 discovery radar 40 候選覆核節奏對齊):ETF 上市/資金流係
低頻結構性事件(對比 daily VIX/RS 呢啲高頻訊號),月度跑太密、年度跑太疏(24 個月
嘅「新」窗口可能漏一整個上市潮)。
