"""KARST-171 步驟三:把 data/prices/_parts/ 的逐批檔合併成單一價格庫。

輸出:
  data/prices/daily/part_NN.parquet   16 個分片,按 entity_id 尾數分,長表
  data/prices/daily/manifest.csv      每個代號時段一行
  data/prices/daily/failed.csv        status = fail 的代號時段

同實體多代號重疊的處置(同實體別名閘,照 KARST-084 的規則形):
  同一實體的兩個代號時段若日期區間相交,只有一條可以入實體序列(series_role=primary),
  其餘標 alias。優先次序:valid_to 空白(仍然生效)→ 真實日線較多 → 代號字母序。
  不重疊的多段(例如改名 FISV → FI)全部是 primary,自然接成一條時間序列。
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(r"C:\projects\Karst")
PARTS = ROOT / "data" / "prices" / "_parts"
OUT = ROOT / "data" / "prices" / "daily"
NSHARD = 16
SOURCE = "yfinance(auto_adjust=False, actions=False)"

# status 判定門檻(寫在 README,是定義不是可調參數)
# 只用尾段判 partial。頭段(head_gap_days)刻意不入 status:valid_from 是「首次申報日」
# 的代理而不是上市日,借殼上市與早年申報的公司頭段必然大幅落後,那是 v0 日期口徑的性質,
# 不是抓取失敗。head_gap_days 照樣逐段記在 manifest 供讀取方自行判斷。
TAIL_TOL_DAYS = 45   # 尾日比 valid_to 早超過這麼多日 = 缺尾


def build_manifest() -> pd.DataFrame:
    recs = []
    for js in sorted(PARTS.glob("batch_*.json")):
        fetched = datetime.fromtimestamp(js.stat().st_mtime, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
        for s in json.loads(js.read_text(encoding="utf-8")):
            s = dict(s)
            s["batch"] = js.stem
            s["fetchedAt"] = fetched
            recs.append(s)
    m = pd.DataFrame(recs)
    vf = pd.to_datetime(m["valid_from"])
    vt = pd.to_datetime(m["valid_to"])
    fd = pd.to_datetime(m["first_date"].replace("", pd.NaT))
    ld = pd.to_datetime(m["last_date"].replace("", pd.NaT))
    m["head_gap_days"] = (fd - vf).dt.days
    m["tail_gap_days"] = (vt - ld).dt.days
    partial = (m["rows"] > 0) & (m["tail_gap_days"] > TAIL_TOL_DAYS)
    m.loc[partial, "status"] = "partial"
    return m


def assign_series_role(m: pd.DataFrame) -> pd.DataFrame:
    m = m.copy()
    m["series_role"] = "primary"
    m["alias_reason"] = ""
    for eid, grp in m[m["rows"] > 0].groupby("entity_id"):
        if len(grp) == 1:
            continue
        order = grp.assign(
            _open=(grp["valid_to"] == grp["valid_to"].max()).astype(int),
        ).sort_values(["_open", "rows", "ticker"], ascending=[False, False, True])
        accepted: list[tuple[pd.Timestamp, pd.Timestamp, str]] = []
        for r in order.itertuples():
            a, b = pd.Timestamp(r.valid_from), pd.Timestamp(r.valid_to)
            clash = next((t for t in accepted if not (b < t[0] or a > t[1])), None)
            if clash is None:
                accepted.append((a, b, r.ticker))
            else:
                m.loc[r.Index, "series_role"] = "alias"
                m.loc[r.Index, "alias_reason"] = f"與同實體 {clash[2]} 的時段相交,別名閘判 alias"
    return m


def write_shards(m: pd.DataFrame) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("part_*.parquet"):
        old.unlink()
    role = {(r.entity_id, r.ticker): r.series_role for r in m.itertuples()}
    fetched = {(r.entity_id, r.ticker): r.fetchedAt for r in m.itertuples()}
    schema = pa.schema(
        [
            ("entity_id", pa.string()),
            ("ticker", pa.string()),
            ("date", pa.date32()),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("adj_close", pa.float64()),
            ("volume", pa.float64()),
            ("series_role", pa.string()),
            ("source", pa.string()),
            ("fetchedAt", pa.string()),
        ]
    )
    writers = {
        s: pq.ParquetWriter(OUT / f"part_{s:02d}.parquet", schema, compression="zstd")
        for s in range(NSHARD)
    }
    total = 0
    for f in sorted(PARTS.glob("batch_*.parquet")):
        df = pd.read_parquet(f)
        keys = list(zip(df["entity_id"], df["ticker"]))
        df["series_role"] = [role.get(k, "primary") for k in keys]
        df["source"] = SOURCE
        df["fetchedAt"] = [fetched.get(k, "") for k in keys]
        df["shard"] = df["entity_id"].str[-2:].astype(int) % NSHARD
        for s, sub in df.groupby("shard"):
            writers[s].write_table(
                pa.Table.from_pandas(sub.drop(columns=["shard"]), schema=schema, preserve_index=False)
            )
        total += len(df)
    for w in writers.values():
        w.close()
    files = {}
    for p in sorted(OUT.glob("part_*.parquet")):
        b = p.read_bytes()
        files[p.name] = {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
    return {"rows": total, "files": files}


def main() -> None:
    m = build_manifest()
    m = assign_series_role(m)
    cols = [
        "entity_id", "ticker", "valid_from", "valid_to", "rows", "first_date", "last_date",
        "status", "error", "series_role", "alias_reason", "head_gap_days", "tail_gap_days",
        "attempt", "batch", "fetchedAt",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    m[cols].to_csv(OUT / "manifest.csv", index=False, encoding="utf-8")
    failed = m[m["status"] == "fail"][
        ["entity_id", "ticker", "valid_from", "valid_to", "error", "attempt", "batch"]
    ]
    failed.to_csv(OUT / "failed.csv", index=False, encoding="utf-8")
    stats = write_shards(m)
    summary = {
        "periods": int(len(m)),
        "status_counts": m["status"].value_counts().to_dict(),
        "series_role_counts": m["series_role"].value_counts().to_dict(),
        "entities_with_prices": int(m.loc[m["rows"] > 0, "entity_id"].nunique()),
        "total_rows": stats["rows"],
        "shard_files": stats["files"],
    }
    (Path(__file__).parent / "out" / "consolidate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "shard_files"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
