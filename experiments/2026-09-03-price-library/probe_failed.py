"""KARST-171:三個失敗代號與 70 個 partial 段的身分。唯讀。"""

import pandas as pd

ROOT = r"C:\projects\Karst"


def main() -> None:
    man = pd.read_csv(rf"{ROOT}\data\prices\daily\manifest.csv", dtype={"entity_id": str})
    ent = pd.read_parquet(rf"{ROOT}\data\universe\entities.parquet")[
        ["entity_id", "name", "exchange", "is_smallcap"]
    ]
    m = man.merge(ent, on="entity_id", how="left")
    print("=== fail ===")
    print(m[m["status"] == "fail"][["ticker", "entity_id", "name", "exchange", "is_smallcap"]].to_string())
    p = m[m["status"] == "partial"]
    print("=== partial:", len(p), "段;尾段落後日數分佈 ===")
    print(p["tail_gap_days"].describe(percentiles=[0.25, 0.5, 0.75, 0.9]).to_string())
    print(p[["ticker", "name", "last_date", "tail_gap_days", "is_smallcap"]]
          .sort_values("tail_gap_days", ascending=False).head(15).to_string())
    print("partial 之中屬小型股名單的:", int(p["is_smallcap"].fillna(False).sum()))


if __name__ == "__main__":
    main()
