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
        "write-values", help="經同一道門寫因子值(每列要有事件時間與知情時間)"
    )
    factor_values.add_argument("--name", required=True)
    factor_values.add_argument("--version", type=int, default=None, help="留空寫入最新版")
    factor_values.add_argument(
        "--from-json", dest="from_json", required=True,
        help="JSON 檔:一個 list,每項 {entity_id, event_time, knowledge_time, value}",
    )
    factor_values.add_argument("--snapshot-id", dest="snapshot_id", default=None,
                               help="這批值出自哪個數據快照(追溯到批次)")

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
    take.add_argument("--root", default=None, help="快取根(預設 data/snapshots)")
    take.add_argument("--taken-on", dest="taken_on", default=None,
                      help="快照日期,留空即抓取當日")
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
    data_commands.add_parser("list", help="列庫內全部數據快照")

    where = commands.add_parser("where", help="講出一項定義的唯一落點,並掃全庫查有沒有第二份影像")
    where.add_argument("--kind", required=True, choices=("factor", "strategy"))
    where.add_argument("--name", required=True)

    commands.add_parser("verify", help="核對全庫:揪出繞過唯一入口的寫入與落庫後的改動")
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
            return _verify(gateway, out)
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
        print("  每個值都帶事件時間與知情時間;知情時間早過事件時間即前視,寫不入。", file=out)
        return EXIT_OK

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
    if args.subcommand == "macro-snapshot":
        return _data_macro(args, gateway, out)

    universe = resolve_universe(args.tickers)
    source = build_source(args.source, bars=args.bars)
    snapshot, fetch = gateway.take_snapshot(
        start=args.start,
        end=args.end,
        universe=universe,
        source=source,
        root=args.root,
        taken_on=args.taken_on,
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


def _data_macro(args: argparse.Namespace, gateway: Gateway, out: TextIO) -> int:
    snapshot, fetch = gateway.take_macro_snapshot(
        price_snapshot_id=args.price_snapshot,
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
    for note in snapshot.notes:
        print(f"  註記      {note}", file=out)
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


def _verify(gateway: Gateway, out: TextIO) -> int:
    findings = gateway.verify()
    print(f"核對單一定義庫:{gateway.path}", file=out)
    if not findings:
        print("  全庫清白:受治理的每一列都有唯一入口的寫入者簽章,內容與登記時一字不差。", file=out)
        return EXIT_OK
    print(f"  揪到 {len(findings)} 處不合格:", file=out)
    for finding in findings:
        print(f"  - {finding}", file=out)
    print("  這些內容不會被當作正常定義用落去,請按版本鏈重新經唯一入口登記。", file=out)
    return EXIT_NOT_CLEAN


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
