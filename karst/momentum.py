"""Dated, descriptive basket momentum. No ratings, flows or trading signals.

Fixed daily weights measure the average constituent's move, not an investable
portfolio return. Current membership is retrospective, never a historical index.
Inputs are completed daily closes of one currency and one explicit return basis.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from statistics import median

from .comparison import _number


def rsi(closes, period=14):
    """Wilder smoothing seeded by the first period's arithmetic gains/losses."""
    values = [None] * len(closes)
    if len(closes) <= period:
        return values
    changes = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(x, 0) for x in changes[:period]) / period
    loss = sum(max(-x, 0) for x in changes[:period]) / period
    def value():
        return 50.0 if gain == loss == 0 else 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    values[period] = value()
    for i, change in enumerate(changes[period:], period + 1):
        gain = (gain * (period - 1) + max(change, 0)) / period
        loss = (loss * (period - 1) + max(-change, 0)) / period
        values[i] = value()
    return values


def _series(raw, cutoff):
    result, previous = {}, None
    for bar in raw:
        day = date.fromisoformat(bar['date']).isoformat()
        if previous is not None and day <= previous:
            raise ValueError('Daily dates must be unique and increasing')
        previous = day
        if day > cutoff:
            continue
        close = _number(bar['close'], 'close', positive=True)
        if bar.get('complete') is True:
            result[day] = close
    if cutoff not in result:
        raise ValueError('Every series needs a completed close at the exact cutoff')
    return result


def _change(values, window, end=None):
    end = len(values) - 1 if end is None else end
    return None if end < window else (values[end] / values[end-window] - 1) * 100


def _profile(values, benchmark, days):
    windows = {}
    for n in (1, 5, 20, 63):
        absolute, market = _change(values, n), _change(benchmark, n)
        windows[str(n)] = {'absolute_pct': absolute,
                          'excess_pp': None if absolute is None else absolute - market,
                          'from': days[-n-1] if len(days) > n else None}
    beta = None
    if len(values) > 63:
        x = [b/a-1 for a,b in zip(benchmark[-64:-1], benchmark[-63:])]
        y = [b/a-1 for a,b in zip(values[-64:-1], values[-63:])]
        xm, ym = sum(x)/63, sum(y)/63
        variance = sum((v-xm)**2 for v in x)
        if variance > 1e-16:
            beta = sum((a-xm)*(b-ym) for a,b in zip(x,y)) / variance
    oscillator = rsi(values)
    current_rsi = oscillator[-1]
    previous_rsi = oscillator[-6] if len(oscillator) > 5 else None
    def above(n, end):
        return None if end < n-1 else values[end] > sum(values[end-n+1:end+1])/n
    rs = [p/b for p,b in zip(values,benchmark)]
    start = max(0, len(rs)-21)
    return {'windows': windows, 'beta63': beta, 'beta_observations': 63 if beta is not None else 0,
            'last': values[-1], 'rsi14': current_rsi,
            'rsi_change5': None if current_rsi is None or previous_rsi is None else current_rsi-previous_rsi,
            'above_ma20': above(20,len(values)-1), 'above_ma20_previous5': above(20,len(values)-6),
            'above_ma50': above(50,len(values)-1),
            'previous5_excess_pp': None if len(values)<11 else _change(values,5,len(values)-6)-_change(benchmark,5,len(values)-6),
            'rs_history': [{'date':d,'value':v/rs[start]*100} for d,v in zip(days[start:],rs[start:])]}


def compare(*, series, benchmark, weights, cutoff, selected_on, basis, currency):
    """Strict calendar alignment; no forward fill, dropped member or hidden weight change.

Series shorter than a window yield null. A missing middle session refuses the
comparison rather than silently changing daily intervals. Future bars never enter.
"""
    cutoff = date.fromisoformat(cutoff).isoformat()
    date.fromisoformat(selected_on)
    if basis not in ('unadjusted_price', 'split_adjusted_price', 'total_return') or not currency:
        raise ValueError('Explicit shared price basis and currency required')
    if not weights or benchmark in weights or set(series) != set(weights) | {benchmark}:
        raise ValueError('Supply precisely the constituents and a separate benchmark')
    for weight in weights.values():
        _number(weight, 'weight', positive=True)
    if not math.isclose(sum(weights.values()),1,abs_tol=1e-9):
        raise ValueError('Weights must sum to one')
    maps = {key:_series(value,cutoff) for key,value in series.items()}
    start = max(next(iter(value)) for value in maps.values())
    days = [d for d in maps[benchmark] if d >= start]
    if len(days) < 2:
        raise ValueError('At least two common completed sessions required')
    for values in maps.values():
        if [d for d in values if d>=start] != days:
            raise ValueError('Missing or unmatched trading session; do not forward fill')
    closes = {key:[values[d] for d in days] for key,values in maps.items()}
    market = closes[benchmark]
    basket = [100.0]
    for i in range(1,len(days)):
        basket.append(basket[-1]*(1+sum(w*(closes[k][i]/closes[k][i-1]-1) for k,w in weights.items())))
    members = {key:_profile(closes[key],market,days) for key in weights}
    result = _profile(basket,market,days)
    def count(field):
        available = [m[field] for m in members.values() if m[field] is not None]
        return {'count':sum(available), 'covered':len(available), 'total':len(weights)}
    oscillators = [m['rsi14'] for m in members.values() if m['rsi14'] is not None]
    result.update(breadth20=count('above_ma20'), breadth20_previous5=count('above_ma20_previous5'),
                  breadth50=count('above_ma50'),
                  outperformers5={'count':sum(m['windows']['5']['excess_pp']>0 for m in members.values() if m['windows']['5']['excess_pp'] is not None),
                                  'covered':sum(m['windows']['5']['excess_pp'] is not None for m in members.values()),'total':len(weights)},
                  median_rsi14=median(oscillators) if oscillators else None,
                  rsi_over70=sum(v>70 for v in oscillators), rsi_coverage=len(oscillators))
    # Descriptive quadrants, not optimized thresholds or a buy/sell score.
    slow, fast = (result['windows'][str(n)]['excess_pp'] for n in (20,5))
    threshold = .25
    if slow is None or fast is None:
        state = 'insufficient'
    elif fast > threshold:
        state = 'leading' if slow > threshold else 'warming'
    elif fast < -threshold:
        state = 'cooling' if slow > threshold else 'lagging'
    else:
        state = 'mixed'
    return {'schema_version':1, 'cutoff':cutoff, 'selected_on':selected_on,
            'membership_basis':'current_constituents_retrospective', 'weighting':'daily_constant_weights',
            'basis':basis, 'currency':currency, 'benchmark':benchmark, 'weights':weights,
            'aligned_from':days[0], 'aligned_sessions':len(days), 'state':state,
            'state_threshold_pp':threshold, 'basket':result, 'members':members,
            'benchmark_profile':_profile(market,market,days)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(**json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    main()
