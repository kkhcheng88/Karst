---
id: KARST-161
title: 人手鏈位表 v2 純度版(用戶裁決 D-147 ③「同一層必須共享同一敘事,加多少家不設上限」):拆開 staples/web3_crypto/china 三條不同位置的 v0 鏈;對全部 52 條鏈逐家做敘事純度覆核,不共享該鏈敘事的成員出隊或另立新鏈;名冊門檻收緊為「同鏈位且同敘事」;交用戶審後作 v2 正本
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: chain-purity-161
deliverable: KARST-D02
---

## 工作內容

背景:KARST-159 交付 v1(52 鏈/309 行/298 家,experiments/2026-09-02-chain-layers/chain_membership_v1.csv + chain_stories_v1.md),用戶審表裁決(D-147 ③,原話「Yes, I dont care how much you add, but the purity of the layer is the highest priority. The company in the same layer should share the same narrative」)。先讀 CONTEXT.md 的「價值鏈」「鏈層」「鏈位名冊 vs 投注代表」三行、chain_stories_v1.md 全文(特別是「我要用戶特別看的三件事」)、.kira/decisions.md D-146 與 D-147、舊倉 ADR-0039 §三之二與 §4.8(路徑見 chain-layers/README.md)。做法:①**拆三條**:staples 拆為品牌製造商(提價方)與大型零售商(壓價方)兩條;web3_crypto 拆為交易所/持幣國庫/礦工(礦工已有 crypto_mining 鏈,合併去該鏈或保留一條,寫明理由);china 按實際上下游位置拆(電商平台、電動車、教育等),同一則消息打不到同一方向的不放同一條;拆出來的鏈各自補到 ≥5 家,美股結構性不足者寫明。②**全表純度覆核**:52 條鏈逐家問一句「這家公司的股價,主要跟這條鏈的敘事走,還是跟它自己的故事走?」——後者出隊(記入 removed_v2.csv 連理由),或另立更純的新鏈;舊倉 ADR-0039 的「代表性測試」(「一間得一兩個礦嘅初級礦商,佢電話會講嘅係佢嗰個礦,唔係銅市」)回歸為名冊門檻的一部分,D-146 ③ 放寬撤回。多元業務公司(一家公司橫跨兩條鏈)只入其股價主要跟隨的那條,並在 note 註明。③**加成員不設上限**:純度過關的可加;每家照 v1 欄位(valid_from/role/position/story/source_url/evidence_10k/added_by=v2),年報佐證從 C:\projects\Karst\data\sec\10k_text 快取讀,缺才抓 EDGAR 並寫入快取連 manifest(每秒 ≤10,User-Agent `Casy Limited kaho.career@gmail.com`),抓前先查 manifest.jsonl 不重抓。④**v1 原行不改**:v2 另出 chain_membership_v2.csv(UTF-8 BOM)與 chain_stories_v2.md;v1 檔一字不動;每條鏈在 v2 加一欄 purity_note(一句:這條鏈的共同敘事是什麼、哪家最邊緣)。⑤誠實聲明照 v1 三項再加一項:純度判斷是人手判斷,沒有統計量度背書。⑥在票上 raise 請用戶審表(docs 鍵指向 chain_stories_v2.md),不等審批即收工。

## 驗收條件

- [ ] chain_membership_v2.csv:staples/web3_crypto/china 三條已拆,新鏈各 ≥5 家或寫明結構性不足;全部鏈逐家有 purity 判斷;出隊名單 removed_v2.csv 每行附一句理由;v1 檔一字不改
- [ ] chain_stories_v2.md:每鏈共同敘事一句、位置、成員表、purity_note、來源;首段誠實聲明四項(事後眼光、來源品質、valid_from 近似比例、純度為人手判斷)
- [ ] 年報全文只入 data/sec/10k_text 快取(D-134),抓前查 manifest;票內不存副本
- [ ] 票上 raise 請用戶審表(docs 指向 chain_stories_v2.md);commit 用 git commit --only -F <訊息檔> -- <自己的檔>;生產庫(倉根 C:\projects\Karst\karst.sqlite)只讀,SHA256 首 16 位維持 b168e9f45b578cf9

## 結果

**誠實聲明(四項)**:①這張表是事後編的,量到的解析度一定偏高——v2 比 v1 更受影響,本次的拆鏈用了 2025 年才明朗的資訊(例如礦商轉型 AI 託管)。②來源品質未經核數:`source_url` 與 `evidence_10k` 可逐家覆核,但「這家公司屬於這條鏈」這個判斷本身沒有外部來源背書。③`valid_from` 近似 210/347 行(60.5%),撐不起需要準確入位日的測試。④**純度判斷是人手判斷,沒有任何統計量度背書**——本票是編表票,不出成績、不寫「及格」;另外每行都有一句 purity 判斷,但當中大部分是該鏈的共同判斷句,只有需要另外交代的成員才有自己那一句。

**交付物**:`experiments/2026-09-02-chain-layers/` 下的 `chain_stories_v2.md`(交審正本)、`chain_membership_v2.csv`(UTF-8 BOM,新增 `purity` / `purity_note` / `src_theme_v1` 三欄)、`removed_v2.csv`(23 行出隊,每行一句理由加規則編號)、`roster_v2.py` / `build_v2.py` / `gen_doc_v2.py`,README 加 v2 一節。commit `41797e1`。

**做法**:用戶那一句落地成四條出隊規則(a 位置不同、b 定價機制不同、c 單一資產主導、d 主業已轉向),逐家問「股價主要跟這條鏈的共同敘事走,還是跟它自己的故事走」。規則 c 就是舊倉 ADR-0039 的代表性測試,按 D-147 ③ 收回作名冊門檻(D-146 ③ 的放寬立場已撤回)。

**數**:52 鏈 → **65 鏈**(拆散 9 條、22 個新鏈名);309 行 → **347 行**(新增 61、出隊 23);298 家 → **343 家**;名冊 <5 家的鏈 4 → **16**;年報佐證 **306/347(88.2%)**,本票新抓 25 份(`fetchedBy: chain-purity-161`,抓前查 manifest,失敗 0);`valid_from` 近似 50.8% → 60.5%。

**拆鏈**:票面指定三條——`staples`→`staples_brand`/`staples_retail`;`web3_crypto`→`crypto_exchange`/`crypto_treasury`,礦工**合併**去 `crypto_mining`(理由:再開一條純礦鏈只會把樣本切細);`china`→`china_ecommerce`/`china_online_content`/`china_education`,`BIDU` 出隊。純度覆核另發現六條要拆:`uranium_power`(礦/濃縮/公用事業)、`streaming`(內容/廣告平台)、`fintech`(信貸/收單)、`ev`(美國/中國)、`casino_resorts`(美國本土/澳門)、`ag_fertilizer`(鉀磷/氮)。另由 `crypto_mining` 拆出 `ai_hpc_hosting`(四家自 2024 年起股價跟 AI 託管租約走),由 `auto_retail` 拆出 `auto_aftermarket`;新開 `aero_aftermarket` 補 `airlines` 的上游缺口。

**兩個代價,要用戶裁**:①`copper` 由八家縮到三家(HBM/ERO/TGB 中規則 c、BHP/RIO 中規則 d),這條鏈從此量不出顯著的層內同步度;②`ag_fertilizer` 拆完之後鉀磷四家、氮肥三家,兩邊都不足五家。**純度與可量度性在這兩條上直接相撞,本票按 D-147 ③ 一律讓純度贏,但這是可以推翻的選擇。**另外 `banks`(GS/MS)與 `datacenter_power`(PWR)兩處判了「留」不「拆」,理由與標示已寫在表上。

**生產庫核對**:`karst.sqlite` SHA256 首 16 位 = `b168e9f45b578cf9`,與票面一致,全程只讀。v0/v1 檔一字未改(`build_v2.py` 逐行對帳:v1 的 309 行不是被承接就是在出隊名單,否則報錯退出)。

**未做**:事前可得那一關仍未答;純度沒有統計驗證;`CONTEXT.md`「鏈位名冊 vs 投注代表」一行的門檻已由 D-147 ③ 收窄為「同鏈位且同敘事」,但該檔在本票執行期間被另一隊改動中,為免撞車未動,交主 agent 補。

## 留言
