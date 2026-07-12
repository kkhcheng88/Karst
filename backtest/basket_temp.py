"""Daily basket-temperature readout (Phase-3 WS4 spine, backtest/spine/sector.py).

Two-dimensional read per thesis basket (user design, 2026-07-10):
  cap-weighted ROC20   = "heat" / where cashflow is concentrating (money-weighted)
  equal-weighted ROC20 = "breadth" view (one name, one vote)
  divergence = cap - equal:
    > 0 -> megacap-led (narrow, crowded/late, breadth thin)
    < 0 -> small-cap-led (broadening, or late-stage retail froth depending on context)
  breadth_above50 = % of basket names trading above their own 50DMA (threshold breadth, separate lens)
  roc_dispersion  = std dev of member ROC20s = "variance" -- how spread out the moves are within
                    the basket (can be high even when cap/equal read similarly)

Read-only, no orders. Run by daily_playbook.cmd (appends to playbook_log.txt).

    python backtest/basket_temp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.spine import sector, universe as universe_mod


def main():
    from datetime import datetime
    print(f"==== {datetime.now():%Y-%m-%d %H:%M} ====")
    print("=== Basket temperature (cap-weighted heat vs equal-weighted breadth vs dispersion) ===")
    sectors_cfg, _ = universe_mod.load_universe()
    sec_ctx = sector.build_all(sectors_cfg)
    if not sec_ctx:
        print("(no sector context resolved)")
        return
    for key, sc in sec_ctx.items():
        print(f"\n### {key} (parent {sc.parent})  {sc.temperature}  coherence={sc.coherence}")
        print(f"  cap-weighted ROC20 (heat/cashflow)   = {sc.roc20*100:+6.1f}%")
        print(f"  equal-weighted ROC20 (breadth view)  = {sc.equal_roc20*100:+6.1f}%")
        div = sc.cap_equal_divergence
        label = ("megacap-led/narrow" if div > 0.03 else
                 "small-cap-led/broadening" if div < -0.03 else "balanced")
        print(f"  divergence (cap-equal, crowding)     = {div*100:+6.1f}pp  [{label}]")
        if sc.breadth_above50 == sc.breadth_above50:
            print(f"  breadth (%>50DMA)                    = {sc.breadth_above50*100:5.0f}%")
        print(f"  roc_dispersion (variance across names) = {sc.roc_dispersion*100:5.1f}%")
        ls = f" ({sc.leader_share*100:.0f}% of contribution)" if sc.leader_share == sc.leader_share else ""
        print(f"  leader={sc.leader}{ls}")
        for cav in sc.caveats:
            print(f"  ! {cav}")


if __name__ == "__main__":
    main()
