"""把測試寫進生產庫的那一次正式運行除名(KARST-093 第二件)。

## 為什麼要跑這一支

``tests/test_web_jobs.py`` 驗的是「畫面上按重跑」,而重跑走的正是**正式路徑**:
經唯一入口登記一版新參數集、跑引擎、落一次 ``origin='formal'`` 的運行。以前那個
檔的讀取層直接打倉根那個生產庫,於是**每跑一次測試,生產庫就多一條正式運行**,
而那一條與人手跑出來的一模一樣,事後分不出來。

KARST-087 收工時見到正式運行由 12 條變成 13 條,並在票上寫明多出來的是哪一條:

    「六個 test_web*.py 直接對倉根那個生產庫 karst.sqlite 跑,其中
      test_web_jobs.py 每跑一次就在生產庫多寫一條正式運行(這一次多了
      run-47479e5b36fed94a)」

所以要除名的是**哪一條並不用估**——上一張票當日就記下了編號。本支只是把那句話
落實到庫身上。

## 佐證(除名之前另行查過,兩邊對得上)

庫內 13 條正式運行,逐條join 返 param_set 的簽章登記之後:

    run-47479e5b36fed94a  2026-08-29T21:12:31  參數集 8326(示例-KARST-028 v9)
                          參數集由 karst-web 於 2026-08-29T21:12:23 寫入

「karst-web」是網頁殼那條重跑路徑的寫入者名;它比運行本身早 8 秒寫入,正是
「登記一版新參數集 → 跑引擎 → 落運行」那個次序。而同日 21:04 KARST-087 那個
代理正在跑測試(gateway_write 內 writer='KARST-087-agent' 的一批,時間戳
2026-08-29T21:04:08)。時序、寫入者、參數集版本鏈三邊指同一件事。

## 做法:加一列,不是刪一列

``backtest_run`` 身上有一道 BEFORE DELETE 閘,寫明「運行登記不可刪,追溯要指得
回」。所以除名照 ``data_snapshot_retraction``(KARST-084)那一套:落一列
``backtest_run_retraction``,經唯一入口蓋簽章。除名之後 ``list_runs`` 與
``count_runs`` 略過它(正式運行計數回到 12),``get_run`` 照樣讀得到,那次運行的
淨值與交易 parquet 一個字不動——它確實跑過,帳上不可以當它沒發生過。

## 怎樣跑

    PYTHONUTF8=1 python experiments/2026-08-30-測試污染運行除名/除名.py

只跑得一次:同一次運行除名兩次會被 ``trg_run_retraction_no_update`` 擋下。
"""

from __future__ import annotations

from pathlib import Path

from karst.gateway import Gateway
from karst.store import FORMAL_RUN

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "karst.sqlite"

#: 要除名的那一次。編號由 KARST-087 票上留言直接抄下來,不是這裡估出來的。
POLLUTED_RUN_ID = "run-47479e5b36fed94a"

WRITER = "KARST-093-agent"
REASON = (
    "測試污染:tests/test_web_jobs.py 對生產庫跑,經正式路徑寫入的運行,"
    "不是人手跑的成績(KARST-087 觀察、KARST-093 收拾;"
    "同票已把該批測試接去臨時庫,不會再有下一條)"
)


def main() -> None:
    with Gateway.open(str(DB_PATH), writer=WRITER) as gateway:
        store = gateway.store

        before = store.count_runs(origin=FORMAL_RUN)
        print(f"除名前:正式運行 {before} 條")

        record = store.get_run(POLLUTED_RUN_ID)  # 查無此運行即拋 NotFound
        print(
            f"要除名的:{record.run_id}\n"
            f"  策略   {record.strategy_name}\n"
            f"  參數集 {record.param_set_name} v{record.param_set_version_no}\n"
            f"  期間   {record.period_start} 至 {record.period_end}\n"
            f"  快照   {record.snapshot_id}\n"
            f"  引擎   {record.engine_name} {record.engine_version}"
        )

        retraction = gateway.retract_run(POLLUTED_RUN_ID, reason=REASON)
        print(f"已除名,並蓋上 {retraction.retracted_by} 的簽章({retraction.retracted_at})")

        after = store.count_runs(origin=FORMAL_RUN)
        print(f"除名後:正式運行 {after} 條")

        # 除名之後仍然查得回:追溯指得回,才算「加一列」而不是「抹走一件事」
        still = store.get_run(POLLUTED_RUN_ID)
        print(f"直取仍然讀得到:{still.run_id}")

        findings = gateway.verify()
        print(f"全庫核對:{'清白' if not findings else f'揪到 {len(findings)} 處'}")
        for finding in findings:
            print(f"  {finding}")


if __name__ == "__main__":
    main()
