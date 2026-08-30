"""單一定義庫的 sqlite 表結構。

D-026 第 1 條:因子定義、策略、運行登記、實體代號映射存**單一 sqlite 檔**;
行情、基本面、逐字稿等大批數據存 parquet,本庫只登記其快照編號。

四組表:
1. ``entity`` / ``entity_ticker``  實體編號與代號歷史映射(D-026 第 2 條)
2. ``factor`` / ``factor_version`` 因子定義與版本鏈(D-021 第 2、6、9 條)
3. ``factor_value``                日期 × 實體 → 值,雙時間戳連可執行時點
                                   (D-021 第 1、3、4 條;可執行時點 KARST-064)。
                                   **大批因子值不住這裡**:由 D-032 起改存 Parquet,
                                   本表只餘小批人手登記的值(KARST-068)
   ``factor_value_batch`` / ``factor_value_batch_member``
                                   因子值批次的登記:一個「數據快照 × 因子庫批次」
                                   一個 Parquet 檔,庫內只留落點、內容雜湊、行數,
                                   連檔內載住哪幾個因子版本(D-032;KARST-068)
4. ``data_snapshot``               數據快照登記(D-026 第 3 條)
5. ``strategy`` / ``strategy_version`` / ``strategy_factor_ref`` / ``param_set`` /
   ``param_value``                 策略定義、版本鏈、引用因子與參數集(D-020 第 4 條、KARST-022)
6. ``gateway_write``               寫入者簽章登記:凡經唯一入口寫入的列在此有一筆(KARST-022)
7. ``backtest_run`` / ``run_artifact`` / ``run_factor_ref``
                                   回測運行登記、逐日序列檔案落點、運行蓋齊的因子版本
                                   (D-020 第 7 條、規格 7.4;KARST-026)。運行的來歷
                                   (正式運行／掃描格,連所屬掃描編號)在 backtest_run
                                   的 origin 與 sweep_id 兩格(D-029;KARST-054)
8. ``active_setup``                現役設定的指定登記:一套策略當下跟隨哪一個參數集
                                   (規格 7.5、CONTEXT.md「現役設定」;KARST-030)
9. ``risk_rule`` / ``strategy_risk_ref``
                                   共用風控層三條規則的定義登記與策略引用
                                   (D-013 第 4 條、規格 1.6;KARST-025)
10. ``data_snapshot_fetch``        數據快照的抓取登記:抓取時間、抓的是哪一段窗口,
                                   以及凍結那一刻的齊全度核對結果
                                   (D-026 第 3 條;KARST-034、KARST-067)
11. ``data_snapshot_retraction``   快照除名登記:哪個快照不再算可回測、被誰除名、
                                   幾時、為什麼、被哪個快照取代。只加不改不刪——
                                   除名是加一列,不是刪一列(KARST-084)
12. ``gateway_countersign``        補簽留痕:一列本來沒有簽章(唯一入口收窄之前落庫的),
                                   由誰、幾時、為什麼補上簽章(KARST-087)
13. ``backtest_run_retraction``    運行除名登記:哪一次運行不再算數、被誰除名、幾時、
                                   為什麼。只加不改不刪——除名是加一列,不是刪一列
                                   (KARST-093)
14. ``sweep_batch``                批次登記:一次參數掃描收工寫的那一列——格數、達標格數、
                                   三個中位數成績、判讀目標與門檻、最佳格與代表格、報告
                                   落點與內容雜湊(D-042、CONTEXT.md「批次登記」;
                                   KARST-091 加表時漏了這一行,KARST-094 補上)
15. ``param_set_alignment``        參數集對齊標記:一個參數集是「已對齊」還是「示例」、
                                   對齊日期、對齊依據一句。只加不改不刪——改標記是加一筆
                                   新申報,不是改寫已發生的申報。走旁表而不是參數集多一格,
                                   所以不進運行編號雜湊、不動既有簽章
                                   (D-038、CONTEXT.md「參數集對齊標記」;KARST-094)
16. ``strategy_governance``        策略治理宣告:一條策略屬由上而下三層的哪一層(市況/板塊/
                                   個股),離場治理屬哪一型(延續型注/回歸型注/規則型),連
                                   宣告依據一句。兩格必填,未答即拒收。只加不改不刪——改宣告
                                   是加一筆新的,不是改寫已發生的宣告。走旁表而不是 ``strategy``
                                   多兩欄:``strategy`` 一經落庫即不可改(trigger 擋住),既有
                                   三條登記補填不了,而多兩欄亦會令該表既有簽章一次過作廢
                                   (D-054、D-056、D-058;CONTEXT.md「由上而下三層」「離場治理」;
                                   KARST-116)
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

# 第 2 版加入策略定義、參數集與寫入者簽章三組表(KARST-022);
# 第 3 版加入回測運行登記三組表(KARST-026);
# 第 4 版加入現役設定登記表(KARST-030);
# 第 5 版加入共用風控層的規則定義表與策略引用表(KARST-025);
# 第 6 版加入數據快照的抓取登記附表(KARST-034)。舊庫重開即自動補建;
# 第 7 版把 param_set 的換倉節奏約束改為由引擎那份正本砌出來(KARST-044),
#        舊庫重開時自動重建 param_set(見 ``_migrate_param_set_cadence``);
# 第 8 版在 backtest_run 加「來歷」與「掃描編號」兩格(KARST-054),舊庫重開時
#        自動重建 backtest_run 並回填(見 ``_migrate_backtest_run_origin``);
# 第 9 版在 data_snapshot_fetch 加「齊全度警報條數」與「警報摘要」兩格(KARST-067),
#        舊庫重開時原地補欄、既有登記一列不動(見 ``_migrate_snapshot_fetch_alerts``);
# 第 10 版在 factor_value 加「可執行時點」一格(KARST-064),舊庫重開時原地補欄、
#        既有因子值一列不動(見 ``_migrate_factor_value_executable_time``);
# 第 11 版加因子值批次的兩張登記表,因子值本身搬去 Parquet(D-032、KARST-068)。
#        舊庫重開時**只在**那批值已經有 Parquet 登記、行數逐個因子版本對得上、
#        而且檔案真的在落點上,才把 factor_value 清空重建(見
#        ``_migrate_factor_values_to_files``);既有的因子、因子版本、實體編號
#        一個都不動,所以策略引用與運行蓋住的版本編號照舊指得回。
# 第 12 版加快照除名登記表 ``data_snapshot_retraction``(KARST-084):快照凍出來之後
#        才發現不可用(三數等式對不上一類),由**加一列**令它不再算可回測,不是刪走
#        登記——data_snapshot_fetch 與因子值批次那三道 BEFORE DELETE 閘寫明
#        「登記不可刪,追溯要指得回」。舊庫重開時 DDL 自動補建,既有登記一列不動。
# 第 13 版加補簽留痕表 ``gateway_countersign``(KARST-087):數據快照登記與抓取登記
#        由本版起收入治理清單,而它們在收窄之前已經落庫的那幾列一列簽章都沒有。
#        補簽是**加一列簽章 + 加一列留痕**(誰、幾時、為什麼),不是靜靜替舊列蓋章:
#        沒有這一列留痕,日後就分不出「當日經唯一入口凍的」與「事後補簽的」。
#        舊庫重開時 DDL 自動補建,既有登記一列不動。
# 第 14 版加運行除名登記表 ``backtest_run_retraction``(KARST-093):一次運行落了庫之後
#        才發現不算數(最常見的是自動測試經正式路徑寫進來的那種),由**加一列**令它
#        不再入清單、不再入計數,不是刪走 backtest_run 那一列——運行登記與快照登記
#        同一個道理:刪走就等於把一件發生過的事由帳上抹掉,而那次運行的淨值、交易、
#        參數集版本鏈全部還在,追溯要指得回。這張表入治理清單,故每一列都有唯一入口
#        的簽章:「這次運行不算數」是一個定義級動作,不可以有人繞過那道門靜靜除掉一次
#        運行。舊庫重開時 DDL 自動補建,既有登記一列不動。
# 第 15 版加批次登記表 ``sweep_batch``(KARST-091):一次參數掃描收工經唯一入口寫一列,
#        記住格數、達標格數、隱藏的失敗運行條數、三個中位數成績、判讀目標與門檻、最佳格、
#        代表格、批內最佳單次的運行編號、報告落點與內容雜湊。以前這幾個數只住在 CSV 裡,
#        畫面靠掃實驗目錄反推——那是全站唯一繞過定義庫的地方,而 D-042 明文用「達標運行
#        的中位數年化」排批次名次,即門面左半那四個數當時全部無憑無據。本表入治理清單,
#        每列有唯一入口簽章。掃描編號不入運行編號(KARST-054),所以這是加一列:舊掃描
#        可以事後補登記,既有運行一個位都不動。舊庫重開時 DDL 自動補建,既有登記一列不動。
# 第 16 版加參數集對齊標記表 ``param_set_alignment``(D-038、KARST-094):按參數集編號記
#        「已對齊／示例」、對齊日期、對齊依據一句,追加式不可刪,入治理清單逐列有簽章。
#        D-038 要求「畫面與紀錄須能分辨」示例參數集與現役設定,而 KARST-090 只做到登記時
#        強制申報,結果掛在記憶體裡、庫內查不到。標記走**旁表**而不是參數集多一格:當一格
#        參數值會改動參數集內容、13 條正式運行連同編號一併改號(KARST-026);做成 param_set
#        一條新欄會改動該表的 content_digest、8326 列既有簽章一次過作廢。旁表兩樣都不碰
#        (假設 A-014,2026-08-30 查證成立)。舊庫重開時 DDL 自動補建,既有登記一列不動;
#        新表開頭是空的,補記由唯一入口逐列簽章寫入,不由遷移直接塞。
# 第 17 版加策略治理宣告表 ``strategy_governance``(D-054、D-056、D-058;KARST-116):按策略
#        編號記「屬三層哪一層」「離場治理屬哪一型」連依據一句,追加式不可刪,入治理清單逐列
#        有簽章。D-058 第 1 條要求這兩格必填、未答拒收——這是全倉唯一一個「唔答就跑唔到」的
#        防漂移閘:一條新策略交代不出自己屬哪一層、離場靠什麼,它連登記都登記不了。
#        走**旁表**而不是 ``strategy`` 多兩欄,兩個理由都是硬的:(1) ``strategy`` 有
#        ``trg_strategy_no_update`` 擋住 UPDATE,多兩欄的話生產庫現存三條登記永遠補填不到,
#        而登記按設計不可刪重來;(2) 多兩欄會改動 ``strategy`` 的 content_digest,既有簽章
#        一次過作廢,``karst verify`` 會全紅。旁表兩樣都不碰。
#        舊庫重開時 DDL 自動補建,既有登記一列不動;新表開頭是空的,補填由唯一入口逐列簽章
#        寫入,不由遷移直接塞——「這條策略屬哪一層」是要人判的事,不是遷移猜得出的。
SCHEMA_VERSION = 17

# 換倉節奏清單在 DDL 裡的佔位。**不在此處逐個字寫死節奏**:正本住在
# ``karst.engine.contracts.CADENCES``,建表那一刻才由它砌出 CHECK 的取值表
# (KARST-044)。以前這裡另寫一份日/月/季,於是引擎認得週度、庫身收不到,
# 週度參數集登記不了——同一件事有兩個講法,遲早各走各路。
_CADENCE_SLOT = "__REBALANCE_CADENCES__"

_DDL_TEMPLATE = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 實體:一個不變的內部編號。上市公司以 SEC CIK 為錨,ETF 與籃子另編內部代碼。
CREATE TABLE IF NOT EXISTS entity (
    entity_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_kind  TEXT NOT NULL CHECK (entity_kind IN ('company', 'etf', 'basket')),
    display_name TEXT NOT NULL,
    cik          TEXT UNIQUE,
    local_code   TEXT UNIQUE,
    created_at   TEXT NOT NULL,
    CHECK (
        (entity_kind = 'company' AND cik IS NOT NULL AND local_code IS NULL)
        OR (entity_kind IN ('etf', 'basket') AND local_code IS NOT NULL AND cik IS NULL)
    )
);

-- 代號歷史映射:代號只是有生效起訖的屬性,會被回收再發給別人。
CREATE TABLE IF NOT EXISTS entity_ticker (
    entity_id  INTEGER NOT NULL REFERENCES entity(entity_id),
    ticker     TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to   TEXT,
    PRIMARY KEY (entity_id, ticker, valid_from),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS idx_entity_ticker_lookup
    ON entity_ticker (ticker, valid_from);

-- 因子:具體定義那一級,名稱「族名·具體定義」全庫唯一(單一定義)。
CREATE TABLE IF NOT EXISTS factor (
    factor_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    family     TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 因子版本:每版不可改,parent_version_id 指前版(git 式版本鏈)。
CREATE TABLE IF NOT EXISTS factor_version (
    factor_version_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_id          INTEGER NOT NULL REFERENCES factor(factor_id),
    version_no         INTEGER NOT NULL,
    parent_version_id  INTEGER REFERENCES factor_version(factor_version_id),
    scale_kind         TEXT NOT NULL CHECK (scale_kind IN ('cardinal', 'ordinal', 'boolean')),
    procedure_kind     TEXT NOT NULL CHECK (procedure_kind IN ('formula', 'material')),
    formula            TEXT,
    input_data_version TEXT,
    material           TEXT,
    judge_version      TEXT,
    description        TEXT,
    created_at         TEXT NOT NULL,
    UNIQUE (factor_id, version_no),
    CHECK (
        (procedure_kind = 'formula'
            AND formula IS NOT NULL AND length(trim(formula)) > 0
            AND input_data_version IS NOT NULL AND length(trim(input_data_version)) > 0
            AND material IS NULL AND judge_version IS NULL)
        OR (procedure_kind = 'material'
            AND material IS NOT NULL AND length(trim(material)) > 0
            AND judge_version IS NOT NULL AND length(trim(judge_version)) > 0
            AND formula IS NULL AND input_data_version IS NULL)
    ),
    CHECK ((version_no = 1 AND parent_version_id IS NULL)
        OR (version_no > 1 AND parent_version_id IS NOT NULL))
);

-- 因子值:缺失=沒有這一列,不填 0、不填 NULL。
-- 追溯到批次 = factor_version_id(含產生程序版本) × snapshot_id。
--
-- **大批因子值由 D-032 起不住這裡**:一個值連三個時點入表要近 300 字節,值本身
-- 只需 8 字節;Alpha158 十二隻十二年已經 555 萬列、庫檔 1.6 GB。因子庫級數的值
-- 改為按「數據快照 × 因子庫批次」一批一個 Parquet 檔(見下面兩張登記表)。
-- 本表**留下來**給小批人手登記的值:一次幾百列、要即場查得到、犯不著為它開一個檔
-- (``factor write-values`` 那道命令;讀回來經 ``karst.factorvalues`` 那個取值口,
-- 與因子值批次同一條路)。
-- 分界線是量,不是意思:兩邊的一列都是同一件事——三個時點連一個有限數。

-- 三個時點齊落一列(D-021 第 3 條):事件時點(那根 K 線)、知情時點(該日收工)、
-- 可執行時點(其後下一根可交易 K 線的開市)。可執行時點**可以留空**,而留空
-- 有它自己的意思:這個快照的日曆裡沒有下一根 K 線——值知得到,但成交不到。
-- 把它記成「同一日可成交」就是前視,所以寧可留空而不猜(engine/cadence.py
-- 的排期亦是這樣丟掉最後一個決策日的)。
CREATE TABLE IF NOT EXISTS factor_value (
    factor_version_id INTEGER NOT NULL REFERENCES factor_version(factor_version_id),
    entity_id         INTEGER NOT NULL REFERENCES entity(entity_id),
    event_time        TEXT NOT NULL,
    knowledge_time    TEXT NOT NULL,
    value             REAL NOT NULL,
    snapshot_id       TEXT REFERENCES data_snapshot(snapshot_id),
    executable_time   TEXT CHECK (executable_time IS NULL OR executable_time > knowledge_time),
    PRIMARY KEY (factor_version_id, entity_id, event_time, knowledge_time),
    CHECK (knowledge_time >= event_time)
);

CREATE INDEX IF NOT EXISTS idx_factor_value_asof
    ON factor_value (factor_version_id, entity_id, knowledge_time, event_time);

-- ====================================================================
-- 因子值批次的登記(D-032;KARST-068)
-- ====================================================================

-- 一個因子值批次 = 一個「數據快照 × 因子庫批次」的 Parquet 檔。值住檔案,庫內
-- 只留這一列:落點、內容雜湊、行數、產生程序版本。做法與運行的三條逐日序列
-- (run_artifact)、選股痕跡一字不差——大批數據住檔案、定義庫只登記編號與雜湊
-- (D-026 第 1 條),``karst verify`` 重讀檔案再算一次雜湊,對不上即報。
--
-- 主鍵是「批次名 × 快照」,而**產生程序版本是它的一格內容,不是主鍵的一部分**:
-- 同一個批次名在同一個快照上只可以有一份值。改了算法就是另一批值,要用另一個
-- 批次名——否則同一個名底下會有兩份內容不同的正本,而讀取方無從知道自己讀到
-- 哪一份(單一定義,無第二影像)。
CREATE TABLE IF NOT EXISTS factor_value_batch (
    batch_key         TEXT NOT NULL,
    snapshot_id       TEXT NOT NULL REFERENCES data_snapshot(snapshot_id),
    procedure_version TEXT NOT NULL,
    path              TEXT NOT NULL,
    content_hash      TEXT NOT NULL,
    rows              INTEGER NOT NULL CHECK (rows >= 0),
    written_at        TEXT NOT NULL,
    PRIMARY KEY (batch_key, snapshot_id),
    CHECK (length(trim(batch_key)) > 0),
    CHECK (length(trim(procedure_version)) > 0),
    CHECK (length(trim(path)) > 0 AND length(trim(content_hash)) > 0)
);

-- 一個批次檔載住哪幾個因子版本、各佔幾多列。D-032 要求登記講得出「因子、因子
-- 版本」,靠的就是這一張;讀取介面亦靠它由「因子版本 × 快照」直接指到那一個檔,
-- 不必逐個檔開來看。行數逐個因子版本記,所以缺值比例不用開檔就數得出。
CREATE TABLE IF NOT EXISTS factor_value_batch_member (
    batch_key         TEXT NOT NULL,
    snapshot_id       TEXT NOT NULL,
    factor_version_id INTEGER NOT NULL REFERENCES factor_version(factor_version_id),
    rows              INTEGER NOT NULL CHECK (rows >= 0),
    PRIMARY KEY (batch_key, snapshot_id, factor_version_id),
    FOREIGN KEY (batch_key, snapshot_id)
        REFERENCES factor_value_batch (batch_key, snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_factor_value_batch_member_version
    ON factor_value_batch_member (factor_version_id, snapshot_id);

CREATE TRIGGER IF NOT EXISTS trg_factor_value_batch_no_update
BEFORE UPDATE ON factor_value_batch BEGIN
    SELECT RAISE(ABORT, '因子值批次的落點與雜湊落庫後不可改;改了算法就是另一批值,請用另一個批次名');
END;

CREATE TRIGGER IF NOT EXISTS trg_factor_value_batch_no_delete
BEFORE DELETE ON factor_value_batch BEGIN
    SELECT RAISE(ABORT, '因子值批次的登記不可刪,追溯要指得回');
END;

CREATE TRIGGER IF NOT EXISTS trg_factor_value_batch_member_no_update
BEFORE UPDATE ON factor_value_batch_member BEGIN
    SELECT RAISE(ABORT, '批次載住哪幾個因子版本落庫後不可改');
END;

CREATE TRIGGER IF NOT EXISTS trg_factor_value_batch_member_no_delete
BEFORE DELETE ON factor_value_batch_member BEGIN
    SELECT RAISE(ABORT, '批次載住哪幾個因子版本不可刪,追溯要指得回');
END;

-- 數據快照:編號=日期+內容雜湊;舊快照不動。
CREATE TABLE IF NOT EXISTS data_snapshot (
    snapshot_id  TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    taken_on     TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    path         TEXT,
    universe     TEXT NOT NULL DEFAULT '[]',
    created_at   TEXT NOT NULL,
    UNIQUE (source, taken_on, content_hash)
);

-- 不可改,只可出新版(D-021 第 9 條);值一經入庫即正本,不重判(D-024 第 2 條)。
CREATE TRIGGER IF NOT EXISTS trg_factor_version_no_update
BEFORE UPDATE ON factor_version BEGIN
    SELECT RAISE(ABORT, '因子定義落庫後不可改,只可出新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_factor_version_no_delete
BEFORE DELETE ON factor_version BEGIN
    SELECT RAISE(ABORT, '因子定義落庫後不可刪,版本鏈須完整');
END;

CREATE TRIGGER IF NOT EXISTS trg_factor_value_no_update
BEFORE UPDATE ON factor_value BEGIN
    SELECT RAISE(ABORT, '因子值落庫後不可改,只可以更晚知情時間寫新值');
END;

CREATE TRIGGER IF NOT EXISTS trg_factor_value_no_delete
BEFORE DELETE ON factor_value BEGIN
    SELECT RAISE(ABORT, '因子值落庫後不可刪');
END;

CREATE TRIGGER IF NOT EXISTS trg_snapshot_no_update
BEFORE UPDATE ON data_snapshot BEGIN
    SELECT RAISE(ABORT, '數據快照落庫後不可改,重拉數請出新快照編號');
END;

-- 快照除名登記(KARST-084)。
--
-- 一個快照凍出來之後才發現不可用(例如宇宙表三數等式對不上——兩個代號撞同一個
-- 實體編號,有價格序列被靜靜蓋走),要令它不再被當作可回測的數據。**做法不是刪列**:
-- data_snapshot_fetch、factor_value_batch 三張表各有一道 BEFORE DELETE 閘,寫明
-- 「登記不可刪,追溯要指得回」。刪走就等於把一件發生過的事由帳上抹掉。
--
-- 所以除名是**加一列**,不是減一列:這張表只加不改不刪,一列講清楚哪個快照、
-- 被誰除名、幾時、為什麼、被哪個快照取代。除名之後:
--   · list_snapshots() 與三數等式核對一律略過它——登記冊列得出的只有可回測的;
--   · 直連查詢(get_snapshot、read_manifest 一類)照樣讀得到——追溯指得回;
--   · 快照目錄與 parquet 檔一個字都不動(D-026 第 3 條:舊快照永不改動)。
--
-- 這張表入治理清單(ledger.GOVERNED_TABLES),故此每一列都有唯一入口的寫入者簽章:
-- 「除名」本身是一個定義級動作,不可以有人繞過那道門靜靜除掉一個快照。
CREATE TABLE IF NOT EXISTS data_snapshot_retraction (
    snapshot_id    TEXT PRIMARY KEY REFERENCES data_snapshot(snapshot_id),
    reason         TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    superseded_by  TEXT REFERENCES data_snapshot(snapshot_id),
    retracted_by   TEXT NOT NULL CHECK (length(trim(retracted_by)) > 0),
    retracted_at   TEXT NOT NULL,
    CHECK (superseded_by IS NULL OR superseded_by <> snapshot_id)
);

CREATE TRIGGER IF NOT EXISTS trg_snapshot_retraction_no_update
BEFORE UPDATE ON data_snapshot_retraction BEGIN
    SELECT RAISE(ABORT, '除名登記落庫後不可改;判斷變了請另開票,不要改寫已發生的除名');
END;

CREATE TRIGGER IF NOT EXISTS trg_snapshot_retraction_no_delete
BEFORE DELETE ON data_snapshot_retraction BEGIN
    SELECT RAISE(ABORT, '除名登記不可刪,追溯要指得回');
END;

CREATE TRIGGER IF NOT EXISTS trg_entity_anchor_immutable
BEFORE UPDATE ON entity
WHEN old.cik IS NOT new.cik
     OR old.local_code IS NOT new.local_code
     OR old.entity_kind <> new.entity_kind
BEGIN
    SELECT RAISE(ABORT, '實體的錨(CIK/內部代碼)與種類不可改');
END;

-- ====================================================================
-- 策略定義與參數集(D-020 第 4 條唯一入口、D-002 第 4 條單一定義)
-- ====================================================================

-- 策略:名稱全庫唯一(單一正本、無第二影像);類型限策略總覽八類之一。
CREATE TABLE IF NOT EXISTS strategy (
    strategy_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    strategy_type TEXT NOT NULL CHECK (strategy_type IN (
        'fundamental', 'technical', 'multifactor', 'event',
        'meanrev', 'follow', 'macro', 'options')),
    created_at    TEXT NOT NULL
);

-- 策略版本:與因子同制,一經落庫不可改、只可出新版,每版有父版本(D-021 第 9 條)。
CREATE TABLE IF NOT EXISTS strategy_version (
    strategy_version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id         INTEGER NOT NULL REFERENCES strategy(strategy_id),
    version_no          INTEGER NOT NULL,
    parent_version_id   INTEGER REFERENCES strategy_version(strategy_version_id),
    description         TEXT,
    created_at          TEXT NOT NULL,
    UNIQUE (strategy_id, version_no),
    CHECK ((version_no = 1 AND parent_version_id IS NULL)
        OR (version_no > 1 AND parent_version_id IS NOT NULL))
);

-- 策略引用的因子:只存因子版本編號,不存第二份因子定義(單一定義)。
-- 引用落在「具體定義 × 版本」那一級,不是族名那一級(CONTEXT.md 因子族)。
CREATE TABLE IF NOT EXISTS strategy_factor_ref (
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    factor_version_id   INTEGER NOT NULL REFERENCES factor_version(factor_version_id),
    PRIMARY KEY (strategy_version_id, factor_version_id)
);

-- 參數集:掛在一個策略版本上的一組「名稱→值」,必帶換倉節奏。
-- 換倉節奏無預設值(CONTEXT.md 換倉節奏;用戶反問「Why we need a default?」),缺就寫不入。
-- 收哪幾個節奏不在此處寫死:見上面 _CADENCE_SLOT,取值由引擎那份正本砌出來。
CREATE TABLE IF NOT EXISTS param_set (
    param_set_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    name                TEXT NOT NULL,
    version_no          INTEGER NOT NULL,
    parent_version_id   INTEGER REFERENCES param_set(param_set_id),
    rebalance_cadence   TEXT NOT NULL CHECK (rebalance_cadence IN (__REBALANCE_CADENCES__)),
    created_at          TEXT NOT NULL,
    UNIQUE (strategy_version_id, name, version_no),
    CHECK (length(trim(name)) > 0),
    CHECK ((version_no = 1 AND parent_version_id IS NULL)
        OR (version_no > 1 AND parent_version_id IS NOT NULL))
);

-- 參數值:一個參數集內每個參數只有一個值,不留空(無預設值)。
CREATE TABLE IF NOT EXISTS param_value (
    param_set_id INTEGER NOT NULL REFERENCES param_set(param_set_id),
    param_key    TEXT NOT NULL,
    param_value  TEXT NOT NULL,
    PRIMARY KEY (param_set_id, param_key),
    CHECK (length(trim(param_key)) > 0 AND length(trim(param_value)) > 0)
);

-- 寫入者簽章:凡經唯一入口寫入的列在此有一筆,簽章的鑰匙住在庫外。
-- 直接改庫寫入的列在此無簽章,karst verify 一掃即揪得出(D-020 第 4 條)。
CREATE TABLE IF NOT EXISTS gateway_write (
    write_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name     TEXT NOT NULL,
    row_key        TEXT NOT NULL,
    content_digest TEXT NOT NULL,
    signature      TEXT NOT NULL,
    writer         TEXT NOT NULL,
    written_at     TEXT NOT NULL,
    UNIQUE (table_name, row_key)
);

CREATE TRIGGER IF NOT EXISTS trg_strategy_no_update
BEFORE UPDATE ON strategy BEGIN
    SELECT RAISE(ABORT, '策略落庫後不可改,只可出新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_no_delete
BEFORE DELETE ON strategy BEGIN
    SELECT RAISE(ABORT, '策略落庫後不可刪,版本鏈須完整');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_version_no_update
BEFORE UPDATE ON strategy_version BEGIN
    SELECT RAISE(ABORT, '策略版本落庫後不可改,只可出新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_version_no_delete
BEFORE DELETE ON strategy_version BEGIN
    SELECT RAISE(ABORT, '策略版本落庫後不可刪,版本鏈須完整');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_factor_ref_no_update
BEFORE UPDATE ON strategy_factor_ref BEGIN
    SELECT RAISE(ABORT, '策略引用的因子版本落庫後不可改,改引用請出策略新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_factor_ref_no_delete
BEFORE DELETE ON strategy_factor_ref BEGIN
    SELECT RAISE(ABORT, '策略引用的因子版本落庫後不可刪,改引用請出策略新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_param_set_no_update
BEFORE UPDATE ON param_set BEGIN
    SELECT RAISE(ABORT, '參數集落庫後不可改,只可出新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_param_set_no_delete
BEFORE DELETE ON param_set BEGIN
    SELECT RAISE(ABORT, '參數集落庫後不可刪,運行留痕要指得回它');
END;

CREATE TRIGGER IF NOT EXISTS trg_param_value_no_update
BEFORE UPDATE ON param_value BEGIN
    SELECT RAISE(ABORT, '參數值落庫後不可改,只可出參數集新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_param_value_no_delete
BEFORE DELETE ON param_value BEGIN
    SELECT RAISE(ABORT, '參數值落庫後不可刪,只可出參數集新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_gateway_write_no_update
BEFORE UPDATE ON gateway_write BEGIN
    SELECT RAISE(ABORT, '寫入者簽章不可改');
END;

CREATE TRIGGER IF NOT EXISTS trg_gateway_write_no_delete
BEFORE DELETE ON gateway_write BEGIN
    SELECT RAISE(ABORT, '寫入者簽章不可刪');
END;

-- 補簽留痕(KARST-087)。
--
-- 治理清單一收窄(這一次收入數據快照登記與抓取登記),清單裡就會出現一批「收窄之前
-- 已經落庫、一個簽章都沒有」的舊列。它們要補簽,否則 verify 由第一日起就永遠不清白,
-- 而一個長期紅色的核對報告等於沒有核對報告——真正的繞過寫入會混在那堆舊帳裡看不見。
--
-- 但補簽與「當日經唯一入口凍的」**不是同一回事**:前者只證明「補簽那一刻起這一列沒有
-- 再被改過」,後者證明「這一列由頭到尾都是經那道門寫的」。混為一談,就等於用一個今日
-- 蓋的章去擔保一件昨日發生的事。所以補簽一律在本表另留一列:哪一列、由誰、幾時、
-- 為什麼補。日後查一個簽章的來歷,查得出它是原簽還是補簽。
--
-- 本表**不入治理清單**,理由與 gateway_write 同:簽章冊自己簽自己等於沒有簽。它靠的是
-- 下面兩道閘(不可改、不可刪),以及它與 gateway_write 逐列對得上。
CREATE TABLE IF NOT EXISTS gateway_countersign (
    table_name       TEXT NOT NULL,
    row_key          TEXT NOT NULL,
    reason           TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    countersigned_by TEXT NOT NULL CHECK (length(trim(countersigned_by)) > 0),
    countersigned_at TEXT NOT NULL,
    PRIMARY KEY (table_name, row_key)
);

CREATE TRIGGER IF NOT EXISTS trg_gateway_countersign_no_update
BEFORE UPDATE ON gateway_countersign BEGIN
    SELECT RAISE(ABORT, '補簽留痕不可改;補簽的理由是一件已經發生的事');
END;

CREATE TRIGGER IF NOT EXISTS trg_gateway_countersign_no_delete
BEFORE DELETE ON gateway_countersign BEGIN
    SELECT RAISE(ABORT, '補簽留痕不可刪,追溯要分得出原簽與補簽');
END;

-- ====================================================================
-- 回測運行留痕(規格 7.4、D-020 第 7 條、D-021 第 9 條;KARST-026)
-- ====================================================================

-- 回測運行:運行編號 = 「策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本」的內容雜湊。
-- 同一組輸入永遠得同一個編號;運行一經落庫**一個字都不可改**,要改就是另一次運行。
-- 逐日淨值、逐日持倉、逐筆交易本體住在 parquet(D-026 第 1 條),本表只記落點與雜湊。
--
-- ``origin`` 是這次運行的**來歷**:``formal`` 正式運行(示例運行、用戶自行重跑),
-- ``sweep`` 參數掃描其中一格。無預設值——落庫那一刻講不出來歷,寧可寫不入
-- (KARST-054;以前庫內沒有這一格,畫面靠參數集名前綴猜,前綴一改掃描格就會扮成
-- 一套策略的門面成績,而且錯得無聲:假設 A-006)。
--
-- ``sweep_id`` 是掃描格所屬那次掃描的**掃描編號**:正式運行必須留空(CHECK 擋住),
-- 掃描格由掃描運行器落庫時填。留空的掃描格只有一種來路——第 8 版遷移之前已經在庫
-- 裡的舊列(當時庫內未有這一格,回填不出),見 ``_migrate_backtest_run_origin``。
-- 掃描編號**不入運行編號**:同一格無論屬於哪一次掃描,算出來仍是同一個運行編號。
CREATE TABLE IF NOT EXISTS backtest_run (
    run_id              TEXT PRIMARY KEY,
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    param_set_id        INTEGER NOT NULL REFERENCES param_set(param_set_id),
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    snapshot_id         TEXT NOT NULL REFERENCES data_snapshot(snapshot_id),
    engine_name         TEXT NOT NULL,
    engine_version      TEXT NOT NULL,
    fingerprint         TEXT NOT NULL UNIQUE,
    trading_days        INTEGER NOT NULL,
    origin              TEXT NOT NULL CHECK (origin IN ('formal', 'sweep')),
    sweep_id            TEXT,
    created_at          TEXT NOT NULL,
    CHECK (period_end >= period_start),
    CHECK (trading_days > 0),
    CHECK (length(trim(engine_name)) > 0 AND length(trim(engine_version)) > 0),
    CHECK (origin = 'sweep' OR sweep_id IS NULL),
    CHECK (sweep_id IS NULL OR length(trim(sweep_id)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_backtest_run_strategy
    ON backtest_run (strategy_version_id, created_at);

-- 總覽與運行清單一開就問「只要正式運行」,四千個掃描格不必逐個砌出來才篩走。
CREATE INDEX IF NOT EXISTS idx_backtest_run_origin
    ON backtest_run (origin, created_at);

-- 運行的序列檔:一次運行三份 parquet(逐日淨值、逐日持倉、逐筆交易),各記路徑與內容雜湊。
-- 雜湊是「同一輸入得同一結果」的憑據,亦是擋改寫的憑據——重錄時對不上即拒收。
CREATE TABLE IF NOT EXISTS run_artifact (
    run_id       TEXT NOT NULL REFERENCES backtest_run(run_id),
    kind         TEXT NOT NULL CHECK (kind IN ('equity', 'holdings', 'orders')),
    path         TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    rows         INTEGER NOT NULL CHECK (rows >= 0),
    PRIMARY KEY (run_id, kind)
);

-- 運行蓋齊的因子版本(D-021 第 9 條:運行記錄蓋齊所用因子版本)。
-- 因子或策略日後出新版,本表一字不變——只是比對之下該運行被查得出「過時」。
CREATE TABLE IF NOT EXISTS run_factor_ref (
    run_id            TEXT NOT NULL REFERENCES backtest_run(run_id),
    factor_version_id INTEGER NOT NULL REFERENCES factor_version(factor_version_id),
    PRIMARY KEY (run_id, factor_version_id)
);

CREATE TRIGGER IF NOT EXISTS trg_backtest_run_no_update
BEFORE UPDATE ON backtest_run BEGIN
    SELECT RAISE(ABORT, '回測運行落庫後不可改,要改就是另一次運行(另一個運行編號)');
END;

CREATE TRIGGER IF NOT EXISTS trg_backtest_run_no_delete
BEFORE DELETE ON backtest_run BEGIN
    SELECT RAISE(ABORT, '回測運行落庫後不可刪,歷次運行要指得回');
END;

CREATE TRIGGER IF NOT EXISTS trg_run_artifact_no_update
BEFORE UPDATE ON run_artifact BEGIN
    SELECT RAISE(ABORT, '運行的序列檔落點與雜湊不可改,重跑請出新運行');
END;

CREATE TRIGGER IF NOT EXISTS trg_run_artifact_no_delete
BEFORE DELETE ON run_artifact BEGIN
    SELECT RAISE(ABORT, '運行的序列檔登記不可刪');
END;

CREATE TRIGGER IF NOT EXISTS trg_run_factor_ref_no_update
BEFORE UPDATE ON run_factor_ref BEGIN
    SELECT RAISE(ABORT, '運行蓋住的因子版本不可改,舊運行永不自動更新,只標過時');
END;

CREATE TRIGGER IF NOT EXISTS trg_run_factor_ref_no_delete
BEFORE DELETE ON run_factor_ref BEGIN
    SELECT RAISE(ABORT, '運行蓋住的因子版本不可刪,追溯要指得回');
END;

-- 運行除名登記(KARST-093)。
--
-- 一次運行落了庫之後才發現「它根本不應該算數」——最常見的是自動測試經正式路徑
-- 跑出來的那種:測試要驗的是「重跑這條路行不行得通」,不是要為策略添一次成績,
-- 但它寫出來的那一列與人手跑的正式運行在庫內一模一樣,於是策略的正式運行計數
-- 無聲無息多了一條,門面成績、歷次運行表、運行選單全部跟住錯。
--
-- 除名照 ``data_snapshot_retraction`` 那一套(KARST-084):**加一列,不是刪一列**。
-- backtest_run 那一列、淨值與交易檔、參數集版本鏈全部一個字不動——
-- ``trg_backtest_run_no_delete`` 本來就寫明「運行登記不可刪,追溯要指得回」。
-- 除名之後:
--   · list_runs() 與 count_runs() 一律略過它——清單同計數列得出的只有算數的運行;
--   · get_run() 一類直連查詢照樣讀得到,追溯指得回;
--   · 運行目錄與 parquet 檔一個字都不動。
--
-- 這張表入治理清單(ledger.GOVERNED_TABLES),故此每一列都有唯一入口的寫入者簽章:
-- 「這次運行不算數」與「指定現役設定」同級,都是決定門面數字取哪幾次運行的定義級
-- 動作,不可以有人繞過那道門靜靜除掉一次運行。
CREATE TABLE IF NOT EXISTS backtest_run_retraction (
    run_id       TEXT PRIMARY KEY REFERENCES backtest_run(run_id),
    reason       TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    retracted_by TEXT NOT NULL CHECK (length(trim(retracted_by)) > 0),
    retracted_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_run_retraction_no_update
BEFORE UPDATE ON backtest_run_retraction BEGIN
    SELECT RAISE(ABORT, '運行除名登記落庫後不可改;判斷變了請另開票,不要改寫已發生的除名');
END;

CREATE TRIGGER IF NOT EXISTS trg_run_retraction_no_delete
BEFORE DELETE ON backtest_run_retraction BEGIN
    SELECT RAISE(ABORT, '運行除名登記不可刪,追溯要指得回');
END;

-- 批次登記(KARST-091;D-042、CONTEXT.md「批次登記」)。
--
-- **批次 = 一次參數掃描跑出來的那批運行。** 以前程式裡根本沒有一個叫批次的東西:
-- 一次掃描在庫內的痕跡只有運行表上一格 ``sweep_id`` 字串,其餘全部住在 experiments/
-- 底下的 CSV,而畫面靠掃實驗目錄、讀 CSV 反推——那是全站唯一真正繞過定義庫的地方。
-- 於是「哪一批最好」這句話(D-042 明文:達標運行的中位數年化最高)要由 CSV 反推,
-- 而 CSV 是任何人改得到的一份檔。
--
-- 本表把那一句收回庫內:一次掃描收工經唯一入口寫**一列**——格數、達標格數、隱藏了
-- 幾多條失敗運行、三個中位數、判讀目標與門檻、最佳格、代表格、批內最佳單次那個運行
-- 編號,以及報告落點與它的內容雜湊。門面左半那四個數自此問庫身要。
--
-- **它不碰運行。** 掃描編號本來就不入運行編號(KARST-054),所以批次登記是加一列,
-- 舊掃描可以事後補登記,既有運行一個位都不動。
--
-- 本表入治理清單(ledger.GOVERNED_TABLES),歸「定義」類——與 active_setup、
-- backtest_run_retraction 同級:三者都是決定「門面數字取哪幾次運行」的定義級動作。
-- 沒有簽章的批次登記即是有人繞過那道門塞一批看似達標的成績入門面,verify 一掃就見到。
--
-- 只加不改不刪:一次掃描的成績是一件已經發生的事。要換判讀口徑請重判並另寫一列
-- (重判出的是另一份判讀,不是把當日那份改掉)。
CREATE TABLE IF NOT EXISTS sweep_batch (
    sweep_id             TEXT PRIMARY KEY,
    strategy_version_id  INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    period_start         TEXT NOT NULL,
    period_end           TEXT NOT NULL,
    snapshot_id          TEXT NOT NULL REFERENCES data_snapshot(snapshot_id),
    engine_name          TEXT NOT NULL,
    engine_version       TEXT NOT NULL,
    cell_count           INTEGER NOT NULL CHECK (cell_count > 0),
    qualified_cells      INTEGER NOT NULL CHECK (qualified_cells >= 0),
    failed_cells         INTEGER NOT NULL CHECK (failed_cells >= 0),
    error_cells          INTEGER NOT NULL CHECK (error_cells >= 0),
    median_annual_return REAL,
    median_sortino       REAL,
    median_max_drawdown  REAL,
    objective            TEXT NOT NULL CHECK (length(trim(objective)) > 0),
    min_trades           INTEGER NOT NULL CHECK (min_trades >= 0),
    lonely_peak_margin   REAL NOT NULL,
    plateau_quantile     REAL NOT NULL,
    best_point           TEXT,
    best_run_id          TEXT REFERENCES backtest_run(run_id),
    representative_point TEXT,
    report_path          TEXT NOT NULL,
    report_hash          TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    CHECK (length(trim(sweep_id)) > 0),
    CHECK (period_end >= period_start),
    CHECK (length(trim(engine_name)) > 0 AND length(trim(engine_version)) > 0),
    CHECK (qualified_cells + failed_cells + error_cells <= cell_count)
);

CREATE INDEX IF NOT EXISTS idx_sweep_batch_strategy
    ON sweep_batch (strategy_version_id, created_at);

CREATE TRIGGER IF NOT EXISTS trg_sweep_batch_no_update
BEFORE UPDATE ON sweep_batch BEGIN
    SELECT RAISE(ABORT, '批次登記落庫後不可改;一次掃描的成績是一件已經發生的事,換判讀口徑請重判並另寫一列');
END;

CREATE TRIGGER IF NOT EXISTS trg_sweep_batch_no_delete
BEFORE DELETE ON sweep_batch BEGIN
    SELECT RAISE(ABORT, '批次登記不可刪,追溯要指得回');
END;

-- ====================================================================
-- 現役設定(規格 7.5、CONTEXT.md「現役設定」;KARST-030)
-- ====================================================================

-- 現役設定:一套策略由用戶指定、紙上交易實際跟隨的那個參數集。門面八個數字
-- 一律只取現役設定那次運行(規格 7.5,防參數擬合美化)。
--
-- 本表是**只加不改的指定登記**:換一個現役設定 = 加一列新的,舊列一字不變。
-- 「現在的現役設定」= 該策略 seq_no 最大的那一列。這樣換設定之後仍然查得出
-- 「上一次跟隨的是哪一個、由哪一日起」——與運行不可改同一個道理。
--
-- 指的是 param_set_id 而不是參數集名稱:參數集同名會出新版(param_set 一版一列),
-- 現役設定必須釘死其中一版,否則參數集一出新版門面數字就會悄悄換一個口徑。
CREATE TABLE IF NOT EXISTS active_setup (
    strategy_id         INTEGER NOT NULL REFERENCES strategy(strategy_id),
    seq_no              INTEGER NOT NULL,
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    param_set_id        INTEGER NOT NULL REFERENCES param_set(param_set_id),
    note                TEXT,
    designated_at       TEXT NOT NULL,
    PRIMARY KEY (strategy_id, seq_no),
    CHECK (seq_no > 0)
);

CREATE INDEX IF NOT EXISTS idx_active_setup_strategy
    ON active_setup (strategy_id, seq_no);

CREATE TRIGGER IF NOT EXISTS trg_active_setup_no_update
BEFORE UPDATE ON active_setup BEGIN
    SELECT RAISE(ABORT, '現役設定的指定不可改,換設定請加新一筆指定');
END;

CREATE TRIGGER IF NOT EXISTS trg_active_setup_no_delete
BEFORE DELETE ON active_setup BEGIN
    SELECT RAISE(ABORT, '現役設定的指定不可刪,換過什麼要指得回');
END;

-- 參數集對齊標記(D-038、CONTEXT.md「參數集對齊標記」;KARST-094)。
--
-- D-038 講明:示例參數集只是通鏈用的取值,未經與用戶對齊,**不是現役設定**,而
-- 「畫面與紀錄須能分辨」。KARST-090 把這句話做成登記時強制申報(``register_setup``
-- 的 ``alignment`` 無預設值,漏填當場拒收),但結果只掛在記憶體的 ``Setup`` 上——
-- 庫裡查不到哪個參數集是示例,日後看報告的人分不出。
--
-- 為什麼是**旁表**而不是參數集多一格:兩條路都撞牆。當一格參數值,參數集內容就變,
-- 而運行編號正是由參數集內容雜湊而來(KARST-026),13 條正式運行會全部改號;做成
-- ``param_set`` 一條新欄,該表的 ``content_digest`` 就變,8326 列既有寫入者簽章
-- 一次過作廢,``karst verify`` 會全紅。主腦於 KARST-090 裁決:標記是一件**治理
-- 資料**,不是策略身份的一部分,所以它不應該進入運行編號的雜湊(假設 A-014,
-- 2026-08-30 查證成立)。旁表兩樣都不碰:運行編號一位不變、既有簽章一個不動。
--
-- **追加式,一列都不改不刪。** 改標記(示例查證過後對齊了,或者對齊依據推翻了)
-- = 加一列新的 ``seq_no``,舊列一字不變——與 ``active_setup`` 同制。「這個參數集
-- 現在的標記」= 該 ``param_set_id`` 之下 ``seq_no`` 最大那一列;歷次改過什麼、
-- 由哪一刻起、依據是什麼,全部查得回。改寫已發生的申報等於把當日那個判斷抹走。
--
-- ``aligned_on``(對齊日期)只有已對齊那一種才有,示例一律留空:示例從來沒有對齊
-- 過,給它一個日期就是憑空造一件沒有發生過的事。CHECK 把這句話寫死在庫身上。
--
-- 本表入治理清單(ledger.GOVERNED_TABLES),歸「定義」類——與 active_setup、
-- backtest_run_retraction、sweep_batch 同級:四者都不是數據來源出了事(那是
-- 「快照」),而是一句「畫面上這個數字算不算數、代表什麼」的定義級講法。沒有簽章
-- 的對齊標記即是有人繞過唯一入口把一組未對齊的示例取值標成已對齊、送上門面充當
-- 現役設定,而那正是 D-038 要防的那件事;verify 一掃就見到。
CREATE TABLE IF NOT EXISTS param_set_alignment (
    param_set_id INTEGER NOT NULL REFERENCES param_set(param_set_id),
    seq_no       INTEGER NOT NULL,
    mark         TEXT NOT NULL CHECK (mark IN ('aligned', 'sample')),
    aligned_on   TEXT,
    basis        TEXT NOT NULL CHECK (length(trim(basis)) > 0),
    recorded_at  TEXT NOT NULL,
    PRIMARY KEY (param_set_id, seq_no),
    CHECK (seq_no > 0),
    CHECK ((mark = 'aligned') = (aligned_on IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_param_set_alignment_set
    ON param_set_alignment (param_set_id, seq_no);

CREATE TRIGGER IF NOT EXISTS trg_param_set_alignment_no_update
BEFORE UPDATE ON param_set_alignment BEGIN
    SELECT RAISE(ABORT, '參數集對齊標記落庫後不可改;標記變了請加新一筆申報,不要改寫已發生的申報');
END;

CREATE TRIGGER IF NOT EXISTS trg_param_set_alignment_no_delete
BEFORE DELETE ON param_set_alignment BEGIN
    SELECT RAISE(ABORT, '參數集對齊標記不可刪,追溯要指得回');
END;

-- 策略治理宣告(D-054、D-056、D-058;CONTEXT.md「由上而下三層」「離場治理」;KARST-116)。
--
-- 一條策略要交代兩件事,兩件都**必填**:
--
-- ``layer``            它屬由上而下三層的哪一層:``regime`` 市況(防守階梯)、``sector`` 板塊、
--                      ``stock`` 個股。D-054 定平台重心為這三層,任何策略按此次序收窄,
--                      不准跳層由個股起步——一條策略講不出自己站在哪一層,就無從判它有沒有
--                      跳層。
-- ``exit_governance``  它的離場治理屬哪一型:``continuation`` 延續型注(價格止蝕增值、不准
--                      溝貨、賠率門檻有意義)、``reversion`` 回歸型注(價格止蝕有害,離場靠
--                      入場前寫死的論點失效條件加注碼上限)、``rule_based`` 規則型(既非押
--                      延續亦非押回歸,離場由預先寫死的規則逐期重算,無價格止蝕亦無論點條件)。
--                      D-056 第 2 條:治理配置必須在入場之前寫死,是策略合約的一部分。
--
-- 為什麼是**旁表**而不是 ``strategy`` 多兩欄:兩條路都撞牆。``strategy`` 有
-- ``trg_strategy_no_update`` 擋住 UPDATE(登記按設計不可改不可刪),多兩欄的話現存三條登記
-- 永遠補填不到;而且多兩欄會改動該表的 content_digest,既有簽章一次過作廢,``verify`` 全紅。
-- 旁表兩樣都不碰,而且與 ``param_set_alignment`` 同制(KARST-094 走過同一條路)。
--
-- **追加式,一列都不改不刪。** 改宣告(例如一條策略由個股層改編為板塊層)= 加一列新的
-- ``seq_no``,舊列一字不變。「這條策略現在屬哪一層」= 該 ``strategy_id`` 之下 ``seq_no``
-- 最大那一列;歷次改過什麼、由哪一刻起、依據是什麼,全部查得回。
--
-- ``basis``(宣告依據一句)不准留空:無理由的宣告等於沒有宣告,日後無人分得出它是判過的
-- 還是隨手填的——與對齊標記同一句話。
--
-- 本表入治理清單(ledger.GOVERNED_TABLES),歸「定義」類:它與 active_setup 同級,是一句
-- 「這條策略是什麼、它的注怎樣走」的定義級講法。沒有簽章的宣告即是有人繞過唯一入口替一條
-- 策略改層別或改離場分型,而那正是 D-057/D-058 要防的漂移。
CREATE TABLE IF NOT EXISTS strategy_governance (
    strategy_id      INTEGER NOT NULL REFERENCES strategy(strategy_id),
    seq_no           INTEGER NOT NULL,
    layer            TEXT NOT NULL CHECK (layer IN ('regime', 'sector', 'stock')),
    exit_governance  TEXT NOT NULL CHECK (exit_governance IN (
        'continuation', 'reversion', 'rule_based')),
    basis            TEXT NOT NULL CHECK (length(trim(basis)) > 0),
    declared_at      TEXT NOT NULL,
    PRIMARY KEY (strategy_id, seq_no),
    CHECK (seq_no > 0)
);

CREATE INDEX IF NOT EXISTS idx_strategy_governance_strategy
    ON strategy_governance (strategy_id, seq_no);

CREATE TRIGGER IF NOT EXISTS trg_strategy_governance_no_update
BEFORE UPDATE ON strategy_governance BEGIN
    SELECT RAISE(ABORT, '策略治理宣告落庫後不可改;層別或離場分型變了請加新一筆宣告,不要改寫已發生的宣告');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_governance_no_delete
BEFORE DELETE ON strategy_governance BEGIN
    SELECT RAISE(ABORT, '策略治理宣告不可刪,追溯要指得回');
END;

-- ====================================================================
-- 共用風控層(D-013 第 4 條、規格 1.6;KARST-025)
-- ====================================================================

-- 共用風控規則:單筆風險上限、月度虧損熔斷、賠率門檻,三條各一列,全庫只此一份。
-- 規則本體(叫什麼、管什麼、參數叫什麼名)的正本在 karst/risk;本表是它的登記處,
-- 內容由該層提供,不在此處另寫一份。
--
-- **取值不在本表**:取值屬用戶領域,住在該策略自己的參數集(param_value),
-- 一律做成可掃描的參數(D-008 第 3 條)。同一條規則、兩套策略、各自的取值,
-- 改一邊不會動到另一邊——正因為兩邊改的都是自己的參數集,不是這條規則。
CREATE TABLE IF NOT EXISTS risk_rule (
    risk_rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_key     TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL UNIQUE,
    param_key    TEXT NOT NULL UNIQUE,
    description  TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    CHECK (length(trim(rule_key)) > 0 AND length(trim(name)) > 0),
    CHECK (length(trim(param_key)) > 0 AND length(trim(description)) > 0)
);

-- 策略引用了哪幾條風控規則:只存編號,不存規則本身(單一定義,與引用因子同制)。
-- 一條都不引用 = 這裡一列都沒有,那套策略照樣跑得(D-013 第 4 條「可用可不用」)。
CREATE TABLE IF NOT EXISTS strategy_risk_ref (
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    risk_rule_id        INTEGER NOT NULL REFERENCES risk_rule(risk_rule_id),
    PRIMARY KEY (strategy_version_id, risk_rule_id)
);

CREATE TRIGGER IF NOT EXISTS trg_risk_rule_no_update
BEFORE UPDATE ON risk_rule BEGIN
    SELECT RAISE(ABORT, '共用風控規則的定義落庫後不可改;三條規則全平台只有一個正本');
END;

CREATE TRIGGER IF NOT EXISTS trg_risk_rule_no_delete
BEFORE DELETE ON risk_rule BEGIN
    SELECT RAISE(ABORT, '共用風控規則的定義不可刪;策略引用要指得回');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_risk_ref_no_update
BEFORE UPDATE ON strategy_risk_ref BEGIN
    SELECT RAISE(ABORT, '策略引用的風控規則落庫後不可改,改引用請出策略新版');
END;

CREATE TRIGGER IF NOT EXISTS trg_strategy_risk_ref_no_delete
BEFORE DELETE ON strategy_risk_ref BEGIN
    SELECT RAISE(ABORT, '策略引用的風控規則落庫後不可刪,改引用請出策略新版');
END;

-- ====================================================================
-- 數據快照的抓取登記(D-026 第 3 條;KARST-034)
-- ====================================================================

-- 一次抓取的隨身資料:幾時抓、抓的是哪一段窗口、抓了多少個實體多少列。
-- 快照編號本身不含抓取時間(同一批數據重抓要得同一個編號),故這幾格另有落點。
--
-- 為什麼另開一張附表,而不是在 data_snapshot 加欄:快照登記一經落庫不可改
-- (trg_snapshot_no_update),舊庫已有的快照列亦不會憑空多出這幾格值;附表只加不改,
-- 舊列一個字都不用動。查不到附表那一列 = 那個快照不是經唯一入口凍的,不是資料缺失。
--
-- **來源不在本表再寫一次**:它的正本住在 data_snapshot.source(單一定義,無第二影像)。
-- 要「抓取時間連來源」一次過取,經 karst/store.py 的 list_snapshots() 兩表併讀。
--
-- ``alert_count`` / ``alert_summary`` 是凍結那一刻的**齊全度核對結果**(KARST-067):
-- 幾多條序列超出門檻、一句講得出是哪幾條。以前這件事只寫在已凍結快照自己的
-- manifest 與說明檔,``karst data list`` 看不到——要開目錄才知道某個快照當日有沒有
-- 警報(KARST-061 留言點名的那個缺口)。
--
-- **兩格都可以留空,而留空有它自己的意思**:``NULL`` = 這個快照根本沒有經過齊全度
-- 核對(價格快照沒有主日曆可核;第 9 版之前登記的舊列亦回填不出),``0`` = 核對過而
-- 且零警報。把「沒有核對過」寫成 0,就是把一件沒有發生過的核對記成合格——那正是
-- ^VIX3M 停更 28 日無人察覺(假設 A-008)那件事的同一種錯。兩格同生共死:
-- 有條數就有摘要,有摘要就有條數。
CREATE TABLE IF NOT EXISTS data_snapshot_fetch (
    snapshot_id   TEXT PRIMARY KEY REFERENCES data_snapshot(snapshot_id),
    fetched_at    TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    entity_count  INTEGER NOT NULL CHECK (entity_count >= 0),
    row_count     INTEGER NOT NULL CHECK (row_count >= 0),
    trading_days  INTEGER NOT NULL CHECK (trading_days >= 0),
    recorded_at   TEXT NOT NULL,
    alert_count   INTEGER CHECK (alert_count IS NULL OR alert_count >= 0),
    alert_summary TEXT CHECK ((alert_count IS NULL) = (alert_summary IS NULL)),
    CHECK (window_end >= window_start),
    CHECK (length(trim(fetched_at)) > 0)
);

CREATE TRIGGER IF NOT EXISTS trg_snapshot_fetch_no_update
BEFORE UPDATE ON data_snapshot_fetch BEGIN
    SELECT RAISE(ABORT, '快照的抓取登記不可改;重抓同一段數據得同一個快照編號,沿用原本那次的抓取時間');
END;

CREATE TRIGGER IF NOT EXISTS trg_snapshot_fetch_no_delete
BEFORE DELETE ON data_snapshot_fetch BEGIN
    SELECT RAISE(ABORT, '快照的抓取登記不可刪,追溯要指得回');
END;
"""


def _cadence_values_sql() -> str:
    """砌出 CHECK 裡那串取值,例如 ``'daily', 'monthly', 'quarterly', 'weekly'``。

    正本要等到本函式被叫的那一刻才匯入:``karst.engine`` 反過來要匯入
    ``karst.store``,而 ``karst.store`` 匯入本檔,寫在檔頭會兜成一個圈
    (與 ``karst/store.py`` 的 ``rebalance_cadences()`` 同一個做法)。
    """
    from .engine.contracts import CADENCES

    return ", ".join(f"'{cadence}'" for cadence in sorted(CADENCES))


def ddl() -> str:
    """完整建表 DDL。換倉節奏那一格由引擎那份正本即場砌入。"""
    return _DDL_TEMPLATE.replace(_CADENCE_SLOT, _cadence_values_sql())


def __getattr__(name: str) -> Any:
    """``DDL`` 是即場由正本砌出來的,不是本檔另存的第二份表結構。"""
    if name == "DDL":
        return ddl()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _cadences_in_db(conn: sqlite3.Connection) -> frozenset[str] | None:
    """庫身現有的 ``param_set`` 收哪幾個換倉節奏;表未建成則 ``None``。"""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'param_set'"
    ).fetchone()
    if row is None or not row[0]:
        return None
    clause = re.search(r"rebalance_cadence\s+IN\s*\(([^)]*)\)", row[0], re.IGNORECASE)
    if clause is None:
        return None
    return frozenset(re.findall(r"'([^']*)'", clause.group(1)))


def _migrate_param_set_cadence(conn: sqlite3.Connection) -> bool:
    """舊庫的 ``param_set`` 重建一次,只換換倉節奏那條 CHECK(KARST-044)。

    sqlite 改不到 CHECK,唯一做法是整張表重建:開新表 → 逐列搬過去 → 刪舊表 →
    改名 → 讓 DDL 補回隨舊表一齊消失的觸發器。

    **``param_set_id`` 逐個原封搬過去**:唯一入口的簽章是按 ``param_set[<id>]``
    這個 row key 記的,``param_value`` 等表亦以它做外鍵。取值一個字不改,所以
    內容雜湊不變、簽章仍然有效——搬完 ``karst verify`` 照舊清白。

    只在偵測到舊版(庫身收的節奏與正本對不上)時跑,跑完庫身就是正本那一份,
    重開不會再跑。回傳有沒有真的搬過。
    """
    from .engine.contracts import CADENCES

    recorded = _cadences_in_db(conn)
    if recorded is None or recorded == frozenset(CADENCES):
        return False

    statement = re.search(
        r"CREATE TABLE IF NOT EXISTS param_set \(.*?\n\);", ddl(), re.DOTALL
    )
    if statement is None:  # pragma: no cover - DDL 改壞才會走到這裡
        raise RuntimeError("建表 DDL 裡找不到 param_set,無法重建")
    create_new = statement.group(0).replace(
        "CREATE TABLE IF NOT EXISTS param_set (", "CREATE TABLE param_set_new (", 1
    )

    # 欄位由舊表自己報:新表與舊表同欄位,只換 CHECK,所以此處不另抄一份欄位名。
    columns = [str(row["name"]) for row in conn.execute("PRAGMA table_info(param_set)")]
    column_list = ", ".join(f'"{column}"' for column in columns)

    # PRAGMA foreign_keys 在交易之內是無聲的空操作,所以收放都要在 BEGIN 之外。
    conn.commit()
    previous_isolation = conn.isolation_level
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            conn.execute(create_new)
            conn.execute(
                f"INSERT INTO param_set_new ({column_list}) "
                f"SELECT {column_list} FROM param_set"
            )
            conn.execute("DROP TABLE param_set")
            conn.execute("ALTER TABLE param_set_new RENAME TO param_set")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.isolation_level = previous_isolation
        conn.execute("PRAGMA foreign_keys = ON")

    # 觸發器隨舊表一齊消失,DDL 是 IF NOT EXISTS,重跑即補回。
    conn.executescript(ddl())
    broken = conn.execute("PRAGMA foreign_key_check").fetchall()
    if broken:  # pragma: no cover - 搬表搬漏了才會走到這裡
        raise RuntimeError(f"param_set 重建後外鍵對不上:{[tuple(r) for r in broken]}")
    conn.commit()
    return True


# 舊庫回填來歷時用的判準:參數集名的前綴。這正是 KARST-049 靠住的那條名前綴判準
# (假設 A-006),自第 8 版起**全倉只此一處**——而且只在遷移那一刻用一次。遷移之後
# 沒有任何一段程式再靠名字猜來歷:問庫身那一格就有答案。
_LEGACY_SWEEP_PREFIX = "掃描"

# 遷移記錄的落點:遷移做過什麼,寫在庫身自己那張 schema_meta,不寫在別處的筆記。
# 下一個開這個庫的人問「這 4,085 格的來歷是誰填的、憑什麼」,答案就在庫內。
RUN_ORIGIN_MIGRATION_KEY = "migration_008_run_origin"


def _migrate_backtest_run_origin(conn: sqlite3.Connection) -> tuple[int, int] | None:
    """舊庫的 ``backtest_run`` 重建一次,補上來歷與掃描編號兩格(KARST-054)。

    做法照 ``_migrate_param_set_cadence``(KARST-044):sqlite 加不到「NOT NULL
    而且無預設值」的欄,唯一做法是整張表重建——開新表 → 逐列搬過去 → 刪舊表 →
    改名 → 讓 DDL 補回隨舊表一齊消失的索引與觸發器。全程一個交易,搬完即
    ``PRAGMA foreign_key_check``。

    **``run_id`` 逐個原封搬過去**:運行編號是「策略版本 × 參數集 × 期間 × 數據快照
    × 引擎版本」的雜湊,本次遷移一件都沒有動過,所以編號逐位不變;``run_artifact``
    與 ``run_factor_ref`` 靠它做外鍵,亦一列不用改。

    來歷按**當時那條名前綴判準**回填一次:參數集名以「掃描」開頭的當掃描格,其餘當
    正式運行。回填的掃描格**沒有掃描編號**——那一格當時不在庫內,回填不出,寧可留空
    也不猜一個出來。回填了幾多列寫入 ``schema_meta``(見 ``RUN_ORIGIN_MIGRATION_KEY``)。

    只在偵測到舊版(表在、但沒有 ``origin`` 那一格)時跑,跑完重開不會再跑。
    回傳 ``(正式運行列數, 掃描格列數)``;沒有搬過即 ``None``。
    """
    columns = [str(row["name"]) for row in conn.execute("PRAGMA table_info(backtest_run)")]
    if not columns or "origin" in columns:
        return None

    statement = re.search(
        r"CREATE TABLE IF NOT EXISTS backtest_run \(.*?\n\);", ddl(), re.DOTALL
    )
    if statement is None:  # pragma: no cover - DDL 改壞才會走到這裡
        raise RuntimeError("建表 DDL 裡找不到 backtest_run,無法重建")
    create_new = statement.group(0).replace(
        "CREATE TABLE IF NOT EXISTS backtest_run (", "CREATE TABLE backtest_run_new (", 1
    )

    column_list = ", ".join(f'"{column}"' for column in columns)
    select_list = ", ".join(f'r."{column}"' for column in columns)
    origin_case = (
        "CASE WHEN p.name LIKE ? || '%' THEN 'sweep' ELSE 'formal' END"
    )

    counted = conn.execute(
        f"SELECT {origin_case} AS origin, COUNT(*) AS n FROM backtest_run AS r"
        " JOIN param_set AS p ON p.param_set_id = r.param_set_id GROUP BY 1",
        (_LEGACY_SWEEP_PREFIX,),
    ).fetchall()
    tally = {str(row["origin"]): int(row["n"]) for row in counted}
    formal_rows, sweep_rows = tally.get("formal", 0), tally.get("sweep", 0)
    note = (
        f"第 8 版遷移:backtest_run 補上來歷與掃描編號兩格。庫內原有的 "
        f"{formal_rows + sweep_rows} 次運行按當時那條判準(參數集名以"
        f"「{_LEGACY_SWEEP_PREFIX}」開頭即掃描格)回填一次:掃描格 {sweep_rows} 格、"
        f"正式運行 {formal_rows} 次。回填的掃描格沒有掃描編號(那一格當時不在庫內,"
        "回填不出,留空而不猜)。運行編號一位都沒有改。"
    )

    # PRAGMA foreign_keys 在交易之內是無聲的空操作,所以收放都要在 BEGIN 之外。
    conn.commit()
    previous_isolation = conn.isolation_level
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            conn.execute(create_new)
            conn.execute(
                f"INSERT INTO backtest_run_new ({column_list}, origin)"
                f" SELECT {select_list}, {origin_case} FROM backtest_run AS r"
                " JOIN param_set AS p ON p.param_set_id = r.param_set_id",
                (_LEGACY_SWEEP_PREFIX,),
            )
            conn.execute("DROP TABLE backtest_run")
            conn.execute("ALTER TABLE backtest_run_new RENAME TO backtest_run")
            conn.execute(
                "INSERT OR IGNORE INTO schema_meta (key, value) VALUES (?, ?)",
                (RUN_ORIGIN_MIGRATION_KEY, note),
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.isolation_level = previous_isolation
        conn.execute("PRAGMA foreign_keys = ON")

    # 索引與觸發器隨舊表一齊消失,DDL 是 IF NOT EXISTS,重跑即補回。
    conn.executescript(ddl())
    broken = conn.execute("PRAGMA foreign_key_check").fetchall()
    if broken:  # pragma: no cover - 搬表搬漏了才會走到這裡
        raise RuntimeError(f"backtest_run 重建後外鍵對不上:{[tuple(r) for r in broken]}")
    conn.commit()
    return formal_rows, sweep_rows


# 第 9 版遷移的記錄落點:補了什麼、補在幾多列身上,寫在庫身自己那張 schema_meta。
SNAPSHOT_FETCH_ALERTS_MIGRATION_KEY = "migration_009_snapshot_fetch_alerts"

# 補的是哪兩格。欄位定義**不在此處另寫一次**:由上面那份建表 DDL 抄出來
# (見 ``_column_definition``),免得新庫與遷移過的舊庫各有一套寫法。
_ALERT_COLUMNS = ("alert_count", "alert_summary")


def _column_definition(table: str, column: str) -> str:
    """由建表 DDL 取一欄的定義原文(連它自己那條 CHECK)。"""
    statement = re.search(
        rf"CREATE TABLE IF NOT EXISTS {table} \(.*?\n\);", ddl(), re.DOTALL
    )
    if statement is None:  # pragma: no cover - DDL 改壞才會走到這裡
        raise RuntimeError(f"建表 DDL 裡找不到 {table},無法補欄")
    line = re.search(rf"^\s*{column}\s+(.+)$", statement.group(0), re.M)
    if line is None:  # pragma: no cover - DDL 改壞才會走到這裡
        raise RuntimeError(f"{table} 的 DDL 裡找不到 {column} 那一欄")
    return f"{column} {line.group(1).strip().rstrip(',')}"


def _migrate_snapshot_fetch_alerts(conn: sqlite3.Connection) -> int | None:
    """舊庫的 ``data_snapshot_fetch`` 原地補上齊全度那兩格(KARST-067)。

    與第 7、8 版那兩個遷移不同,**這一次不重建表**:兩格都可以留空,所以
    ``ALTER TABLE ... ADD COLUMN`` 補得到。既有登記一列都不用搬——連
    ``fetched_at`` 那個「第一次凍結是哪一刻」都不會在搬運途中被碰過,而那正是
    這張表唯一答得出、事後補不回的東西。

    舊列補出來是 ``NULL``,即「這個快照沒有經過齊全度核對」。**不回填 0**:
    第 9 版之前根本沒有人核對過那幾份快照,把它記成「核對過、零警報」,就是把
    一件沒有發生過的核對寫成合格——與 ^VIX3M 停更 28 日仍然看似正常(假設 A-008)
    是同一種錯。

    只在偵測到舊版(表在、但沒有 ``alert_count`` 那一格)時跑,跑完重開不會再跑。
    回傳庫內原有幾多列抓取登記;沒有補過即 ``None``。
    """
    columns = [
        str(row["name"]) for row in conn.execute("PRAGMA table_info(data_snapshot_fetch)")
    ]
    if not columns or _ALERT_COLUMNS[0] in columns:
        return None

    existing = int(
        conn.execute("SELECT COUNT(*) AS n FROM data_snapshot_fetch").fetchone()["n"]
    )
    note = (
        f"第 9 版遷移:data_snapshot_fetch 原地補上齊全度警報條數與警報摘要兩格。"
        f"庫內原有的 {existing} 筆抓取登記一列都沒有搬過,兩格一律留空——"
        "第 9 版之前沒有人核對過那幾份快照的齊全度,回填不出,留空而不記成零警報。"
    )
    with conn:
        for column in _ALERT_COLUMNS:
            conn.execute(
                "ALTER TABLE data_snapshot_fetch ADD COLUMN "
                + _column_definition("data_snapshot_fetch", column)
            )
        conn.execute(
            "INSERT OR IGNORE INTO schema_meta (key, value) VALUES (?, ?)",
            (SNAPSHOT_FETCH_ALERTS_MIGRATION_KEY, note),
        )
    return existing


# 第 10 版遷移的記錄落點:補了什麼、補在幾多列身上,寫在庫身自己那張 schema_meta。
FACTOR_VALUE_EXECUTABLE_MIGRATION_KEY = "migration_010_factor_value_executable_time"

# 補的是哪一格。欄位定義同樣不在此處另寫一次,由建表 DDL 抄出來。
_EXECUTABLE_COLUMN = "executable_time"


def _migrate_factor_value_executable_time(conn: sqlite3.Connection) -> int | None:
    """舊庫的 ``factor_value`` 原地補上可執行時點那一格(KARST-064)。

    做法照第 9 版(``_migrate_snapshot_fetch_alerts``)而**不是**第 7、8 版那種
    整表重建:這一格可以留空,``ALTER TABLE ... ADD COLUMN`` 補得到。因子值落庫
    之後不可改不可刪(D-021 第 9 條,兩個 trigger 鎖住),重建表等於把每一列都
    搬過一次;能不搬就不搬。

    舊列補出來是 ``NULL``。**不回填**:一個舊值的可執行時點要靠它那個快照的日曆
    才數得出下一根 K 線是哪一日,回填就是替一件沒有發生過的登記編一個答案;而且
    ``snapshot_id`` 本身容許留空,那些列連日曆都無從查起。留空的意思寫在建表 DDL
    的註解裡:值知得到、成交不到。

    只在偵測到舊版(表在、但沒有 ``executable_time`` 那一格)時跑,跑完重開不會
    再跑。回傳庫內原有幾多列因子值;沒有補過即 ``None``。
    """
    columns = [str(row["name"]) for row in conn.execute("PRAGMA table_info(factor_value)")]
    if not columns or _EXECUTABLE_COLUMN in columns:
        return None

    existing = int(conn.execute("SELECT COUNT(*) AS n FROM factor_value").fetchone()["n"])
    note = (
        f"第 10 版遷移:factor_value 原地補上可執行時點一格。庫內原有的 {existing} "
        "個因子值一列都沒有搬過,那一格一律留空——第 10 版之前沒有人登記過可執行"
        "時點,要靠各自那個快照的日曆才數得出下一根 K 線,回填不出,留空而不猜。"
    )
    with conn:
        conn.execute(
            "ALTER TABLE factor_value ADD COLUMN "
            + _column_definition("factor_value", _EXECUTABLE_COLUMN)
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_meta (key, value) VALUES (?, ?)",
            (FACTOR_VALUE_EXECUTABLE_MIGRATION_KEY, note),
        )
    return existing


# 第 11 版遷移的記錄落點:搬走了幾多個值、憑什麼敢搬,寫在庫身自己那張 schema_meta。
FACTOR_VALUES_TO_FILES_MIGRATION_KEY = "migration_011_factor_values_to_files"


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _migrate_factor_values_to_files(conn: sqlite3.Connection) -> int | None:
    """把已經搬去 Parquet 的因子值清出 ``factor_value``(D-032;KARST-068)。

    **證明搬完了才清**,三個條件缺一不可:

    1. 表內每一個有值的因子版本,在 ``factor_value_batch_member`` 都登記得到;
    2. 那個因子版本在檔案裡的行數,與表內的行數逐個對得上;
    3. 每一個批次檔真的在它登記的落點上。

    有一項對不上就**一列都不動**(回 ``None``),寧可庫檔留著 1.6 GB。清空是不可逆
    的,而「值已經在別處」這句話若果是猜的,清完就再也證不回——所以這裡不猜,
    要麼三項齊備、要麼原封不動。

    清法是 ``DROP TABLE`` 再由建表 DDL 重建一張空表(連索引與兩個 trigger)。
    不用逐列 ``DELETE``:因子值落庫後不可刪(trigger 鎖住),而 555 萬列逐列刪
    要先拆走那道鎖再裝回去——拆鎖的窗口比重建一張空表危險。**既有編號一個都不動**:
    factor、factor_version、entity 三張表連碰都沒有碰過,所以策略引用、運行蓋住的
    因子版本、實體編號照舊逐個指得回。

    庫檔的體積要等 ``VACUUM`` 才縮——sqlite 只是把頁面標成可再用。本函式刻意不
    自己跑 ``VACUUM``:那是一次全庫重寫,不應該在別人只是開一開庫的時候發生。

    只跑一次:跑完在 ``schema_meta`` 留一筆,下次重開見到那一筆就不再數。
    回傳清走了幾多個值;沒有清過即 ``None``。
    """
    if not _table_exists(conn, "factor_value") or not _table_exists(conn, "schema_meta"):
        return None
    done = conn.execute(
        "SELECT 1 FROM schema_meta WHERE key = ?", (FACTOR_VALUES_TO_FILES_MIGRATION_KEY,)
    ).fetchone()
    if done is not None:
        return None

    # 先看有沒有登記,才去數表內那幾百萬列:數一次是一次全表掃描,而未有登記
    # 那一刻怎樣數都清不了。
    if not _table_exists(conn, "factor_value_batch_member"):
        return None
    if conn.execute("SELECT COUNT(*) AS n FROM factor_value_batch").fetchone()["n"] == 0:
        return None

    in_table = {
        int(row["factor_version_id"]): int(row["n"])
        for row in conn.execute(
            "SELECT factor_version_id, COUNT(*) AS n FROM factor_value GROUP BY factor_version_id"
        )
    }
    if not in_table:
        return None

    in_files = {
        int(row["factor_version_id"]): int(row["n"])
        for row in conn.execute(
            "SELECT factor_version_id, SUM(rows) AS n FROM factor_value_batch_member"
            " GROUP BY factor_version_id"
        )
    }
    if any(in_files.get(version) != rows for version, rows in in_table.items()):
        return None
    if any(
        not Path(str(row["path"])).is_file()
        for row in conn.execute("SELECT path FROM factor_value_batch")
    ):
        return None

    moved = sum(in_table.values())
    note = (
        f"第 11 版遷移:{len(in_table)} 個因子版本共 {moved} 個因子值搬去 Parquet 批次檔"
        "(D-032),factor_value 清空重建。逐個因子版本核對過檔案登記的行數與表內一致、"
        "而且每個批次檔都在登記的落點上,才清。因子、因子版本、實體三張表一個編號都沒有動。"
    )
    with conn:
        conn.execute("DROP TABLE factor_value")
        conn.execute(
            "INSERT OR IGNORE INTO schema_meta (key, value) VALUES (?, ?)",
            (FACTOR_VALUES_TO_FILES_MIGRATION_KEY, note),
        )
    return moved


def connect(path: str) -> sqlite3.Connection:
    """開庫並建表。``path`` 用 ``":memory:"`` 即開一個即用即棄的庫。"""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # 補欄那個遷移要行在建表之前:新版 DDL 有一條索引落在新加的 origin 之上,
    # 欄未補就建不出那條索引(舊庫一開就當場報「no such column」)。
    _migrate_backtest_run_origin(conn)
    # 清空重建那個遷移一樣要行在建表之前:它 DROP 走舊的 factor_value,
    # 由跟住那句 DDL 重建一張空表(連索引與兩個 trigger)。
    _migrate_factor_values_to_files(conn)
    conn.executescript(ddl())
    _migrate_param_set_cadence(conn)
    # 補欄那個不必行在建表之前:兩格都可以留空,而且沒有索引落在它們身上,
    # 所以 DDL 的 IF NOT EXISTS 先行一步也不會撞板。
    _migrate_snapshot_fetch_alerts(conn)
    # 同一個道理:可執行時點可以留空,亦沒有索引落在它身上,所以補欄行在建表之後。
    _migrate_factor_value_executable_time(conn)
    # 舊庫重開時 DDL 會自動補建新表,故版本印記亦要跟上——否則庫身已是新版、
    # 印記仍寫舊版,下一個人會照印記去猜錶內有什麼表。
    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn
