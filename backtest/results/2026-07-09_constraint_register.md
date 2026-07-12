# 供給約束 Register(正式)—— IMA 外資研報掃描,cleaned prompt【2026-07-09】

> 來源:IMA【愛分享】投研「外資研報🥇」資料夾 → DeepSeek v4 Pro,cleaned Prompt ③
> (institutional-only + 優先 5 月後 + 中英雙語 + 完整句)。原檔 `uploads/26d2078e-supply_constraint_scan_20260709.md`。
> **取代第一 pass**(`2026-07-09_constraint_language_report_scan.md`,舊 prompt,含散戶料+2025 舊料)。
> 質量 ~9.5/10:全機構、全 2026-04~07、~120 條完整句逐字引句、30 份報告;memory 組 8 間機構互相印證。
> 已獨立核對(MS sold-out/allocation、Micron $100B SCA、GS DRAM 缺口、變壓器 128 週)一致 → 可信。
> cosmetic 瑕:S 級首條 MS HBM 引句有 OCR 亂碼(唯一一條)。

## 美股可落單映射(Karst = 美股;magnifier 候選)

| 供給緊子行業 | 最強級 | 美股標的/ETF | Karst 主題 |
|---|---|---|---|
| 記憶體 DRAM/NAND/HBM | S | **MU**、WDC(SanDisk) | ✅ memory-supercycle |
| 數據中心實體/電力設備 | S | **VRT、GEV、ETN、PWR、ANET**、EQIX、DLR、HUBB | 🆕 **AI-power(最大新 cluster)** |
| AI 電源/電力半導體·類比 | A | **ON、TXN、ADI、MPWR、NVT** | 🆕 新候選 |
| 先進製程(N3/TSMC) | A | **TSM** | ✅ semicap 鄰接 |
| 先進封裝(CoWoS/ABF) | A/C | **AMKR、TSM** + 設備 | ✅ advanced-packaging |
| 半導體設備 | B | **KLAC、AMAT、LRCX、ASML、COHU** | ✅ semicap-equipment |
| 燃氣輪機/發電 | S | **GEV**(Siemens Energy=OTC SMEGF) | 🆕 AI-power |
| 鈾/核電 | A | **CCJ、UEC、UUUU、URA(ETF)** | 🆕 新候選 |
| 銅 | A | **FCX、SCCO、COPX(ETF)** | 🆕 新候選(金屬) |
| 鋁 | A | **AA** | 🆕 新候選(金屬) |
| 光纖/光學 | A | **GLW、COHR、LITE** | ✅ photonics-optical |
| 汽車半導體 | A | Melexis(MELE.BB)、IFX、NXPI | 🆕 |
| 雲(需求端印證) | S | GOOGL、AMZN、MSFT | — 需求側 |
| 無直接美股(記錄) | — | 玻纖/PCB鑽針/鋰隔膜/諧波減速器/鎢(中港名為主) | — |

**三個最搶眼新 cluster**(magnifier 優先評估):①AI-power/電網 VRT/GEV/ETN/PWR ②鈾 CCJ/URA ③電力半導體 ON/TXN/ADI。

## 強度分佈(子行業)

- **S(sold out/allocation/停簽)**:記憶體、數據中心實體、變壓器、燃氣輪機、雲(Google backlog $460B)
- **A(供不應求/缺口)**:功率半導體、N3/TSMC、汽車芯片、銅、鋁、鎢、鈾、光纖預製棒、銅箔、PCB鑽針、玻纖、ABF、CCL、鋰隔膜
- **B(交期 12M+)**:變壓器(128 週/24-48M)、開關設備(52-65 週)、燃氣輪機(3-5 年)、FPGA(52 週)、高端機床(12M)
- **C(產能吃緊)**:功率半導體、CoWoS、MLCC、諧波減速器、數據中心(throughput 樽頸)
- **D(多輪漲價)**:功率半導體(+10-20%)、記憶體(DRAM/NAND +250%)、CCL(+35-40%)、燃氣輪機(+50%)、變壓器(+77-95%)、N3(+8-10%)
- **E(LTA 鎖量)**:記憶體(Micron 16 SCA/$100B/5yr take-or-pay;SanDisk 5 NBM;ABF 下一個被鎖)

## 5 個跨行業機制(此版更實)

1. AI 供給約束**成條價值鏈**：記憶體→先進製程/封裝→數據中心實體→電力/變壓器/燃氣輪機→上游金屬(銅/鋁/鈾)。
2. **LTA/take-or-pay 係本輪結構變化**:Micron $100B、5 年、預付款+違約金;供應商奪回議價權。
3. **HBM 擠佔**:HBM 食 3-4x wafer + cleanroom 優先 → 傳統 DRAM/NAND 緊 → 成熟制程向 AI 傾 → 功率/類比/汽車緊。
4. **物理瓶頸(非需求)**:變壓器 128 週、燃氣輪機 3-5 年、cleanroom、EPC 勞工、冷卻 2028 起 binding。
5. **強度 ∝ 擴產週期剛性**(變壓器/燃氣輪機/鈾/光棒越長越強)。

## 下一步

- [ ] 新 cluster(AI-power/鈾/電力半導體/金屬)評估入 themes.yaml radar,配美股 ticker + magnifier scorecard。
- [ ] 同 transcript 庫(corpus.py `scan()`)對照:研報 vs 管理層原話,睇一手 transcript 有冇更早訊號。
- [ ] GLM ③b(long-tail)已證失敗(6 條/舊料),此 DeepSeek 版即係 register 主體,GLM 不再倚賴。
- ⚠️ 事件驅動(中東/LNG,GLM 補)另置,唔混入結構候選。
