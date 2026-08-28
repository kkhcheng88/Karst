"""單一定義庫的 sqlite 表結構。

D-026 第 1 條:因子定義、策略、運行登記、實體代號映射存**單一 sqlite 檔**;
行情、基本面、逐字稿等大批數據存 parquet,本庫只登記其快照編號。

四組表:
1. ``entity`` / ``entity_ticker``  實體編號與代號歷史映射(D-026 第 2 條)
2. ``factor`` / ``factor_version`` 因子定義與版本鏈(D-021 第 2、6、9 條)
3. ``factor_value``                日期 × 實體 → 值,雙時間戳(D-021 第 1、3、4 條)
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
10. ``data_snapshot_fetch``        數據快照的抓取登記:抓取時間與抓的是哪一段窗口
                                   (D-026 第 3 條;KARST-034)
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

# 第 2 版加入策略定義、參數集與寫入者簽章三組表(KARST-022);
# 第 3 版加入回測運行登記三組表(KARST-026);
# 第 4 版加入現役設定登記表(KARST-030);
# 第 5 版加入共用風控層的規則定義表與策略引用表(KARST-025);
# 第 6 版加入數據快照的抓取登記附表(KARST-034)。舊庫重開即自動補建;
# 第 7 版把 param_set 的換倉節奏約束改為由引擎那份正本砌出來(KARST-044),
#        舊庫重開時自動重建 param_set(見 ``_migrate_param_set_cadence``);
# 第 8 版在 backtest_run 加「來歷」與「掃描編號」兩格(KARST-054),舊庫重開時
#        自動重建 backtest_run 並回填(見 ``_migrate_backtest_run_origin``)。
SCHEMA_VERSION = 8

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
CREATE TABLE IF NOT EXISTS factor_value (
    factor_version_id INTEGER NOT NULL REFERENCES factor_version(factor_version_id),
    entity_id         INTEGER NOT NULL REFERENCES entity(entity_id),
    event_time        TEXT NOT NULL,
    knowledge_time    TEXT NOT NULL,
    value             REAL NOT NULL,
    snapshot_id       TEXT REFERENCES data_snapshot(snapshot_id),
    PRIMARY KEY (factor_version_id, entity_id, event_time, knowledge_time),
    CHECK (knowledge_time >= event_time)
);

CREATE INDEX IF NOT EXISTS idx_factor_value_asof
    ON factor_value (factor_version_id, entity_id, knowledge_time, event_time);

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
CREATE TABLE IF NOT EXISTS data_snapshot_fetch (
    snapshot_id  TEXT PRIMARY KEY REFERENCES data_snapshot(snapshot_id),
    fetched_at   TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end   TEXT NOT NULL,
    entity_count INTEGER NOT NULL CHECK (entity_count >= 0),
    row_count    INTEGER NOT NULL CHECK (row_count >= 0),
    trading_days INTEGER NOT NULL CHECK (trading_days >= 0),
    recorded_at  TEXT NOT NULL,
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


def connect(path: str) -> sqlite3.Connection:
    """開庫並建表。``path`` 用 ``":memory:"`` 即開一個即用即棄的庫。"""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # 補欄那個遷移要行在建表之前:新版 DDL 有一條索引落在新加的 origin 之上,
    # 欄未補就建不出那條索引(舊庫一開就當場報「no such column」)。
    _migrate_backtest_run_origin(conn)
    conn.executescript(ddl())
    _migrate_param_set_cadence(conn)
    # 舊庫重開時 DDL 會自動補建新表,故版本印記亦要跟上——否則庫身已是新版、
    # 印記仍寫舊版,下一個人會照印記去猜錶內有什麼表。
    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn
