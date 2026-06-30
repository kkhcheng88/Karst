"""Flat launcher for the Karst spine scan (mirrors `python backtest/scorecard.py` style).

Usage:  python backtest/scan.py            # human-readable
        python backtest/scan.py --json     # machine-readable
        python backtest/scan.py --universe <path>
"""
import os
import sys

# Put the repo root on the path so `import backtest` (the package) resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.spine.orchestrator import main  # noqa: E402

if __name__ == "__main__":
    main()
