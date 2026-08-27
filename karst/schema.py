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
"""

from __future__ import annotations

import sqlite3

# 第 2 版加入策略定義、參數集與寫入者簽章三組表(KARST-022);舊庫重開即自動補建。
SCHEMA_VERSION = 2

DDL = """
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
CREATE TABLE IF NOT EXISTS param_set (
    param_set_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_version(strategy_version_id),
    name                TEXT NOT NULL,
    version_no          INTEGER NOT NULL,
    parent_version_id   INTEGER REFERENCES param_set(param_set_id),
    rebalance_cadence   TEXT NOT NULL CHECK (rebalance_cadence IN ('daily', 'monthly', 'quarterly')),
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
"""


def connect(path: str) -> sqlite3.Connection:
    """開庫並建表。``path`` 用 ``":memory:"`` 即開一個即用即棄的庫。"""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO NOTHING",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn
