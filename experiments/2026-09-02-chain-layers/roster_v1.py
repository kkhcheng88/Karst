# -*- coding: utf-8 -*-
"""KARST-159 人手鏈位表 v1 骨幹定義。

規則(票面 + D-129):
- v0 原行一字不改,由 chain_membership_v0.csv 原樣讀入,只補新欄。
- 同鏈位 = 同上下游位置 + 同故事;不同位置分開成兩條鏈,不塞入同一條。
- 純 ETF 不入;美國上市 ADR 可入。
- story / position 兩欄的措詞盡量引用舊倉 ADR-0039 §三之二「賣什麼 · 賣給誰 ·
  售價由什麼決定 · 實體樽頸」四格,以及 chain_audit_proposal.md 的出隊理由。

每條鏈的欄位:
  position : 上下游位置(一句)
  story    : 該鏈一句故事(同一則行業消息會同方向衝擊這群公司)
  src      : 這條鏈的定性依據出處
  kw       : 從年報快取抽佐證片段時用的關鍵詞(依序試)
  add      : v1 新增成員 [(ticker, valid_from, basis, role, note)]
             valid_from 為 None 表示交由建表腳本按機械規則決定
  short    : 若補不到五家,寫明結構性原因(None = 無短缺)
  new      : True 表示整條鏈是 v1 新開
"""

EXACT = {
    # 有據可查的入位日(上市日 / 分拆完成日 / 合併完成日)
    "GEV":  ("2024-04-02", "精確(GE Vernova 由 GE 分拆完成上市日)"),
    "EXE":  ("2024-10-01", "精確(Chesapeake 與 Southwestern 合併完成、易名 Expand Energy)"),
    "CART": ("2023-09-19", "精確(Instacart 母公司 Maplebear 上市日)"),
    "NXT":  ("2023-02-09", "精確(Nextracker 由 Flex 分拆上市日)"),
    "ALAB": ("2024-03-20", "精確(Astera Labs 上市日)"),
    "CRDO": ("2022-01-27", "精確(Credo Technology 上市日)"),
    "VIK":  ("2024-05-01", "精確(Viking Holdings 上市日)"),
    "SGHC": ("2022-01-27", "精確(Super Group 併殼上市完成日)"),
    "CORZ": ("2022-01-20", "精確(Core Scientific 併殼上市完成日)"),
}

CHAINS = {}


def C(theme, position, story, src, kw, add, short=None, new=False):
    CHAINS[theme] = dict(position=position, story=story, src=src, kw=kw,
                         add=add, short=short, new=new)


# ─────────────────────────── v0 三十三條鏈(骨幹不動,補員) ───────────────────────────

C("semis",
  "上游:AI 加速器與資料中心互連矽片的設計商,直接賣給超大規模雲廠",
  "AI 算力荒——訂單由雲廠的資本開支決定,實體樽頸是先進封裝(CoWoS)與高頻寬記憶體產能,以年計才補得回。",
  "ADR-0039 §三之二 A「AI 晶片:AI 加速器 → 超大規模雲廠商;售價由先進封裝、HBM、晶圓產能決定」",
  ["accelerator", "data center", "hyperscale", "artificial intelligence"],
  [("MRVL", None, None, "core", "客製化 AI ASIC 與資料中心互連矽片,與 AVGO 同一種生意"),
   ("ALAB", None, None, "core", "PCIe/CXL 連接矽片,直接入 AI 機架,客戶同為雲廠"),
   ("CRDO", None, None, "core", "SerDes 與有源電纜矽片,同一批雲廠客戶、同一條資本開支開關")],
  short="⚠️ ADR-0039 §4.8 判過「冇第三間夠純嘅美股 AI 晶片設計商」。v1 放寬到「同客戶 + 同資本開支開關」"
        "才補到 MRVL/ALAB/CRDO 三家;它們賣的是互連而非運算矽片,純度低於 NVDA/AMD,量度時應另立對照。")

C("biotech",
  "下游:已商業化的大型生物製藥原廠,專利藥經處方賣給病人與保險",
  "審批稀缺性即定價權——同一則 FDA、專利懸崖或保險核價消息,對這批有在售產品的原廠方向一致。",
  "ADR-0039 §三之二 C「biotech:專利藥 → 病人;各藥廠賣不同適應症,不是單一條供需方程式」(純需求型,不落注)",
  ["FDA", "clinical", "patent"],
  [("INCY", None, None, "core", "Jakafi 等在售產品的商業化生物科技原廠,與 v0 五家同位置"),
   ("ALNY", None, None, "core", "RNAi 平台,已有多隻在售藥物,同屬商業化原廠")])

C("uranium_power",
  "上游:核燃料(鈾礦開採,以及 LEU 的鈾濃縮一節)",
  "鈾精礦賣給核電廠,售價由礦供給(長期減產、庫存見底)對反應堆需求決定;開一個新礦要七至十年,而買家是剛需——貴極都要買,停爐蝕得更多。",
  "ADR-0039 §三之二 A「鈾燃料」四格原文",
  ["uranium", "yellowcake", "U3O8", "enrich"],
  [("UUUU", None, None, "core", "美國本土鈾礦與加工廠(White Mesa),同為鈾精礦賣家"),
   ("URG", None, None, "core", "懷俄明州原地浸出鈾礦商,已在生產"),
   ("EU",  None, None, "core", "德州原地浸出鈾礦商,2023 年入生產"),
   ("DNN", None, None, "core", "加拿大 Athabasca 鈾礦商,40-F 申報人,無 10-K 快取")],
  short="⚠️ v0 把礦商(CCJ)與濃縮商(LEU)放同一條;兩者嚴格說是鏈上兩個位置,v1 未動 v0 原行,"
        "只在 position 欄分開標示,建議 v2 拆成「鈾礦開採」與「鈾濃縮」兩條。")

C("copper",
  "上游:銅礦開採(銅精礦與陰極銅)",
  "賣給電氣化與工業製造商,售價由全球礦供給(品位下跌、罷工、新礦投產)決定;開一個新礦要十年以上。",
  "ADR-0039 §三之二 A「銅礦」四格原文",
  ["copper", "concentrate", "cathode"],
  [("HBM", None, None, "core", "秘魯 Constancia + 加拿大礦區的中型銅礦商,40-F 申報人"),
   ("ERO", None, None, "core", "巴西純銅礦商,40-F 申報人"),
   ("TGB", None, None, "core", "加拿大 Gibraltar 銅礦商(2026 年易名 Trekor Metals),40-F 申報人")],
  short="⚠️ ADR-0039 §4.8 明言 HBM/ERO/TGB「有數據但過唔到代表性測試——一間得一兩個礦嘅初級礦商,"
        "佢電話會講嘅係佢嗰個礦,唔係銅市」。代表性測試是選投注代表用的,不是鏈位歸屬用的;"
        "本表按「同位置同故事」收錄,但把這一條差異寫明,量度時可另設「只計龍頭」對照。")

C("china",
  "橫向:在美國上市的中國互聯網平台(共通點是政策開關,不是上下游位置)",
  "盈利開關是中國監管政策(反壟斷、數據安全、ADR 退市風險),結構性落在供需卷之外——同一則政策消息把整批打上打落。",
  "ADR-0039 §三之二 D「china 永久剔除:BABA 賣電商、BIDU 賣搜尋、NTES 賣遊戲,產品完全唔同,"
  "唯一共通點就係政策風險——呢個先係佢哋組成一籃嘅原因」",
  ["People's Republic of China", "PRC", "variable interest entity"],
  [("PDD", None, None, "core", "拼多多/Temu,同一組政策與退市風險,20-F 申報人"),
   ("TME", None, None, "core", "騰訊音樂,20-F 申報人"),
   ("BILI", None, None, "core", "嗶哩嗶哩,20-F 申報人")],
  short="⚠️ 這條鏈按 D-129 的定義其實不合格——成員不是同一個上下游位置,只是同一個政策風險源。"
        "v0 已把它永久剔出投注池。保留在表內只作對照(它是「非位置型分組」的反例)。")

C("energy",
  "全鏈:一體化石油巨頭(上游開採 + 煉化 + 零售同一屋簷)",
  "一體化把上游與下游兩種售價機制溝在一起——原油升價時上游賺、煉化蝕,對沖掉自己,所以讀不出單一缺口。",
  "ADR-0039 §5.1 + §三之二 D「energy 已退役:一體化把上游 E&P 同下游煉化零售兩種售價機制溝埋一齊」",
  ["integrated", "upstream", "downstream", "refining"],
  [("SHEL", None, None, "core", "殼牌,20-F 申報人,同為一體化巨頭"),
   ("BP",   None, None, "core", "BP,20-F 申報人"),
   ("TTE",  None, None, "core", "道達爾能源,20-F 申報人")],
  short="v0 已於 2026-07-22 整條退役;v1 補員只為補齊鏈位名冊,不代表復活。")

C("upstream_oil",
  "上游:純油氣開採(E&P),不持煉廠",
  "原油與天然氣賣給煉廠,售價由 OPEC+ 產能與頁岩投資紀律決定;樽頸是鑽探投資週期與有限的優質井位。",
  "ADR-0039 §三之二 A「上游油氣」四格原文",
  ["proved reserves", "drilling", "acreage", "crude oil"],
  [("FANG", None, None, "core", "二疊紀盆地純上游,與 EOG/OXY 同位置"),
   ("DVN",  None, None, "core", "多盆地純上游"),
   ("APA",  None, None, "core", "純上游,美國 + 埃及 + 北海")])

C("defense",
  "上游/中游:純國防主承包商,裝備系統賣給美國及盟國政府",
  "售價由國防預算撥款加生產鏈產能決定;樽頸是固體火箭發動機、船台與專用產線——加不了單靠加班。",
  "ADR-0039 §三之二 A「國防」四格原文",
  ["Department of Defense", "defense", "government contracts"],
  [("LDOS", None, None, "core", "純政府客戶的國防/情報 IT 與任務系統"),
   ("BWXT", None, None, "core", "海軍核動力部件與核燃料,獨市產線"),
   ("KTOS", None, None, "core", "無人機與導彈標靶,純國防客戶")])

C("software_cloud",
  "下游:企業訂閱制軟件與雲平台,賣給企業 IT 預算",
  "零邊際成本,加座位即刻加得到,沒有實體樽頸;售價由企業 IT 支出週期決定,不由供給缺口決定。",
  "ADR-0039 §三之二 C「software_cloud:訂閱制軟件 → 企業;零邊際成本,加座位即刻加得到」",
  ["subscription", "cloud", "enterprise"],
  [("WDAY", None, None, "core", "企業 HR/財務 SaaS,同一條企業 IT 預算開關"),
   ("SNOW", None, None, "core", "雲端資料倉庫,用量計費的企業 IT 支出")])

C("banks",
  "中游:美國大型銀行(存貸與交易服務)",
  "售價由聯儲利率與信貸週期決定,不是實體樽頸;同一則利率或信貸消息把整批打同一個方向。",
  "ADR-0039 §三之二 C「banks:借貸、交易服務 → 客戶;售價由聯儲利率同信貸週期」",
  ["Federal Reserve", "FDIC", "net interest income"],
  [("C",   None, None, "core", "四大貨幣中心銀行之一,補齊 JPM/BAC/WFC/C 一組"),
   ("USB", None, None, "core", "大型區域銀行"),
   ("PNC", None, None, "core", "大型區域銀行")])

C("staples",
  "⚠️ 兩個位置溝在一條:品牌快消製造商(定價者)+ 大型零售商(壓價者)",
  "PG/KO 靠品牌提價,WMT/COST 靠規模壓供應商價——同一則成本上升消息,一邊是成本、一邊是議價籌碼,方向相反。",
  "ADR-0039 §三之二 C「staples ⚠️ 籃子本身溝雜:PG/KO 係品牌制定者,WMT/COST 係零售壓價者,兩種定價型態溝埋一籃」",
  ["brands", "retail", "consumer"],
  [("PEP", None, None, "core", "品牌快消製造(飲料+零食),與 PG/KO 同位置"),
   ("CL",  None, None, "core", "品牌快消製造(家居個護)"),
   ("KMB", None, None, "core", "品牌快消製造(紙品個護)"),
   ("TGT", None, None, "core", "大型零售商,與 WMT/COST 同位置"),
   ("KR",  None, None, "core", "大型食品零售商")],
  short="⚠️ 建議 v2 拆成 staples_brand(PG KO PEP CL KMB)與 staples_retail(WMT COST TGT KR)兩條;"
        "v1 不動 v0 原行,只把兩個位置在 position 欄分開標示。")

C("gold",
  "上游:黃金礦開採(不含權利金公司)",
  "黃金賣給央行、投資者與珠寶,售價就是全球金價;新礦十年以上、礦供給年增長不足 2%——但礦商是價格接受者,缺口讀不到。",
  "ADR-0039 §三之二 A「金礦」四格原文,含「⚠️ 但礦商係價格接受者——缺口讀唔到(工具邊界,唔係讀錯)」",
  ["gold", "ounces", "mineral reserves"],
  [("KGC", None, None, "core", "美洲/西非金礦商,40-F 申報人"),
   ("AU",  None, None, "core", "AngloGold Ashanti,20-F 申報人"),
   ("GFI", None, None, "core", "Gold Fields,20-F 申報人")],
  short="RGLD/WPM 一類權利金公司刻意不入——它們不開礦、不負擔成本通脹,是鏈上另一個位置。")

C("memory",
  "上游:記憶體晶片製造(DRAM / NAND)",
  "賣給電子產品與資料中心廠商,售價由現貨與合約市場供需決定;新廠三年再加關鍵設備交期。",
  "ADR-0039 §三之二 A「記憶體製造」四格原文",
  ["DRAM", "NAND", "flash memory"],
  [],
  short="結構性補不到,不是找漏(ADR-0039 §4.8 原文):「三星、海力士唔喺美股。希捷賣硬碟唔係記憶體晶片"
        "(錯市場)」。現役 2 家(MU、SNDK),名冊 4 行(含 WDC 兩行已剔除)。"
        "STX 刻意不補——舊倉 chain_audit_proposal 判它「純近線 HDD 硬碟寡頭,由 HDD 市場定價,唔係 DRAM/NAND 晶片」。")

C("optical_cpo",
  "中游:資料中心光收發模組與光子元件,賣給網絡設備與系統商",
  "售價由磷化銦/砷化鎵雷射晶片產能決定;樽頸是化合物半導體晶圓廠,補不了快。",
  "ADR-0039 §三之二 A「光元件」四格原文",
  ["optical", "transceiver", "laser", "photonic"],
  [("FN", None, None, "core", "光模組代工龍頭,與 LITE/COHR 同一段光鏈")],
  short="現役只得 3 家(LITE、COHR、FN)。v0 已把 CIEN(系統商=下游客戶)、GLW(光通訊只佔一小瓣)、"
        "AAOI(市值佔 1% 卻主導籃子回報,主席明令剔走)三家剔出;美股純光元件商本來就只剩這三間。名冊 6 行。")

C("power_producers",
  "中游:競爭性(非規管)批發發電商,電力賣給電網與資料中心長約大用戶",
  "售價由區域電力市場供需決定;樽頸是併網排隊與新機組建設週期——AI 資料中心用電是需求端最直接的那個開關。",
  "ADR-0039 §三之二 A「獨立發電商」四格原文",
  ["wholesale power", "merchant", "ERCOT", "PJM"],
  [],
  short="現役 3 家(VST、CEG、TLN),名冊 5 行。結構性:美股 merchant 發電商本來就只有四間,"
        "第四間 NRG 已被 v0 以純度(零售電力業務)剔除;規管公用事業(ETR/DUK/SO/PEG)盈利來自 rate-base 回報、"
        "不隨市價,按 v0 同一把尺不得補入。⚠️ 舊倉 chain_audit_proposal.md 曾判 NRG「主歸屬正是 power_producers"
        "(佢喺嗰邊係強證人)」,與 ADR-0039 的剔除相左;v1 依較後的 ADR-0039,但把分歧記在這裡待用戶裁。")

C("web3_crypto",
  "⚠️ 三個位置溝在一條:交易所(COIN/HOOD)+ 國庫持幣(MSTR)+ 礦工(MARA/RIOT/HUT)",
  "收入等於幣價——不是不想投,是讀電話會這套方法答不到這類題。",
  "ADR-0039 §三之二 D「web3_crypto 永久剔除:收入 = 幣價」",
  ["bitcoin", "digital asset", "cryptocurrency"],
  [],
  short="不補員。礦工那一節已另開新鏈 crypto_mining(v1),它才是真正的同位置同故事群。")

C("glp1",
  "下游:GLP-1 減重藥原廠(有在售產品,有真實產能與定價權)",
  "GLP-1 藥物經處方賣給病人,售價由專利期內產能對臨床需求決定;無菌注射產線要動土兼審批,補不了快。",
  "ADR-0039 §三之二 A「減肥藥」四格原文",
  ["GLP-1", "obesity", "tirzepatide", "semaglutide", "weight loss"],
  [],
  short="結構性補不到(ADR-0039 §4.8 原文):「回測窗內冇第三間有實質 GLP-1 產品收入嘅上市藥廠。"
        "雙寡頭本身就係缺口」。現役 2 家,名冊 5 行。臨床期挑戰者(VKTX、GPCR、ALT)是另一個位置——"
        "無產品收入、靠試驗數據——美股只湊到三家,未達五家門檻,故本次不另開鏈。")

C("solar",
  "中游:住宅與商用太陽能逆變器、功率優化器,賣給安裝商",
  "售價由組件供需加裝機需求決定;⚠️ 這是十六條可投鏈裡樽頸最弱的一條——逆變器產能加得起。",
  "ADR-0039 §三之二 A「太陽能」四格原文",
  ["inverter", "solar", "module"],
  [],
  short="結構性補不到(ADR-0039 §4.8 原文):「Shoals / Array 賣俾公用規模開發商,唔同客 = 唔同層;"
        "組件廠(CSIQ/JKS)賣嘅嘢就唔同」。現役 2 家,名冊 4 行。公用事業級那一節已另開新鏈 solar_utility(v1)。")

C("cannabis",
  "下游:美國州級大麻 MSO(種植到零售一體)",
  "收入由美國各州零售供需決定,聯邦層面仍屬違法——這一條就是它上不了主要交易所的原因。",
  "ADR-0039 §三之二 D「cannabis 已退役:剔走加拿大 LP 後(唔同國家嘅供需方程式)剩返一隻美國 MSO,砌唔到籃子」",
  ["cannabis", "marijuana", "dispensary"],
  [],
  short="補不到,而且是結構性:美國聯邦法令下 MSO 全部在場外(OTC)交易,不符票面「美國上市公司」;"
        "加拿大 LP(TLRY/CGC/ACB/CRON)是另一個國家的供需方程式,按 v0 同一把尺不得補入。名冊 1 行。")

C("metaverse_innov",
  "下游:消費級 3D / UGC 平台與遊戲引擎",
  "估值重估押注,不是供需缺口;PLTR/SHOP/ROKU 按實際業務搬走之後,剩下兩隻根本不同步。",
  "ADR-0039 §三之二 D「metaverse_innov 已退役:剩返兩隻根本唔同步(讀分相關 −0.16、營收相關 −0.25)= 殘留主題」",
  ["metaverse", "virtual", "creators"],
  [],
  short="不補員。舊倉已量到這兩隻讀分相關 −0.16、營收相關 −0.25,即「同層對同一消息反應相似」這一條實測不成立;"
        "補人只會製造一條假層。名冊 2 行。")

C("quantum",
  "上游:量子運算硬件商(未商業化)",
  "沒有產品出貨、沒有售價可讀,估值全靠敘事——同一則政府撥款或大廠里程碑消息把整批一齊推上推落。",
  "ADR-0039 §三之二 C「quantum:量子運算 → 未商業化;冇產品出貨、冇售價可讀,估值靠敘事」",
  ["quantum computing", "qubit", "quantum"],
  [("INFQ", None, None, "core", "中性原子量子運算商,2026 年上市,美股第五家純量子硬件")])

C("streaming",
  "⚠️ 兩個位置溝在一條:內容自有的串流商(NFLX/DIS/WBD/PARA)+ 分發平台(ROKU/SPOT)",
  "訂閱制媒體賣給消費者,售價自訂,沒有實體樽頸。",
  "ADR-0039 §三之二 C「streaming:訂閱制媒體 → 消費者;售價自訂」",
  ["streaming", "subscribers", "content"],
  [],
  short="已達六家,不補員。⚠️ ROKU 由 metaverse_innov 搬入時舊倉已註明它是「CTV 串流廣告分發層」,"
        "與內容自有商是不同位置,建議 v2 拆開。")

C("betting",
  "下游:純線上體育博彩與 iGaming 營運商(抽成)",
  "抽成由自己定,售價自訂,沒有實體樽頸;真正的開關是「州份牌照開放 × 下注需求」。",
  "ADR-0039 §三之二 C「betting:線上博彩抽成 → 玩家;售價自訂」",
  ["sports betting", "iGaming", "online gaming"],
  [("RSI",  None, None, "core", "純線上體育博彩與賭場,美加拉美市場"),
   ("SGHC", None, None, "core", "Betway/Spin 母企,純線上博彩,20-F 申報人")],
  short="現役 4 家(DKNG、FLUT、RSI、SGHC),名冊 5 行。實體賭場度假村(LVS/WYNN/MGM/CZR/PENN)"
        "已按 v0 的去向另開新鏈 casino_resorts(v1)。")

C("ev",
  "中游:純電動車製造商",
  "供需方程式本身沒問題(電池/晶片缺貨期真的有缺口),但過完純度與方向測試只剩特斯拉一間——一間公司不是一條鏈。",
  "ADR-0039 §三之二 B「電動車 ❌ 唔成立:過完三關淨返特斯拉一間;RIVN/LCID 缺貨期都轉嫁唔到成本、"
  "靠主權基金注資 → 售價由咩供需決定答唔到」",
  ["electric vehicle", "battery", "vehicles"],
  [],
  short="不補員。名冊 5 行,現役 0 家——v0 判整層不成立。這一條保留在表內是為了記錄「層不成立」也是一個結論。")

C("cyber",
  "下游:企業訂閱制網絡安全平台",
  "訂閱制安全賣給企業,零邊際成本;有講價權,但講價權不等於缺口。",
  "ADR-0039 §三之二 C「cyber:訂閱制網絡安全 → 企業;有講價權,但講價權唔等於缺口」",
  ["cybersecurity", "threat", "endpoint", "security platform"],
  [("S", None, None, "core", "端點與雲工作負載安全平台,與 CRWD 同位置")],
  short="⚠️ CyberArk 已於 2025 年被 PANW 收購除牌,原擬補入的第二家落空;現役 6 家,已過門檻。")

C("travel_cruise",
  "下游:郵輪營運商(床位運力)",
  "航次賣給旅客,售價由船隊床位運力對需求決定;新船三至四年,而且船廠船台有限。",
  "ADR-0039 §三之二 A「郵輪」四格原文",
  ["cruise", "ships", "berths", "guests"],
  [("VIK",  None, None, "core", "河輪與海洋郵輪營運商,20-F 申報人"),
   ("LIND", None, None, "core", "探險郵輪營運商,同一條運力方程式")])

C("homebuilders",
  "下游:量產型持地建商(自有土地庫存)",
  "新屋賣給買家,售價由土地、可建地塊、勞工與按揭利率決定;樽頸是已開發地塊與建築工人。",
  "ADR-0039 §三之二 A「建商」四格原文",
  ["homebuilding", "lots", "homebuyers", "land development"],
  [("KBH",  None, None, "core", "量產型建商,與 DHI/LEN/PHM 同一種持地模式"),
   ("MHO",  None, None, "core", "中西部/東南部量產型建商"),
   ("LGIH", None, None, "core", "入門級量產型建商")],
  short="TOL(豪宅訂製)與 NVR(輕土地模式)已被 v0 以純度剔除,v1 不重入——它們的定價機制與持地量產商不同。")

C("ag_fertilizer",
  "上游:化肥生產(鉀肥、磷肥、氮肥)",
  "賣給農民與農業經銷商;鉀磷看礦山供給,氮看天然氣邊際成本;鉀礦七年,氨廠四至五年。",
  "ADR-0039 §三之二 A「化肥生產」四格原文",
  ["fertilizer", "potash", "nitrogen", "ammonia"],
  [("IPI", None, None, "core", "美國本土鉀肥生產商"),
   ("UAN", None, None, "core", "氮肥(UAN/氨)生產商,天然氣成本傳導最直接"),
   ("ICL", None, None, "core", "鉀肥與特種肥料,20-F 申報人"),
   ("LXU", None, None, "core", "氮肥與工業化學品生產商")],
  short="ADR-0039 §4.8 當時補不到 ICL/LXU 的理由是「喺市值檔完全冇 2021-12-01 數據,唔准用今日市值頂替」——"
        "那是選投注代表要按市值排序才需要的數據,鏈位歸屬不需要,所以 v1 補得入。NTR(零售分部佔 EBITDA 31%)"
        "仍按 v0 排除。")

C("fintech",
  "⚠️ 三個位置溝在一條:另類信貸(SOFI/AFRM/UPST)+ 支付(PYPL/XYZ)+ 零售券商(HOOD)",
  "售價(息率/手續費/抽成)自己定,沒有實體樽頸。",
  "ADR-0039 §三之二 C「fintech:借貸、支付平台 → 消費者商戶;售價(息率/手續費)自己定」",
  ["consumer lending", "payments", "merchants"],
  [("XYZ", None, None, "core", "Block(Square/Cash App),支付與商戶服務")],
  short="⚠️ LendingClub 已不在 SEC 現役代碼表,原擬補入的第二家落空。建議 v2 按三個位置拆開。")

C("gig",
  "下游:零工經濟叫車與外送平台(抽成)",
  "抽成由自己的算法定,沒有實體樽頸;同一則零工分類法規或油價消息對整批方向一致。",
  "ADR-0039 §三之二 C「gig:網約車、外賣抽成 → 消費者;抽成由自己算法定」",
  ["drivers", "couriers", "gig", "marketplace"],
  [("CART", None, None, "core", "Instacart,同一條零工外送抽成方程式")])

C("oilfield_services",
  "中游:油田服務與設備(鑽井/完井/儲層服務),賣給油氣開採商",
  "售價由鑽井活動量與油價週期決定;樽頸是鑽機隊與壓裂車隊——重資本,報廢了補不回快。",
  "ADR-0039 §三之二 A「油田服務」四格原文",
  ["oilfield", "completion", "wellbore", "drilling services"],
  [("NOV", None, None, "core", "鑽井設備與資本裝備,同一條鑽井活動量開關"),
   ("FTI", None, None, "core", "海底生產系統與完井"),
   ("OII", None, None, "core", "海底工程與 ROV 服務")],
  short="鑽機承包商(RIG/VAL/NE/HP/NBR/PTEN)按日費率收費,是鏈上另一個位置,已另開新鏈 drilling_contractors(v1)。"
        "BKR 仍按 v0 以純度(工業與能源技術分部佔近半)排除。")

C("semi_equipment",
  "上游:晶圓製造設備(WFE),賣給晶圓廠",
  "售價由設備交期與技術壁壘決定;樽頸是光學與精密零件,交期以年計。⚠️ 它坐在資本開支這一邊 = 可斬需求,脆。",
  "ADR-0039 §三之二 A「半導體設備」四格原文,含「⚠️ 資本開支邊 = 可斬需求,脆」",
  ["wafer", "deposition", "etch", "metrology", "semiconductor equipment"],
  [("ONTO", None, None, "core", "製程控制與量測設備,同賣晶圓廠"),
   ("ACLS", None, None, "core", "離子植入設備"),
   ("TER",  None, None, "core", "半導體測試設備")],
  short="ASML 按 v0 原註排除(荷蘭上市);v1 未推翻此註。")

C("smr_newbuild",
  "上游:小型模組化核反應堆開發商(未入生產)",
  "兩間都未有商用反應堆交付發電,「售價由什麼供需決定」目前答不到——同一則能源部撥款或雲廠供電合約消息把整批推同一個方向。",
  "ADR-0039 §5.2 + §三之二 E,主席 2026-07-27 原話:「to keep the experiment simple I will drop this for now. "
  "Surely later we may add this if we have round 2 and it must in production」",
  ["small modular reactor", "nuclear reactor", "fission", "reactor"],
  [("NNE",  None, None, "core", "微型模組化反應堆開發商,同為未入生產"),
   ("LTBR", None, None, "core", "核燃料技術開發商,同一組政策與撥款開關"),
   ("ASPI", None, None, "core", "同位素與 HALEU 燃料開發商")],
  short="全部成員仍屬 pre-revenue;v0 的重開條件(round 2 且必須入生產)未達成,v1 補員只補名冊。")


# ─────────────────────────── v1 新開鏈 ───────────────────────────

C("crypto_mining",
  "中游:比特幣挖礦與算力託管(自建電力與資料中心,賣算力或賣幣)",
  "收入等於幣價乘算力份額,成本等於電價;同一則減半、幣價或電力合約消息把整批打同一個方向——"
  "近兩年再加一個開關:把礦場改裝成 AI 資料中心的租約。",
  "機器分層 2023-06-30 layer 5「CIFR CLSK MARA RIOT WULF」與語意分層 2023-06-30 layer 1 同一組,"
  "是兩種方法都獨立找到的少數幾條層之一(layers_v2.csv)",
  ["bitcoin mining", "hash rate", "miners", "mining"],
  [("CLSK", None, None, "core", "自建礦場的比特幣礦商"),
   ("CIFR", None, None, "core", "同上,並已簽 AI 資料中心租約"),
   ("WULF", None, None, "core", "核電供電礦場,同樣轉型 AI 託管"),
   ("IREN", None, None, "core", "礦場加 AI 雲,同一條電力與幣價方程式"),
   ("CORZ", None, None, "core", "礦場轉 AI 託管的代表案例"),
   ("HIVE", None, None, "core", "北美/南美礦商,40-F 申報人")],
  new=True)

C("travel_platform",
  "下游:資產輕的線上旅遊訂房與出行平台(抽佣,不持有運力)",
  "抽佣由平台自訂,不持有房間或船位——同一則旅遊需求消息對它們的衝擊與郵輪商不同:郵輪商受運力綁死,平台商不受。",
  "v0 chain_membership 原註:ABNB/BKNG 由 travel_cruise 出隊,「去向=純需求平台」(universe_audit_v2.md §三);"
  "研究第四節 2023 切片層「ABNB BKNG DASH EXPE HLT MAR UBER」層內殘餘相關 0.206",
  ["online travel", "bookings", "reservations", "accommodations"],
  [("BKNG", None, None, "core", "全球最大線上訂房平台"),
   ("EXPE", None, None, "core", "線上旅遊代理"),
   ("ABNB", None, None, "core", "短租平台,同一條抽佣方程式"),
   ("TRIP", None, None, "core", "旅遊評論與元搜尋"),
   ("TCOM", None, None, "core", "攜程,20-F 申報人")],
  new=True)

C("airlines",
  "下游:客運航空公司(座位運力)",
  "座位賣給旅客,售價由運力對需求加燃油成本決定;新飛機交付排隊以年計,而且機場時刻有限——同一則油價或需求消息把整批打同一方向。",
  "機器分層三個切片(2015/2019/2023)全部獨立找到同一組航空公司;語意分層同樣找到(layers_v2.csv)",
  ["airline", "flights", "aircraft", "available seat miles"],
  [("DAL",  None, None, "core", "網絡型全服務航空"),
   ("UAL",  None, None, "core", "網絡型全服務航空"),
   ("AAL",  None, None, "core", "網絡型全服務航空"),
   ("LUV",  None, None, "core", "低成本航空"),
   ("ALK",  None, None, "core", "區域/低成本航空"),
   ("JBLU", None, None, "core", "低成本航空")],
  new=True)

C("railroads",
  "中游:一級鐵路貨運(路網獨佔,重資產)",
  "運力賣給貨主,售價由路網獨佔加燃油附加費決定;補供應要鋪路軌與買機車,以年計——最接近「實體樽頸」的運輸位置。",
  "機器分層 2015-06-30 layer 21「CSX NSC UNP WAB」與 2023-06-30 layer 10「CSX NSC UNP」;"
  "研究第四節 2023 層「CSX JBHT NSC R UNP」0.215",
  ["railroad", "intermodal", "carloads", "rail"],
  [("UNP", None, None, "core", "西部一級鐵路"),
   ("CSX", None, None, "core", "東部一級鐵路"),
   ("NSC", None, None, "core", "東部一級鐵路"),
   ("CP",  None, None, "core", "加拿大太平洋堪薩斯城,40-F 申報人"),
   ("CNI", None, None, "core", "加拿大國家鐵路,40-F 申報人")],
  new=True)

C("casino_resorts",
  "下游:實體賭場與綜合度假村營運商(持牌照與物業)",
  "賭枱與房間賣給到場客人,售價由牌照稀缺加物業供給決定;開一座度假村要動土並拿牌照,以年計——與純線上博彩(零實體樽頸)是兩個位置。",
  "v0 chain_membership 原註:PENN 由 betting 出隊,「去向=實體賭場板塊」;舊倉 chain_audit_proposal.md 判"
  "「LVS 已賣 Vegas,純澳門/新加坡綜合度假村,零美國線上體育博彩」、「WYNN 2023 已退出 WynnBET,純豪華賭場度假村」;"
  "機器分層 2015 layer 0 與 2023 layer 9 兩次找到同一組",
  ["casino", "resort", "gaming", "table games"],
  [("MGM",  None, None, "core", "拉斯維加斯 + 澳門綜合度假村"),
   ("CZR",  None, None, "core", "美國區域賭場 + 拉斯維加斯"),
   ("LVS",  None, None, "core", "澳門 + 新加坡綜合度假村"),
   ("WYNN", None, None, "core", "拉斯維加斯 + 澳門豪華度假村"),
   ("BYD",  None, None, "core", "美國區域賭場"),
   ("PENN", None, None, "core", "美國區域賭場(v0 已由 betting 出隊,此為其去向)")],
  new=True)

C("building_products",
  "中游:住宅建材與裝修產品,賣給建商、承包商與家居賣場",
  "售價由住宅開工與翻新需求決定,再加木材/樹脂等原料成本;產能要建廠,補不了快——它坐在建商的上游,同一則按揭利率消息比建商慢一拍到。",
  "研究第四節 2023 切片層「LPX MHK POOL」層內殘餘相關 0.314、「MAS SHW SWK」0.272;"
  "機器分層 2015 layer 15「MAS MHK POOL」",
  ["remodeling", "residential construction", "home centers", "building products"],
  [("SHW",  None, None, "core", "建築塗料"),
   ("MAS",  None, None, "core", "廚衛與裝修產品"),
   ("MHK",  None, None, "core", "地板"),
   ("POOL", None, None, "core", "泳池設備分銷"),
   ("BLDR", None, None, "core", "建材分銷,直接賣建商"),
   ("LPX",  None, None, "core", "結構板材(OSB)")],
  new=True)

C("refiners",
  "下游:煉油與成品油銷售(crack spread)",
  "買原油、賣汽柴油,賺的是裂解價差——原油升價對它們是成本不是收入,方向與上游 E&P 相反;新煉廠美國三十年沒建過,產能就是樽頸。",
  "ADR-0039 §5.1:v0 的 energy 鏈退役理由正是「一體化把上游 E&P 同下游煉化零售兩種售價機制溝埋一齊」——"
  "上游那半拆了出去做 upstream_oil,下游這半一直沒有承繼者,本鏈補回",
  ["refining", "crack spread", "throughput", "refinery"],
  [("MPC",  None, None, "core", "美國最大煉廠商"),
   ("VLO",  None, None, "core", "純煉油"),
   ("PSX",  None, None, "core", "煉油 + 中游 + 化工"),
   ("DINO", None, None, "core", "中大陸區煉廠"),
   ("PBF",  None, None, "core", "純煉油"),
   ("DK",   None, None, "core", "區域煉廠")],
  new=True)

C("midstream",
  "中游:油氣集輸、處理與管道(收費型)",
  "賣的是通過量不是價——長約收費,對油氣價格的敏感度遠低於上游;樽頸是管道許可與建設週期,新線批不批得到是政策題。",
  "機器分層 2015 layer 33「CNP CNX EQT FANG OKE PARR WMB」與 2019 layer 40「CNP OKE WMB」;"
  "語意分層 2023 layer 11「CNX EP EQT OKE WMB」",
  ["midstream", "gathering", "pipelines", "throughput"],
  [("WMB",  None, None, "core", "天然氣長輸管道"),
   ("OKE",  None, None, "core", "NGL 集輸與處理"),
   ("KMI",  None, None, "core", "天然氣管道"),
   ("TRGP", None, None, "core", "二疊紀集輸處理"),
   ("AM",   None, None, "core", "Appalachia 集輸")],
  new=True)

C("natgas_ep",
  "上游:純天然氣開採(Appalachia / Haynesville)",
  "賣的是亨利港氣價,不是油價——同一則 LNG 出口核准、冬季氣溫或 AI 資料中心用電消息把整批打同一方向,"
  "而這些消息對原油 E&P 不一定同向。",
  "機器分層 2019 layer 38 與 2023 layer 25「CNX EOG EP EQT L NC OKE WMB」;"
  "上游油氣按售價開關拆成油與氣兩個位置,是 D-129「同故事」規則的直接應用",
  ["natural gas", "Henry Hub", "Appalachian", "dry gas"],
  [("EQT",  None, None, "core", "Appalachia 最大氣商"),
   ("RRC",  None, None, "core", "Marcellus 氣商"),
   ("CNX",  None, None, "core", "Appalachia 氣商"),
   ("AR",   None, None, "core", "Appalachia 氣與 NGL"),
   ("EXE",  None, None, "core", "Chesapeake 與 Southwestern 合併後的最大純氣商"),
   ("GPOR", None, None, "core", "Utica / Anadarko 氣商")],
  new=True)

C("managed_care",
  "下游:醫療保險與管理式醫療(承保醫療成本風險)",
  "保費賣給僱主與政府(Medicare Advantage / Medicaid),賺的是保費減賠付——同一則 CMS 費率或使用率消息"
  "把整批打同一方向,而且方向與醫院相反:使用率上升對保險商是成本、對醫院是收入。",
  "機器分層三個切片全部獨立找到同一組(2015 layer 45、2019 layer 24、2023 layer 23);語意分層同樣找到",
  ["Medicare Advantage", "medical loss ratio", "CMS", "health plans"],
  [("UNH", None, None, "core", "最大管理式醫療商"),
   ("ELV", None, None, "core", "藍十字系"),
   ("CNC", None, None, "core", "Medicaid 為主"),
   ("HUM", None, None, "core", "Medicare Advantage 為主"),
   ("MOH", None, None, "core", "Medicaid 為主")],
  new=True)

C("insurance_brokers",
  "中游:保險經紀與風險顧問(收佣金,不承保風險)",
  "佣金跟保費規模走,不承擔賠付——所以硬市場(保費升)對它們是純收入,對承保商是收入加風險;這是兩個位置。",
  "機器分層 2015 layer 36「AJG AON BRO MRSH WTW」與 2019 layer 35,兩個切片獨立找到同一組",
  ["brokerage", "insurance brokerage", "commissions", "risk management"],
  [("AON",  None, None, "core", "全球保險經紀"),
   ("MRSH", None, None, "core", "Marsh McLennan,全球保險經紀"),
   ("AJG",  None, None, "core", "中型市場保險經紀"),
   ("WTW",  None, None, "core", "保險經紀與精算顧問"),
   ("BRO",  None, None, "core", "零售保險經紀")],
  new=True)

C("auto_retail",
  "下游:二手車零售、拍賣與零件回收",
  "賣二手車與車輛零件,售價由二手車價指數與車貸利率決定;供給樽頸是新車產量三年前的缺口——"
  "同一則二手車價或車貸消息把整批打同一方向。",
  "機器分層 2015 layer 19「CPRT KMX LKQ」、2019 layer 15、2023 layer 11「AN CPRT CVNA KMX LKQ」;"
  "研究第四節 2019 層「AN CPRT CVNA GPC KMX LKQ」0.199",
  ["used vehicles", "auction", "salvage", "vehicle sales"],
  [("CVNA", None, None, "core", "線上二手車零售"),
   ("KMX",  None, None, "core", "實體二手車零售"),
   ("AN",   None, None, "core", "新車 + 二手車經銷"),
   ("CPRT", None, None, "core", "事故車拍賣"),
   ("LKQ",  None, None, "core", "回收零件分銷")],
  new=True)

C("datacenter_power",
  "中游:資料中心的電力、配電與散熱設備,賣給雲廠與獨立發電商",
  "AI 資料中心用電是這一輪最硬的實體樽頸——變壓器、開關設備、液冷機組交期已排到兩三年後;"
  "同一則雲廠資本開支消息對這批設備商的衝擊,比對晶片商慢一拍但同向。",
  "D-129 由上而下框架:AI 鏈的買家一端(雲廠)與供電一端是兩個獨立位置,v0 的 semis / power_producers 兩條都沒有覆蓋這一節",
  ["data center", "power distribution", "thermal management", "electrical equipment"],
  [("VRT",  None, None, "core", "資料中心電力與液冷機組"),
   ("ETN",  None, None, "core", "配電與開關設備"),
   ("PWR",  None, None, "core", "電網與資料中心接電工程"),
   ("GEV",  None, None, "core", "燃氣輪機與電網設備"),
   ("HUBB", None, None, "core", "電氣連接與公用事業配電"),
   ("MOD",  None, None, "core", "資料中心散熱")],
  new=True)

C("hyperscalers",
  "下游:超大規模雲廠(AI 鏈的買家一端)",
  "它們是整條 AI 鏈的需求源頭——資本開支指引一改,晶片、光模組、電力設備、資料中心全部跟著動;"
  "但對它們自己來說,資本開支上升是成本不是收入,所以方向與供應商相反。",
  "D-129 由上而下框架:一條產業鏈要串得起來,買家一端必須在表內,否則量到的只是供應商之間的共同因子。"
  "MSFT/ORCL 同時坐 software_cloud,循 v0 AMGN 同時坐 biotech 與 glp1 的雙掛先例",
  ["capital expenditures", "data center", "cloud infrastructure", "artificial intelligence"],
  [("MSFT",  None, None, "core", "Azure(與 software_cloud 雙掛)"),
   ("AMZN",  None, None, "core", "AWS"),
   ("GOOGL", None, None, "core", "Google Cloud"),
   ("META",  None, None, "core", "自用 AI 基建,資本開支規模同級"),
   ("ORCL",  None, None, "core", "OCI(與 software_cloud 雙掛)")],
  new=True)

C("drilling_contractors",
  "中游:鑽機承包商(按日費率出租鑽機與船隊)",
  "賣的是鑽機日費率,不是服務工序——樽頸是鑽機隊本身,新建一台深水鑽井船要三年以上;"
  "與油田服務商(按工序收費)是鏈上兩個不同位置。",
  "機器分層 2015 layer 18「HP NBR NOV SLB」與 2019 layer 17「FTI HAL HP NBR NOV OII SLB」;"
  "研究第四節 2015 層「HP NBR NOV SLB」0.314、2019 層 0.252",
  ["drilling rigs", "dayrate", "offshore drilling", "rig fleet"],
  [("RIG",  None, None, "core", "深水鑽井船"),
   ("VAL",  None, None, "core", "海上鑽井平台"),
   ("NE",   None, None, "core", "海上鑽井平台"),
   ("HP",   None, None, "core", "陸上鑽機"),
   ("NBR",  None, None, "core", "陸上鑽機"),
   ("PTEN", None, None, "core", "陸上鑽機與壓裂")],
  new=True)

C("solar_utility",
  "中游:公用事業級太陽能設備(組件、追蹤器、電氣平衡系統),賣給大型開發商",
  "客戶是公用規模開發商而不是住宅安裝商,售價由關稅壁壘、IRA 製造補貼與合約簿決定——"
  "同一則關稅或補貼消息對它們是收入,對住宅逆變器商幾乎無關。",
  "ADR-0039 §4.8 原文:「Shoals / Array 賣俾公用規模開發商,唔同客 = 唔同層;組件廠(CSIQ/JKS)賣嘅嘢就唔同」;"
  "v0 chain_membership 原註:FSLR 去向=「美國本土太陽能製造」真敘事但未夠三員‧孵化器候補",
  ["utility scale", "modules", "trackers", "investment tax credit"],
  [("FSLR", None, None, "core", "美國本土薄膜組件製造(v0 已由 solar 出隊,此為其去向)"),
   ("NXT",  None, None, "core", "追蹤器"),
   ("ARRY", None, None, "core", "追蹤器"),
   ("SHLS", None, None, "core", "電氣平衡系統"),
   ("CSIQ", None, None, "core", "組件製造,20-F 申報人")],
  new=True)

C("steel",
  "上游:鋼廠(電爐與高爐)",
  "賣熱軋卷板給製造與建築商,售價由廢鋼成本、關稅與產能利用率決定;新電爐要兩至三年——"
  "同一則關稅或基建法案消息把整批打同一方向。",
  "機器分層 2015 layer 14「ATI NUE RS STLD」;研究第四節 2015 層「ATI LEG NUE STLD」0.204",
  ["steel", "scrap", "mills", "hot rolled"],
  [("NUE",  None, None, "core", "最大電爐鋼廠"),
   ("STLD", None, None, "core", "電爐鋼廠"),
   ("CLF",  None, None, "core", "高爐 + 鐵礦石一體化"),
   ("RS",   None, None, "core", "金屬服務中心(加工分銷)"),
   ("CMC",  None, None, "core", "電爐長材鋼廠")],
  new=True)

C("restaurants",
  "下游:連鎖餐飲(以加盟制為主)",
  "賣餐給消費者,加盟商付特許權費——同一則食品成本、最低工資或同店銷售消息把整批打同一方向;"
  "沒有實體樽頸,開店速度就是供給。",
  "機器分層 2015 layer 1「CMG DPZ DRI MCD WEN YUM」、2019 layer 34、語意分層 2019 layer 2 同一組",
  ["restaurants", "franchisees", "same-store sales", "menu"],
  [("MCD", None, None, "core", "全球最大加盟制連鎖"),
   ("YUM", None, None, "core", "加盟制多品牌"),
   ("CMG", None, None, "core", "直營快休閒"),
   ("DPZ", None, None, "core", "加盟制外送"),
   ("WEN", None, None, "core", "加盟制快餐"),
   ("DRI", None, None, "core", "直營休閒餐飲")],
  new=True)

C("discount_retail",
  "下游:折扣與離價零售(off-price / dollar store)",
  "賣的是價格差——同一則消費降級、庫存過剩或關稅消息對它們是順風,對正價零售商是逆風,方向相反;"
  "這正是它們不應與 staples 的 WMT/COST 混為一談的原因。",
  "機器分層 2015 layer 24「DLTR SIG TJX」、2019 layer 22、2023 layer 32;語意分層 2023 layer 10「DG ROST TJX」",
  ["off-price", "merchandise", "assortment", "treasure hunt"],
  [("TJX",  None, None, "core", "離價服飾家居"),
   ("ROST", None, None, "core", "離價服飾"),
   ("DG",   None, None, "core", "小型折扣店"),
   ("DLTR", None, None, "core", "小型折扣店"),
   ("BURL", None, None, "core", "離價服飾")],
  new=True)
