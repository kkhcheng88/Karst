"""Marks backtest/ as a package so `backtest.spine` is importable via `python -m` /
the scan.py launcher. The flat modules (scorecard/regime/signals/data) still run
standalone via their own sys.path bootstrap — this file does not change that."""
