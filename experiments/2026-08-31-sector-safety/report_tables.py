import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results.json").read_text(encoding="utf-8"))


def f(x, nd=2):
    if isinstance(x, (int, float)):
        return f"{x:.{nd}f}"
    return str(x)


print("=== 五次熊基礎事實(不涉判準)===")
for name, d in r["bear_facts"].items():
    spy = d["SPY"]
    ief = d["IEF"]
    ief_s = (
        ief.get("note")
        if "note" in ief
        else f"回報 {f(ief['total'])}% 回撤 {f(ief['maxdd'])}%"
    )
    sec = d["sector_hold_returns_pct"]
    best = list(sec.items())[0]
    worst = list(sec.items())[-1]
    print(
        f"{name} [{d['window'][0]}~{d['window'][1]}, {d['months']}月] "
        f"SPY {f(spy['total'])}% (回撤 {f(spy['maxdd'])}%) | "
        f"最好板塊 {best[0]} {f(best[1])}% | 最差 {worst[0]} {f(worst[1])}% | IEF {ief_s}"
    )

print()
for label in ("A", "B", "C"):
    L = r["ladders"][label]
    print(f"=== 判準 {label} 階梯({L['window'][0]}~{L['window'][1]},{L['months']} 月)===")
    bh = L["buyhold_SPY"]
    print(f"  單純持有 SPY      年化 {f(bh['annual'])}%  最大回撤 {f(bh['maxdd'])}%")
    for mode, name in (
        ("two", "兩級 SPY/USD  "),
        ("three_a", "三級甲 SPY/IEF"),
        ("three_b", "三級乙 SPY/IEF濾"),
    ):
        s = L[mode]
        print(f"  {name}   年化 {f(s['annual'])}%  最大回撤 {f(s['maxdd'])}%")
    print(
        f"  成本敏感度(兩級):0bp 年化 {f(L['two_cost0']['annual'])}% / "
        f"25bp 年化 {f(L['two_cost25']['annual'])}%"
    )
    print("  逐熊(期內總回報 / 期內最大回撤):")
    for bname, b in L["bears"].items():
        if "note" in b:
            print(f"    {bname}: {b['note']}")
            continue
        cov = "全窗口" if b["full_window"] else f"只覆蓋 {b['covered'][0]}~{b['covered'][1]}"
        print(
            f"    {bname} ({b['months']}月,{cov}) "
            f"SPY {f(b['buyhold_SPY']['total'])}%/{f(b['buyhold_SPY']['maxdd'])}% | "
            f"兩級 {f(b['two']['total'])}%/{f(b['two']['maxdd'])}% | "
            f"三級甲 {f(b['three_a']['total'])}%/{f(b['three_a']['maxdd'])}% | "
            f"三級乙 {f(b['three_b']['total'])}%/{f(b['three_b']['maxdd'])}%"
        )
    print()

print("=== 訊號響的月份 ===")
for label in ("A", "A1", "B", "C"):
    fm = r["criteria"][label]["fire_months"]
    print(f"判準 {label}({len(fm)} 次):{', '.join(fm)}")
