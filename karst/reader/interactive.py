"""Allowlisted public OHLC projection from the same normalized bars as MCP charts."""
from __future__ import annotations

from datetime import date
import math

from .build import keys, text


def validate(data):
    keys(data, {"schema_version", "name", "currency", "price_basis", "as_of", "views"})
    if data["schema_version"] != 1 or set(data["views"]) != {"D", "W", "M"}:
        raise ValueError("Expected daily, weekly and monthly public views")
    for key in ("name", "currency", "price_basis"):
        text(data[key])
    cutoff = date.fromisoformat(data["as_of"])
    for view in data["views"].values():
        keys(view, {"bars", "lines", "levels"})
        previous = None
        for bar in view["bars"]:
            keys(bar, {"time", "open", "high", "low", "close", "volume", "complete"})
            at = date.fromisoformat(bar["time"])
            if at > cutoff or (previous is not None and at <= previous) or type(bar["complete"]) is not bool:
                raise ValueError("Bars must be chronological, unique and within the cutoff")
            previous = at
            for field in ("open", "high", "low", "close", "volume"):
                if type(bar[field]) not in (float, int) or not math.isfinite(bar[field]) or bar[field] < 0:
                    raise ValueError("Invalid public price or volume")
            if not bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]:
                raise ValueError("Invalid OHLC")
        if not view["bars"]:
            raise ValueError("Empty chart view")
        dates = {b["time"] for b in view["bars"]}
        for line in view["lines"]:
            keys(line, {"name", "data"})
            text(line["name"])
            seen = []
            for point in line["data"]:
                keys(point, {"time", "value"})
                if point["time"] not in dates or type(point["value"]) not in (float, int) or not math.isfinite(point["value"]):
                    raise ValueError("Line must align with displayed bars")
                seen.append(point["time"])
            if seen != sorted(set(seen)):
                raise ValueError("Line dates must be unique and sorted")
        if len(view["levels"]) > 6:
            raise ValueError("At most six relevant price levels per view")
        for level in view["levels"]:
            keys(level, {"label", "price", "kind"})
            text(level["label"])
            if (level["kind"] not in ("support", "resistance", "reference") or type(level["price"]) not in (int, float)
                    or not math.isfinite(level["price"]) or level["price"] <= 0):
                raise ValueError("Invalid chart level")
    return data


def project(bars, *, name, currency, price_basis, as_of, levels=None):
    from .. import charts
    daily = bars["D"]
    averages = [("20 日 EMA", charts.ema_series(daily, 20)),
                ("50 日 SMA", charts.sma_series(daily, 50)),
                ("200 日 SMA", charts.sma_series(daily, 200))]
    views = {}
    for rule in ("D", "W", "M"):
        series = bars.get(rule) or charts.resample(daily, rule)
        # Attach end for daily-to-week/month MA mapping without changing the bars.
        series = [b | {"end": b.get("end", b["at"])} for b in series]
        views[rule] = {"bars": [{"time": b["at"][:10], **{k: b[k] for k in
                            ("open", "high", "low", "close", "volume", "complete")}} for b in series],
                       "lines": [{"name": title, "data": [{"time": b["at"][:10], "value": v}
                                   for b, v in zip(series, charts.map_daily(daily, values, series)) if v is not None]}
                                 for title, values in averages],
                       "levels": (levels or {}).get(rule, [])}
    return validate({"schema_version": 1, "name": name, "currency": currency, "price_basis": price_basis,
                     "as_of": as_of, "views": views})
