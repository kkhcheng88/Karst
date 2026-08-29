"""``karst`` 命令:唯一入口的門面。

一句話用法(PowerShell 記得先 ``$env:PYTHONUTF8 = "1"``):

    python -m karst.gateway --store karst.sqlite factor register ^
        --name "動量·12-1 月" --scale cardinal ^
        --formula "close[-21] / close[-252] - 1" --input-data-version 2026-08-27-a1b2c3d4e5f6

    python -m karst.gateway strategy register --name 趨勢波段 --type technical ^
        --factor "動量·12-1 月" --param-set 現役 --cadence monthly ^
        --set breakout_window=50 --set stop_atr=2.0

    python -m karst.gateway params activate --strategy 趨勢波段 --name 現役 --note 換季調整

    python -m karst.gateway risk register
    python -m karst.gateway risk refs

    python -m karst.gateway data snapshot --ticker SPY --ticker QQQ ^
        --start 2024-01-02 --end 2024-01-31

    python -m karst.gateway data list

    python -m karst.gateway factor ingest-alpha158 --snapshot 2026-08-28-a508d635a5fa

    python -m karst.gateway verify

回傳碼:0 寫得入/核對清白;1 合約拒收或查不到;2 命令用法錯(argparse);
3 核對揪到不合格(繞過唯一入口寫入、落庫後被改、第二影像)。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from ..errors import KarstError
from ..store import REBALANCE_CADENCES, STRATEGY_TYPES, check_param_set
from .service import (
    SOURCE_KINDS,
    Gateway,
    build_procedure,
    build_source,
    default_store_path,
    resolve_universe,
)

EXIT_OK = 0
EXIT_REJECTED = 1
EXIT_NOT_CLEAN = 3

SCALE_LABELS = {"cardinal": "基數", "ordinal": "序數", "boolean": "是非"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="karst",
        description="Karst 唯一入口:策略定義、參數集、因子定義一律經這道門入庫。",
    )
    parser.add_argument(
        "--store",
        default=None,
        help=f"單一定義庫的路徑(預設:環境變數 KARST_STORE,再預設 {default_store_path()})",
    )
    parser.add_argument("--writer", default=None, help="寫入者署名(預設:環境變數 KARST_WRITER 或本機登入名)")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="開庫建表,並備妥簽章鑰匙")

    factor = commands.add_parser("factor", help="因子定義")
    factor_commands = factor.add_subparsers(dest="subcommand", required=True)
    for verb, helptext in (("register", "登記新因子的第一版"), ("new-version", "為既有因子出新版")):
        sub = factor_commands.add_parser(verb, help=helptext)
        sub.add_argument("--name", required=True, help="因子名稱,寫成「族名·具體定義」")
        sub.add_argument("--scale", default=None, choices=sorted(SCALE_LABELS), help="刻度型")
        sub.add_argument("--formula", default=None, help="公式派:公式")
        sub.add_argument("--input-data-version", default=None, help="公式派:輸入數據版本")
        sub.add_argument("--material", default=None, help="數值派:材料")
        sub.add_argument("--judge-version", default=None, help="數值派:判官版本")
        sub.add_argument("--description", default=None, help="一句說明")
    factor_show = factor_commands.add_parser("show", help="看某因子的某一版連版本鏈")
    factor_show.add_argument("--name", required=True)
    factor_show.add_argument("--version", type=int, default=None, help="留空取最新版")

    factor_values = factor_commands.add_parser(
        "write-values", help="經同一道門寫因子值(每列要有三個時點)"
    )
    factor_values.add_argument("--name", required=True)
    factor_values.add_argument("--version", type=int, default=None, help="留空寫入最新版")
    factor_values.add_argument(
        "--from-json", dest="from_json", required=True,
        help="JSON 檔:一個 list,每項 {entity_id, event_time, knowledge_time, "
             "executable_time, value};可執行時點必給,沒有下一根 K 線就寫 null",
    )
    factor_values.add_argument("--snapshot-id", dest="snapshot_id", default=None,
                               help="這批值出自哪個數據快照(追溯到批次)")

    # Alpha158 一句入庫(KARST-064):158 條逐條登記因子版本 + 批量寫因子值。
    # 走的是上面那兩道命令同一條路,只是不必逐條打 158 次。
    alpha158 = factor_commands.add_parser(
        "ingest-alpha158",
        help="把一個價格快照上的 Alpha158 全部 158 條登記並入庫(三個時點照 D-021 合約)",
    )
    alpha158.add_argument("--snapshot", required=True, help="要算哪一個價格快照(無預設)")
    alpha158.add_argument("--root", default=None, help="快照快取根(預設 data/snapshots)")
    alpha158.add_argument(
        "--factor-root", dest="factor_root", default=None,
        help="因子值批次檔的根(預設 data/factors)",
    )

    # 因子預測力(KARST-066):逐日 Spearman IC + 滾動 ICIR,唯一入口輸出成表。
    ic = factor_commands.add_parser(
        "ic", help="逐因子逐日 Spearman IC 與滾動 ICIR(回報起點=可執行時點開價)",
    )
    ic.add_argument("--snapshot", required=True, help="要對哪一個價格快照跑(無預設)")
    ic.add_argument("--factor", dest="factors", action="append", required=True,
                    help="因子引用「名稱」或「名稱@版本號」,可重複給;至少一條")
    ic.add_argument("--horizon", type=int, required=True, help="持有期交易日數,無預設")
    ic.add_argument("--window", type=int, required=True, help="滾動 ICIR 的窗口交易日數,無預設")
    ic.add_argument("--root", default=None, help="價格快照快取根(預設 data/snapshots)")
    ic.add_argument("--factor-root", dest="factor_root", default=None,
                    help="因子值批次檔的根(預設 data/factors)")

    strategy = commands.add_parser("strategy", help="策略定義")
    strategy_commands = strategy.add_subparsers(dest="subcommand", required=True)
    register = strategy_commands.add_parser("register", help="登記新策略的第一版(連第一個參數集)")
    register.add_argument("--name", required=True, help="策略名稱")
    register.add_argument("--type", dest="strategy_type", default=None, help=f"策略類型:{'、'.join(STRATEGY_TYPES)}")
    register.add_argument("--factor", dest="factors", action="append", default=[],
                          help="引用因子「名稱」或「名稱@版本號」;可重複給")
    register.add_argument("--param-set", dest="param_set", default=None, help="第一個參數集的名稱")
    register.add_argument("--cadence", default=None, help=f"換倉節奏:{'、'.join(REBALANCE_CADENCES)};無預設值")
    register.add_argument("--set", dest="params", action="append", default=[],
                          metavar="鍵=值", help="參數,可重複給;無預設值,要用的一律寫明")
    register.add_argument("--description", default=None)

    new_version = strategy_commands.add_parser("new-version", help="為既有策略出新版(類型不可改)")
    new_version.add_argument("--name", required=True)
    new_version.add_argument("--factor", dest="factors", action="append", default=[])
    new_version.add_argument("--description", default=None)

    strategy_show = strategy_commands.add_parser("show", help="看某策略的某一版連引用因子與參數集")
    strategy_show.add_argument("--name", required=True)
    strategy_show.add_argument("--version", type=int, default=None, help="留空取最新版")

    params = commands.add_parser("params", help="參數集")
    params_commands = params.add_subparsers(dest="subcommand", required=True)
    params_add = params_commands.add_parser("add", help="為某策略版本加一個參數集(同名即出新版)")
    params_add.add_argument("--strategy", required=True, help="策略名稱,可寫「名稱@版本號」")
    params_add.add_argument("--name", required=True, help="參數集名稱")
    params_add.add_argument("--cadence", default=None, help="換倉節奏;無預設值")
    params_add.add_argument("--set", dest="params", action="append", default=[], metavar="鍵=值")
    params_show = params_commands.add_parser("show", help="看某策略版本的參數集")
    params_show.add_argument("--strategy", required=True)
    params_show.add_argument("--name", default=None, help="留空即列出全部參數集")
    params_activate = params_commands.add_parser(
        "activate", help="指定某策略的現役設定(釘死參數集的某一版),印出生效序號"
    )
    params_activate.add_argument("--strategy", required=True, help="策略名稱,可寫「名稱@版本號」")
    params_activate.add_argument("--name", required=True, help="參數集名稱")
    params_activate.add_argument("--set-version", dest="set_version", type=int, default=None,
                                 help="參數集版本號,留空即最新版")
    params_activate.add_argument("--note", default=None, help="一句講明為什麼換")

    risk = commands.add_parser("risk", help="共用風控層:三條規則的正本與策略引用")
    risk_commands = risk.add_subparsers(dest="subcommand", required=True)
    risk_commands.add_parser(
        "register", help="把共用風控層三條規則登記入庫(重覆跑回同一批,不會多出第二份)"
    )
    risk_commands.add_parser("list", help="列三條共用風控規則")
    risk_refs = risk_commands.add_parser("refs", help="列各策略引用了哪幾條風控規則")
    risk_refs.add_argument("--strategy", default=None, help="策略名稱,留空即全部策略")
    risk_attach = risk_commands.add_parser("attach", help="記下某策略版本引用哪幾條風控規則")
    risk_attach.add_argument("--strategy", required=True, help="策略名稱,可寫「名稱@版本號」")
    risk_attach.add_argument("--rule", dest="rules", action="append", default=[],
                             metavar="規則程式名", help="可重複給,例如 --rule per_trade_risk")

    data = commands.add_parser("data", help="數據快照")
    data_commands = data.add_subparsers(dest="subcommand", required=True)
    take = data_commands.add_parser(
        "snapshot", help="一句命令抓日線、凍成快照、登記編號並印出來"
    )
    take.add_argument("--ticker", dest="tickers", action="append", default=[],
                      help="宇宙代號,可重複給;留空即起步宇宙名單全份")
    take.add_argument("--start", required=True, help="窗口起(含頭)")
    take.add_argument("--end", required=True, help="窗口訖(含尾)")
    take.add_argument("--source", default="yfinance", choices=SOURCE_KINDS,
                      help="來源適配器:yfinance 抓真數;csv 由檔案重放同一批數")
    take.add_argument("--bars", default=None, help="來源 csv 時:日線檔路徑")
    take.add_argument("--anchors", default=None,
                      help="帶生效期的代號→CIK 對照表路徑(KARST-082);"
                           "留空即問 SEC「代號今日屬誰」,歷史成分不宜")
    take.add_argument("--root", default=None, help="快取根(預設 data/snapshots)")
    take.add_argument("--taken-on", dest="taken_on", default=None,
                      help="快照日期,留空即抓取當日")
    # 呼叫方交來的註記(KARST-065)。管線只講得出自己見到的事;「這批數據少了哪些
    # 代號、為什麼少」只有發起那個人知道,沒有這一格就只能靠人記得去翻另一份檔。
    take.add_argument("--note", dest="notes", action="append", default=[],
                      help="寫入快照說明檔的一句註記,可重複給(不入內容雜湊,不會改變快照編號)")
    # 快照除名(KARST-084)。除的是登記,不是檔案:快照目錄與 parquet 一個字都不動,
    # 只是登記冊由此不再把它當作可回測的數據。除名是加一列,不是刪一列。
    retract = data_commands.add_parser(
        "retract-snapshot",
        help="把一個快照由登記冊除名(檔案照留、追溯照指得回),經唯一入口留簽章",
    )
    retract.add_argument("--snapshot", required=True, help="要除名的快照編號")
    retract.add_argument("--reason", required=True,
                         help="為什麼除名,一句講清楚;這一句會落登記冊,日後查得回")
    retract.add_argument("--superseded-by", dest="superseded_by", default=None,
                         help="被哪個快照取代;沒有取代者就不給這一格")
    macro = data_commands.add_parser(
        "macro-snapshot",
        help="抓宏觀序列、對齊指定價格快照的主日曆、凍成快照並登記編號",
    )
    macro.add_argument("--price-snapshot", dest="price_snapshot", required=True,
                       help="要對齊哪一個價格快照的主日曆(窗口由該日曆讀回,不另給)")
    macro.add_argument("--series", dest="series", action="append", default=[],
                       help="宏觀序列代號,可重複給;留空即名冊全份十四條")
    macro.add_argument("--root", default=None, help="宏觀快取根(預設 data/macro_snapshots)")
    macro.add_argument("--price-root", dest="price_root", default=None,
                       help="價格快取根(預設 data/snapshots)")
    macro.add_argument("--taken-on", dest="taken_on", default=None,
                       help="快照日期,留空即抓取當日")
    # 齊全度門檻(KARST-061)。**兩個都是必給,兩個都沒有預設值**:「幾多日算停更」
    # 不是數據的性質,是用戶對這條訊號的容忍度,程式代揀一個數就等於把一個沒有人
    # 裁決過的判斷寫進了每一次凍結。
    macro.add_argument("--max-stale-days", dest="max_stale_days", type=int, required=True,
                       help="齊全度門檻:一條序列的尾段容許落後主日曆幾多個交易日(0 = 必須供到尾日)")
    macro.add_argument("--max-missing-ratio", dest="max_missing_ratio", type=float, required=True,
                       help="齊全度門檻:整段窗口留空日數佔主日曆的比例上限,0.01 即 1%%")
    # 快照補簽(KARST-087)。治理清單收入數據快照登記與抓取登記之後,收窄之前落庫那批
    # 舊列一個簽章都沒有;這道命令經唯一入口替它們補簽,逐列留痕(誰、幾時、為什麼)。
    countersign = data_commands.add_parser(
        "countersign-snapshots",
        help="替治理清單收窄之前落庫、無簽章的快照登記補簽,逐列留痕(誰、幾時、為什麼)",
    )
    countersign.add_argument(
        "--reason", required=True,
        help="為什麼要補簽,一句講清楚;這一句逐列落補簽冊,日後分得出原簽與補簽",
    )
    data_commands.add_parser("list", help="列庫內全部數據快照")
    # 宇宙名單登記(KARST-065):名單住在 karst/data/universe.py,這道命令只是**列**它。
    # 有這一句,「登記上有什麼代號、成分期由哪日到哪日、名單哪裡來」不必開原始碼看。
    universe = data_commands.add_parser(
        "universe", help="列宇宙名單登記:有哪幾份名單、每份的代號與成分期"
    )
    universe.add_argument(
        "--name", default=None,
        help="名單的名(starter / factor-etf / sp500-historical);留空即列全部名單的摘要",
    )

    where = commands.add_parser("where", help="講出一項定義的唯一落點,並掃全庫查有沒有第二份影像")
    where.add_argument("--kind", required=True, choices=("factor", "strategy"))
    where.add_argument("--name", required=True)

    verify = commands.add_parser(
        "verify", help="核對全庫:揪出繞過唯一入口的寫入與落庫後的改動,連因子值檔的雜湊"
    )
    verify.add_argument(
        "--factor-root", dest="factor_root", default=None,
        help="因子值批次檔的根(預設 data/factors);檔案落點由登記那一列自己講,"
             "這一格只在庫與檔搬了家時才用得著",
    )
    return parser


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stream = out or sys.stdout
    try:
        return _dispatch(args, stream)
    except KarstError as error:
        print(f"拒收:{error}", file=stream)
        print("庫內一個字都寫不入。", file=stream)
        return EXIT_REJECTED
    except ValueError as error:
        print(f"拒收:{error}", file=stream)
        return EXIT_REJECTED


def _dispatch(args: argparse.Namespace, out: TextIO) -> int:
    with Gateway.open(args.store, writer=args.writer) as gateway:
        if args.command == "init":
            return _init(gateway, out)
        if args.command == "factor":
            return _factor(args, gateway, out)
        if args.command == "strategy":
            return _strategy(args, gateway, out)
        if args.command == "params":
            return _params(args, gateway, out)
        if args.command == "risk":
            return _risk(args, gateway, out)
        if args.command == "data":
            return _data(args, gateway, out)
        if args.command == "where":
            return _where(args, gateway, out)
        if args.command == "verify":
            return _verify(args, gateway, out)
    raise AssertionError(f"未知命令 {args.command!r}")  # pragma: no cover - argparse 已擋


# ----------------------------------------------------------------------
# 各命令
# ----------------------------------------------------------------------


def _init(gateway: Gateway, out: TextIO) -> int:
    from .ledger import key_file_for

    print(f"單一定義庫:{gateway.path}", file=out)
    print(f"  簽章鑰匙  {key_file_for(gateway.path)}(住在庫檔以外)", file=out)
    print(f"  寫入者    {gateway.writer}", file=out)
    print("  全部定義自此只有這一條入庫的路。", file=out)
    return EXIT_OK


def _factor(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    if args.subcommand == "show":
        chain = gateway.store.factor_version_chain(args.name, args.version)
        head = chain[0]
        print(f"因子「{head.name}」(族:{head.family})", file=out)
        _print_factor_version(head, out)
        print(f"  版本鏈    {' ← '.join(f'第 {v.version_no} 版' for v in chain)}", file=out)
        return EXIT_OK

    if args.subcommand == "write-values":
        rows = _read_json_rows(args.from_json)
        written = gateway.write_factor_values(
            args.name, rows, version_no=args.version, snapshot_id=args.snapshot_id
        )
        version = gateway.store.get_factor_version(args.name, args.version)
        print(f"已寫入因子「{version.name}」第 {version.version_no} 版 {written} 個值", file=out)
        if args.snapshot_id:
            print(f"  數據快照  {args.snapshot_id}", file=out)
        print(
            "  每個值都帶事件時間、知情時間與可執行時點;知情早過事件、"
            "或可執行不在知情之後,即前視,寫不入。",
            file=out,
        )
        return EXIT_OK

    if args.subcommand == "ingest-alpha158":
        return _factor_ingest_alpha158(args, gateway, out)

    if args.subcommand == "ic":
        return _factor_ic(args, gateway, out)

    procedure = build_procedure(
        formula=args.formula,
        input_data_version=args.input_data_version,
        material=args.material,
        judge_version=args.judge_version,
    )
    write = gateway.register_factor if args.subcommand == "register" else gateway.new_factor_version
    version, receipt = write(
        args.name, scale_kind=args.scale, procedure=procedure, description=args.description
    )
    print(f"已登記因子「{version.name}」", file=out)
    _print_factor_version(version, out)
    _print_receipt(receipt, gateway, "factor", version.name, out)
    return EXIT_OK


def _factor_ingest_alpha158(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    """Alpha158 一句入庫(KARST-064)。做法住在 ``karst.gateway.alpha158``,本檔只印。"""
    from .alpha158 import ALPHA158_FORMULA_SOURCE, ALPHA158_PROCEDURE_VERSION

    report = gateway.ingest_alpha158(
        snapshot_id=args.snapshot, root=args.root, factor_root=args.factor_root
    )
    print(f"已入庫 Alpha158 全部 {report.factor_count} 條因子", file=out)
    print(f"  數據快照  {report.snapshot_id}", file=out)
    print(
        f"  範圍      {report.entity_count} 個實體 × {report.trading_days} 個交易日"
        f"({report.first_event_date}~{report.last_event_date})",
        file=out,
    )
    print(
        f"  因子版本  新登記 {report.registered} 條、沿用 {report.reused} 條、"
        f"出新版 {report.new_versions} 條",
        file=out,
    )
    print(f"  產生程序  {ALPHA158_PROCEDURE_VERSION};公式出處 {ALPHA158_FORMULA_SOURCE}", file=out)
    print(
        f"  寫入      {report.written_rows} 個值(本來 {report.possible_rows} 格,"
        f"留空 {report.missing_rows} 格,缺值比例 {report.missing_ratio:.4%})",
        file=out,
    )
    print(
        f"  值的落點  {report.batch_path}({report.file_bytes / 1_048_576:.1f} MB,"
        f"批次「{report.batch_key}」);定義庫只留登記與雜湊 {report.content_hash[:12]}"
        "(D-032)",
        file=out,
    )
    print(
        "  三個時點  事件=該根 K 線那日開頭、知情=該日收工、"
        "可執行=下一根可交易 K 線那日開市(D-021 第 3 條)",
        file=out,
    )
    if report.last_executable_date is None:
        print(
            f"  可執行    最後一日 {report.last_event_date} 之後這個快照沒有下一根 K 線,"
            f"該日 {report.not_executable_rows} 個值知得到、成交不到,可執行時點留空",
            file=out,
        )
    else:
        print(f"  可執行    最後一日的可執行時點 {report.last_executable_date}", file=out)
    print(
        "  留空不補  滾動窗口未滿而算不出值的日子檔內沒有那一列,不前值填補、不填零"
        "(D-021 第 4 條)",
        file=out,
    )
    print(f"  用時      {report.seconds:.1f} 秒", file=out)
    return EXIT_OK


def _factor_ic(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    """因子預測力:逐因子逐日 Spearman IC + 滾動 ICIR,唯一入口輸出成表(KARST-066)。

    對齊、IC、ICIR 的算法住在 ``karst.factorpredict``,本檔只讀值、印表。取值經
    ``karst.factorvalues.FactorValueReader`` ——與選股引擎同一條路(KARST-088),
    表與因子值批次兩個住處一齊看。
    """
    from ..data import read_price_frame
    from ..factorpredict import daily_ic, rolling_icir, summarize_ic
    from ..factorvalues import FactorValueReader

    store = gateway.factor_values(args.factor_root)
    reader = FactorValueReader(gateway.store, store.root)
    factor_long = reader.history(
        args.factors,
        snapshot_id=args.snapshot,
        as_of=None,
        start=None,
        end=None,
        entity_ids=None,
    )
    price_frame = read_price_frame(gateway.store, args.snapshot, root=args.root)

    from ..factorpredict import align_factor_to_forward_returns

    aligned = align_factor_to_forward_returns(factor_long, price_frame, horizon=args.horizon)
    daily = daily_ic(aligned)
    summary = summarize_ic(daily)
    rolled = rolling_icir(daily, window=args.window)

    version_names = {
        version.factor_version_id: f"{version.name}·第{version.version_no}版"
        for version in (store.resolve(name) for name in args.factors)
    }

    print(
        f"因子預測力:快照 {args.snapshot};持有期 {args.horizon} 個交易日;"
        f"滾動 ICIR 窗口 {args.window} 個交易日",
        file=out,
    )
    print(
        "  持有期量法  第 1 日(可執行時點那根)開價買入,持有到第 N 日(含首日)收價賣出",
        file=out,
    )
    if summary.empty:
        print("  對齊之後一格值都沒有(可執行時點對不上這份快照的日曆,或持有期跨出尾巴)", file=out)
        return EXIT_OK

    print("  全期摘要(IC 均值、標準差、ICIR、樣本日數)", file=out)
    for row in summary.sort_values("factor_version_id").itertuples():
        label = version_names.get(row.factor_version_id, f"factor_version_id={row.factor_version_id}")
        print(
            f"    {label}  IC均值={row.ic_mean:.4f}  IC標準差={row.ic_std:.4f}  "
            f"ICIR={row.icir:.4f}  樣本日數={row.n_days}",
            file=out,
        )

    latest = rolled.dropna(subset=["icir"]).sort_values("date").groupby("factor_version_id").tail(1)
    if not latest.empty:
        print(f"  最新一個滾動窗({args.window} 個交易日)ICIR", file=out)
        for row in latest.sort_values("factor_version_id").itertuples():
            label = version_names.get(row.factor_version_id, f"factor_version_id={row.factor_version_id}")
            print(f"    {label}  {row.date.date()}  滾動ICIR={row.icir:.4f}", file=out)
    return EXIT_OK


def _print_factor_version(version, out: TextIO) -> None:
    parent = "無" if version.parent_version_id is None else f"factor_version_id={version.parent_version_id}"
    scale = f"{version.scale_kind}({SCALE_LABELS.get(version.scale_kind, '')})"
    if version.procedure.kind == "formula":
        procedure = f"公式派 — 公式「{version.procedure.formula}」;輸入數據版本 {version.procedure.input_data_version}"
    else:
        procedure = f"數值派 — 材料「{version.procedure.material}」;判官版本 {version.procedure.judge_version}"
    print(f"  版本      第 {version.version_no} 版(父版本:{parent})", file=out)
    print(f"  刻度型    {scale}", file=out)
    print(f"  產生程序  {procedure}", file=out)
    print(f"  落庫時間  {version.created_at}", file=out)


def _strategy(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    if args.subcommand == "show":
        version = gateway.store.get_strategy_version(args.name, args.version)
        print(f"策略「{version.name}」", file=out)
        _print_strategy_version(version, out)
        for param_set in gateway.store.list_param_sets(args.name, strategy_version_no=args.version):
            _print_param_set(param_set, out)
        return EXIT_OK

    if args.subcommand == "new-version":
        version, receipt = gateway.new_strategy_version(
            args.name, factor_refs=args.factors, description=args.description
        )
        print(f"已為策略「{version.name}」出第 {version.version_no} 版", file=out)
        _print_strategy_version(version, out)
        _print_receipt(receipt, gateway, "strategy", version.name, out)
        return EXIT_OK

    # register:策略連第一個參數集一次過登記——參數集是策略定義的一格,不是後補
    values = _parse_params(args.params)
    set_name = (args.param_set or "").strip()
    if not set_name:
        print("拒收:策略定義最少要有一個參數集,請用 --param-set 命名", file=out)
        return EXIT_REJECTED
    check_param_set(set_name, args.cadence, values)  # 先驗參數集,免得策略寫了參數集才拒收

    version, receipt = gateway.register_strategy(
        args.name,
        strategy_type=args.strategy_type,
        factor_refs=args.factors,
        description=args.description,
    )
    param_set, param_receipt = gateway.register_param_set(
        version.name,
        param_set_name=set_name,
        rebalance_cadence=args.cadence,
        values=values,
        strategy_version_no=version.version_no,
    )
    print(f"已登記策略「{version.name}」", file=out)
    _print_strategy_version(version, out)
    _print_param_set(param_set, out)
    _print_receipt(receipt, gateway, "strategy", version.name, out)
    print(f"  參數集簽章 {'、'.join(param_receipt.signed_rows)}", file=out)
    return EXIT_OK


def _print_strategy_version(version, out: TextIO) -> None:
    parent = (
        "無" if version.parent_version_id is None
        else f"strategy_version_id={version.parent_version_id}"
    )
    print(f"  類型      {version.strategy_type}({STRATEGY_TYPES[version.strategy_type]})", file=out)
    print(f"  版本      第 {version.version_no} 版(父版本:{parent})", file=out)
    for factor in version.factors:
        print(
            f"  引用因子  {factor.name} 第 {factor.version_no} 版"
            f"(factor_version_id={factor.factor_version_id};刻度型 {factor.scale_kind})",
            file=out,
        )
    print(f"  落庫時間  {version.created_at}", file=out)


def _print_param_set(param_set, out: TextIO) -> None:
    cadence = f"{param_set.rebalance_cadence}({REBALANCE_CADENCES[param_set.rebalance_cadence]})"
    body = "、".join(f"{k}={v}" for k, v in param_set.values.items())
    print(f"  參數集    {param_set.name} 第 {param_set.version_no} 版;換倉節奏 {cadence}", file=out)
    print(f"            {body}", file=out)


def _params(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    name, version_no = _split_strategy_ref(args.strategy)
    if args.subcommand == "activate":
        setup, receipt = gateway.designate_active_setup(
            name,
            param_set_name=args.name,
            strategy_version_no=version_no,
            param_set_version_no=args.set_version,
            note=args.note,
        )
        print(f"已指定策略「{setup.strategy_name}」的現役設定", file=out)
        print(f"  生效序號  第 {setup.seq_no} 次指定(seq_no={setup.seq_no})", file=out)
        print(
            f"  參數集    {setup.param_set_name} 第 {setup.param_set_version_no} 版"
            f"(param_set_id={setup.param_set_id});換倉節奏 "
            f"{setup.rebalance_cadence}({REBALANCE_CADENCES[setup.rebalance_cadence]})",
            file=out,
        )
        print(
            f"  策略版本  第 {setup.strategy_version_no} 版"
            f"(strategy_version_id={setup.strategy_version_id})",
            file=out,
        )
        print(f"  指定時間  {setup.designated_at}", file=out)
        if setup.note:
            print(f"  註記      {setup.note}", file=out)
        print(f"  寫入者    {receipt.writer}", file=out)
        print(f"  已蓋簽章  {'、'.join(receipt.signed_rows)}", file=out)
        print("  門面八個數字自此取這一個設定那次運行;舊指定一字不變,換過什麼查得回。", file=out)
        return EXIT_OK

    if args.subcommand == "show":
        if args.name:
            sets = [gateway.store.get_param_set(name, args.name, strategy_version_no=version_no)]
        else:
            sets = gateway.store.list_param_sets(name, strategy_version_no=version_no)
        strategy = gateway.store.get_strategy_version(name, version_no)
        print(f"策略「{strategy.name}」第 {strategy.version_no} 版的參數集", file=out)
        for param_set in sets:
            _print_param_set(param_set, out)
        return EXIT_OK

    param_set, receipt = gateway.register_param_set(
        name,
        param_set_name=args.name,
        rebalance_cadence=args.cadence,
        values=_parse_params(args.params),
        strategy_version_no=version_no,
    )
    print(f"已登記參數集「{param_set.name}」第 {param_set.version_no} 版", file=out)
    _print_param_set(param_set, out)
    print(f"  落庫時間  {param_set.created_at}", file=out)
    print(f"  寫入者    {receipt.writer}", file=out)
    print(f"  已蓋簽章  {'、'.join(receipt.signed_rows)}", file=out)
    return EXIT_OK


def _risk(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    if args.subcommand == "register":
        rules, signed = gateway.register_risk_rules()
        print(f"已登記共用風控規則 {len(rules)} 條(全平台一個正本)", file=out)
        for rule in rules:
            _print_risk_rule(rule, out)
        print(f"  寫入者    {gateway.writer}", file=out)
        print(f"  已蓋簽章  {'、'.join(signed)}", file=out)
        return EXIT_OK

    if args.subcommand == "list":
        rules = gateway.store.list_risk_rules()
        if not rules:
            print("庫內未登記共用風控規則;請先跑 karst risk register。", file=out)
            return EXIT_OK
        print(f"共用風控規則(共 {len(rules)} 條;定義只有一份,取值住在各策略的參數集)", file=out)
        for rule in rules:
            _print_risk_rule(rule, out)
        return EXIT_OK

    if args.subcommand == "attach":
        name, version_no = _split_strategy_ref(args.strategy)
        refs, signed = gateway.attach_risk_rules(name, args.rules, strategy_version_no=version_no)
        print(f"策略「{name}」現引用 {len(refs)} 條共用風控規則", file=out)
        for rule in refs:
            print(f"  引用      {rule.name}({rule.key});取值住在參數集的 {rule.param_key}", file=out)
        print(f"  寫入者    {gateway.writer}", file=out)
        print(f"  已蓋簽章  {'、'.join(signed) if signed else '(無引用,無列可簽)'}", file=out)
        return EXIT_OK

    # refs:列各策略引用了哪幾條
    names = [args.strategy] if args.strategy else gateway.store.list_strategy_names()
    if not names:
        print("庫內一套策略都沒有。", file=out)
        return EXIT_OK
    print("各策略引用的共用風控規則", file=out)
    for name in names:
        strategy_name, version_no = _split_strategy_ref(name)
        version = gateway.store.get_strategy_version(strategy_name, version_no)
        rules = gateway.store.strategy_risk_rules(version.name, strategy_version_no=version.version_no)
        if rules:
            body = "、".join(f"{rule.name}({rule.key})" for rule in rules)
            print(f"  {version.name} 第 {version.version_no} 版  引用 {len(rules)} 條:{body}", file=out)
        else:
            print(
                f"  {version.name} 第 {version.version_no} 版  一條都沒有引用"
                "(不引用不是錯,這套策略照樣跑得)",
                file=out,
            )
    return EXIT_OK


def _print_risk_rule(rule, out: TextIO) -> None:
    print(f"  {rule.name}({rule.key})", file=out)
    print(f"            取值參數 {rule.param_key};{rule.description}", file=out)


def _data(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    if args.subcommand == "list":
        return _data_list(gateway, out)
    if args.subcommand == "retract-snapshot":
        return _data_retract(args, gateway, out)
    if args.subcommand == "countersign-snapshots":
        return _data_countersign(args, gateway, out)
    if args.subcommand == "macro-snapshot":
        return _data_macro(args, gateway, out)
    if args.subcommand == "universe":
        return _data_universe(args, out)

    universe = resolve_universe(args.tickers)
    source = build_source(args.source, bars=args.bars)
    cik_map = None
    anchor_valid_to = None
    if args.anchors:
        # 帶生效期的代號對照(KARST-082)。給了這一份就不再問 SEC「代號今日屬誰」——
        # 那條路正是假設 A-011 崩塌的地方。窗口內同一代號錨到兩個實體即當場拒收;
        # 反方向那一格(兩個代號錨到同一個實體)由凍結管線的同實體別名閘處置
        # (KARST-084),生效訖就是那道閘規則第一關要的材料。
        from ..data.ticker_history import (
            anchor_map_for_window,
            read_anchor_table,
            valid_to_for_window,
        )

        table = read_anchor_table(args.anchors)
        cik_map = anchor_map_for_window(table, start=args.start, end=args.end)
        anchor_valid_to = valid_to_for_window(table, start=args.start, end=args.end)
    snapshot, fetch = gateway.take_snapshot(
        start=args.start,
        end=args.end,
        universe=universe,
        source=source,
        root=args.root,
        taken_on=args.taken_on,
        extra_notes=args.notes,
        cik_map=cik_map,
        anchor_valid_to=anchor_valid_to,
    )
    print(f"已凍結數據快照 {snapshot.snapshot_id}", file=out)
    print(f"  來源      {snapshot.source}", file=out)
    print(f"  抓取時間  {fetch.fetched_at}", file=out)
    print(f"  快照日期  {snapshot.taken_on}", file=out)
    print(
        f"  窗口      {fetch.window}({fetch.trading_days} 個交易日、{fetch.row_count} 列日線)",
        file=out,
    )
    print(
        f"  宇宙      {'、'.join(snapshot.universe)}({fetch.entity_count} 個實體)",
        file=out,
    )
    print(f"  落點      {snapshot.path}", file=out)
    print(f"  內容雜湊  {snapshot.content_hash}", file=out)
    if getattr(snapshot, "reused", False):
        print("  沿用      這批數據早已凍結,沿用原本那個編號,快取根沒有多一份副本", file=out)
    for note in snapshot.notes:
        print(f"  註記      {note}", file=out)
    return EXIT_OK


def _data_retract(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    retraction = gateway.retract_snapshot(
        args.snapshot, reason=args.reason, superseded_by=args.superseded_by
    )
    snapshot = gateway.store.get_snapshot(retraction.snapshot_id)
    print(f"已由登記冊除名 {retraction.snapshot_id}", file=out)
    print(f"  除名時間  {retraction.retracted_at}", file=out)
    print(f"  除名者    {retraction.retracted_by}", file=out)
    print(f"  理由      {retraction.reason}", file=out)
    print(
        f"  被取代    {retraction.superseded_by or '(無取代者;除名了而且沒有替身)'}",
        file=out,
    )
    print(
        f"  檔案      {snapshot.path or '(登記未記落點)'};一個字都沒有動"
        "(D-026 第 3 條:舊快照永不改動)",
        file=out,
    )
    print(
        "  除名之後  karst data list 與畫面選單不再列出它;直取(get_snapshot、"
        "讀說明檔)照樣讀得到,追溯指得回",
        file=out,
    )
    return EXIT_OK


def _data_countersign(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    done = gateway.countersign_snapshots(reason=args.reason)
    if not done:
        print("沒有一列快照登記欠簽章,補簽無事可做。", file=out)
        return EXIT_OK
    print(f"已補簽 {len(done)} 列快照登記", file=out)
    print(f"  補簽者    {gateway.writer}", file=out)
    print(f"  理由      {args.reason}", file=out)
    for item in done:
        print(f"    {item.table}[{item.row_key}]", file=out)
    print(
        "  補簽只擔保「由這一刻起這幾列沒有再被改過」,擔保不了它們當日是經唯一入口寫的"
        "——那件事已經過去。補簽冊逐列留住這個分別。",
        file=out,
    )
    return EXIT_OK


def _data_macro(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    from karst.data import CompletenessThresholds

    thresholds = CompletenessThresholds(
        max_stale_days=args.max_stale_days,
        max_missing_ratio=args.max_missing_ratio,
    )
    snapshot, fetch = gateway.take_macro_snapshot(
        price_snapshot_id=args.price_snapshot,
        thresholds=thresholds,
        root=args.root,
        price_root=args.price_root,
        codes=args.series or None,
        taken_on=args.taken_on,
    )
    print(f"已凍結宏觀快照 {snapshot.snapshot_id}", file=out)
    print(f"  來源      {snapshot.source}", file=out)
    print(f"  抓取時間  {fetch.fetched_at}", file=out)
    print(f"  快照日期  {snapshot.taken_on}", file=out)
    print(
        f"  窗口      {fetch.window}({fetch.trading_days} 個交易日、{fetch.row_count} 列讀數)",
        file=out,
    )
    print(f"  主日曆    {snapshot.calendar_ticker}(對齊價格快照 {args.price_snapshot})", file=out)
    print(f"  序列      {'、'.join(snapshot.series)}({len(snapshot.series)} 條)", file=out)
    print(f"  落點      {snapshot.path}", file=out)
    print(f"  內容雜湊  {snapshot.content_hash}", file=out)
    if getattr(snapshot, "reused", False):
        print("  沿用      這批讀數早已凍結,沿用原本那個編號,快取根沒有多一份副本", file=out)

    # 齊全度核對(KARST-061)。放在註記之上、自成一格:這一格要答的是「有沒有一條
    # 訊號已經靜靜停止講話」,以前那件事要有人去翻說明檔第七節才看得見,而 ^VIX3M
    # 停更 28 個交易日就是這樣無人察覺的(假設 A-008)。
    alerts = tuple(getattr(snapshot, "alerts", ()))
    if alerts:
        print(f"  齊全度    警報:{len(alerts)} 條序列超出門檻({thresholds.describe()})", file=out)
        for alert in alerts:
            print(f"            {alert.message}", file=out)
        print(
            "            尾段短過主日曆 = 那條訊號已經停止講話;"
            "驅動器會每日判「數據不足」退回熱身期權重,而掃描與報告一個錯都不會報",
            file=out,
        )
    else:
        print(
            f"  齊全度    {len(snapshot.series)} 條序列全部合格({thresholds.describe()})",
            file=out,
        )

    for note in snapshot.notes:
        if note.startswith("齊全度"):
            continue  # 上面那一格已經逐條講過,不再重覆一次
        print(f"  註記      {note}", file=out)
    return EXIT_OK


def _data_universe(args: argparse.Namespace, out: TextIO) -> int:
    """列宇宙名單登記(KARST-065)。名單的正本住在 ``karst/data/universe.py``,
    這裡一個字都不另存,只是把它讀出來——登記與預設是兩件事,列出來才看得清。"""
    from karst.data import NAMED_UNIVERSES, universe_listing

    if not args.name:
        print(f"宇宙名單登記(共 {len(NAMED_UNIVERSES)} 份)", file=out)
        for listing in NAMED_UNIVERSES:
            print(f"  {listing.key}  {listing.title}({len(listing.members)} 個代號)", file=out)
            print(f"            {listing.description}", file=out)
            for source in listing.sources:
                print(
                    f"            來源  {source.name}({source.url});"
                    f"覆蓋 {source.coverage};抓取日期 {source.fetched_on}",
                    file=out,
                )
        print("  不指定代號時抓的是 starter 那一份;登記與預設批次是兩件事。", file=out)
        return EXIT_OK

    listing = universe_listing(args.name)
    print(f"{listing.title}({listing.key};{len(listing.members)} 個代號)", file=out)
    print(f"  {listing.description}", file=out)
    for source in listing.sources:
        print(
            f"  來源      {source.name}({source.url});"
            f"覆蓋 {source.coverage};抓取日期 {source.fetched_on}",
            file=out,
        )
    if not listing.membership:
        for member in listing.members:
            print(f"  {member.ticker}  {member.kind}  {member.display_name}", file=out)
        return EXIT_OK

    print(f"  成分期    共 {len(listing.membership)} 段(一個代號可以離開又回來)", file=out)
    print("  代號  加入日期  剔除日期  來源  名稱", file=out)
    for period in listing.membership:
        left = period.left_on or "—(來源記為仍在名單上)"
        line = f"  {period.ticker}  {period.joined_on}  {left}  {period.source}  {period.display_name}"
        print(line, file=out)
        if period.note:
            print(f"        註記 {period.note}", file=out)
    return EXIT_OK


def _data_list(gateway: Gateway, out: TextIO) -> int:
    listings = gateway.list_snapshots()
    if not listings:
        print("庫內一個數據快照都沒有。", file=out)
        return EXIT_OK
    print(f"庫內數據快照(共 {len(listings)} 個):", file=out)
    for listing in listings:
        window = listing.window or f"{listing.taken_on}(未經入口凍結,窗口不詳)"
        fetched = listing.fetched_at or "—(不是經唯一入口凍的,無抓取登記)"
        print(
            f"  {listing.snapshot_id}  {window}  {listing.entity_count} 個實體"
            f"  抓於 {fetched}  來源 {listing.source}",
            file=out,
        )
        # 齊全度那一行只在核對過的快照之下出現(KARST-067)。沒有這一行 = 那份
        # 快照凍結時沒有核對過齊全度(價格快照、或第 9 版之前的舊登記),
        # **不是**「核對過而零警報」——後者會正面印出「全部合格」那一句。
        if listing.alert_count is not None:
            print(
                f"            齊全度  警報 {listing.alert_count} 條・{listing.alert_summary}",
                file=out,
            )
    return EXIT_OK


def _where(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    location = gateway.locate(args.kind, args.name)
    label = "因子" if location.kind == "factor" else "策略"
    print(f"{label}「{location.name}」的唯一落點", file=out)
    print(
        f"  正本      {gateway.path} → {location.table}({location.row_key})",
        file=out,
    )
    print(
        f"  版本      共 {location.version_count} 版,最新第 {location.latest_version_no} 版"
        f"(版本鏈同表,不是另一份定義)",
        file=out,
    )
    print(f"  全庫掃描  這個名字只出現在:{'、'.join(location.occurrences)}", file=out)
    if location.has_second_image:
        print("  第二影像  有,見上;單一定義被破(D-002 第 4 條)", file=out)
        return EXIT_NOT_CLEAN
    print("  第二影像  無;引用它的表只存編號,不存第二份定義", file=out)
    return EXIT_OK


def _verify(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    verdicts = gateway.verify_report(factor_root=args.factor_root)
    batches = gateway.store.list_factor_value_batches()
    print(f"核對單一定義庫:{gateway.path}", file=out)
    if batches:
        values = sum(batch.rows for batch in batches)
        print(
            f"  連同 {len(batches)} 個因子值批次檔共 {values} 個值(D-032:值住檔案,"
            "核對照管內容雜湊)",
            file=out,
        )
    checked = _balance_lines(gateway)
    if checked:
        print(
            f"  連同 {len(checked)} 個數據快照的三數等式(宇宙表代號數 = 實體數 + 剔除數,"
            "KARST-084):",
            file=out,
        )
        for line in checked:
            print(f"    {line}", file=out)

    # 三類分列(KARST-087)。一句「全庫清白」讀不出清白的是什麼:定義髒了是策略的講法
    # 被人改過,因子批次髒了是值檔與登記對不上,快照髒了是取數的源頭被人動過。
    print("  分三類:", file=out)
    for verdict in verdicts:
        print(f"    {verdict.describe()}", file=out)
        for finding in verdict.findings:
            print(f"      - {finding}", file=out)

    findings = [finding for verdict in verdicts for finding in verdict.findings]
    if not findings:
        print("  三類全部清白:受治理的每一列都有唯一入口的寫入者簽章,內容與登記時一字不差;"
              "每個因子值批次檔的內容雜湊亦與登記的一樣;每個讀得到的快照三數都對得上。",
              file=out)
        return EXIT_OK
    print(f"  合共揪到 {len(findings)} 處不合格。", file=out)
    print("  這些內容不會被當作正常定義用落去,請按版本鏈重新經唯一入口登記。", file=out)
    return EXIT_NOT_CLEAN


def _balance_lines(gateway: Gateway) -> list[str]:
    """逐個讀得到的數據快照,一行講完它的三數等式。讀不到檔的略過。"""
    from karst.data.errors import SnapshotBroken
    from karst.data.snapshots import universe_balance

    lines: list[str] = []
    for listing in gateway.store.list_snapshots():
        try:
            lines.append(universe_balance(gateway.store, listing.snapshot_id).describe())
        except (SnapshotBroken, OSError, ValueError, KeyError):
            continue
    return lines


# ----------------------------------------------------------------------


def _print_receipt(receipt, gateway: Gateway, kind: str, name: str, out: TextIO) -> None:
    location = gateway.locate(kind, name)
    print(f"  寫入者    {receipt.writer}", file=out)
    print(f"  已蓋簽章  {'、'.join(receipt.signed_rows)}", file=out)
    print(f"  唯一落點  {location.table}({location.row_key});第二影像:"
          f"{'有' if location.has_second_image else '無'}", file=out)


def _parse_params(pairs: Sequence[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs or []:
        key, separator, value = str(pair).partition("=")
        if not separator:
            raise ValueError(f"參數要寫成「鍵=值」,收到 {pair!r}")
        key = key.strip()
        if key in values:
            raise ValueError(f"參數「{key}」在同一個參數集給了兩次,單一定義下只可有一個值")
        values[key] = value.strip()
    return values


def _read_json_rows(path: str) -> list[dict]:
    from pathlib import Path

    text = Path(path).read_text(encoding="utf-8")
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise ValueError(f"{path} 要是一個 list,每項一個因子值")
    return rows


def _split_strategy_ref(ref: str) -> tuple[str, int | None]:
    name, separator, version_text = str(ref or "").partition("@")
    if not separator or not version_text.strip():
        return name.strip(), None
    try:
        return name.strip(), int(version_text)
    except ValueError as exc:
        raise ValueError(f"策略引用 {ref!r} 的版本號不是數字") from exc
