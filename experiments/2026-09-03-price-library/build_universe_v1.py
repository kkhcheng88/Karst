"""KARST-171 步驟一:由 universe_smallcap_v0.csv 出 v1(剔 SIC 6221 信託型 ETP)。

v0 的規則已凍結,v1 只加一條剔除規則 E5(SIC 6221),其餘欄位、其餘實體一律不動。
唯讀讀入,只寫 data/universe/universe_smallcap_v1.csv 與 v1_manifest.json。
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
UNI = ROOT / "data" / "universe"


def main() -> None:
    v0 = pd.read_csv(UNI / "universe_smallcap_v0.csv", dtype=str)
    ent = pd.read_parquet(UNI / "entities.parquet")

    # SIC 6221 = 商品合約經紀商;信託型 ETP(黃金/白銀/石油/加密)以此登記。
    # 人手核例外:三家 SIC 6221 之下的營運公司,逐家核過 submissions 的 entityType 與申報種類。
    MANUAL_KEEP = {
        "0000862861": "AI Financial Corp:entityType=operating,交 10-Q 91 份、DEF 14A 30 份,是營運公司不是信託",
        "0002070542": "AIB Data Centers Inc.:entityType=operating,2025 年上市的數據中心營運商",
        "0002143673": "Uranium Royalty Corp.:entityType=operating,鈾權利金公司,交 10-K/A 與 S-8",
    }
    sic = v0["sic"].fillna("")
    drop_mask = (sic == "6221") & (~v0["entity_id"].isin(MANUAL_KEEP))
    dropped = v0[drop_mask].copy()
    v1 = v0[~drop_mask].copy()

    v1.to_csv(UNI / "universe_smallcap_v1.csv", index=False, encoding="utf-8")
    dropped[["entity_id", "primary_ticker", "name", "sic", "approx_mcap_usd"]].to_csv(
        Path(__file__).parent / "out" / "v1_dropped_etp.csv", index=False, encoding="utf-8"
    )

    blob = (UNI / "universe_smallcap_v1.csv").read_bytes()
    manifest = {
        "produced_by": "KARST-171",
        "source": "universe_smallcap_v0.csv (KARST-167)",
        "rule_added": "E5:剔 SIC 6221(商品合約經紀商)——信託型 ETP;三家人手核為營運公司者留下",
        "manual_keep": MANUAL_KEEP,
        "v0_rows": int(len(v0)),
        "dropped_rows": int(len(dropped)),
        "v1_rows": int(len(v1)),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob),
    }
    (UNI / "universe_smallcap_v1.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    # 全宇宙(不限小型股)受影響家數,供 RULES.md 記錄
    print("entities SIC6221 total:", int((ent["sic"].fillna("") == "6221").sum()))


if __name__ == "__main__":
    main()
