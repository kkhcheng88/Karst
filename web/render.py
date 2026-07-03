"""Render a scan payload (web/data/latest.json) to a self-contained HTML dashboard.

Multi-panel terminal-style layout (Eikon/Bloomberg feel), inline SVG charts, NO external
JS/CSS deps (robust headless). Panels:
  1. Market Regime  — composite risk-on SCORE (0-100) gauge + Δ1d/1w/1m + sparkline +
                      factor-contribution bars (the drivers EXPLAIN the score)
  2. Sector rotation — 11 SPDR diverging RS-vs-SPY bars (baseline 1.0), cyc/def tilt
  3. Themes          — per-theme temperature + layer-1 pips + cap/equal divergence
  4. tier-1 options  — per-tool score bars, recommendation highlighted + rationale
  5. tier-2 long     — dense sortable table: score bar · action chip · RSI2 · thesis · insider

UI chrome is Traditional Chinese; DATA values (tickers, sector keys, thesis verdicts,
driver sentences) are the engine's own output and stay as produced. Read-only (NHITL).
"""
from __future__ import annotations

import html


def _esc(x) -> str:
    return html.escape("" if x is None else str(x))


def _num(x, dash="—"):
    return dash if x is None or (isinstance(x, float) and x != x) else x


_TEMP_CLASS = {"Hot": "hot", "Warm": "warm", "Cold": "cold"}
_ACTION_CLASS = {"BUY": "buy", "BUY_DIP": "buy", "WATCH": "watch", "AVOID": "avoid"}
_TEMP_ZH = {"Hot": "熱", "Warm": "溫", "Cold": "冷", "N/A": "—", "STUB": "—"}
_ACTION_ZH = {"BUY": "買入", "BUY_DIP": "買入", "WATCH": "觀察", "AVOID": "迴避"}
_CYCLE_ZH = {"early": "早期", "mid": "中期", "late": "晚期"}
_RSI_ZH = {"neutral": "中性", "oversold": "超賣", "overbought": "超買",
           "DIP": "回檔", "elevated": "偏高", "OB": "超買", "OS": "超賣"}
_FACTOR_ZH = {"trend": "趨勢 · SPY", "vol": "波動 · VIX", "breadth": "廣度 · IWM",
              "momentum": "動能 · SPMO", "term": "期限 · VIX/3M"}
_FACTOR_FORMULA = {
    "trend": "50 + (SPY ÷ 200日均線 − 1) × 500,夾 0–100(站上 200 線越多越高,±10% 滿格)",
    "vol": "(1 − VIX 的 252 日百分位) × 100(近一年 VIX 越低越平靜、分越高)",
    "breadth": "50 + (IWM ÷ 200日均線 − 1) × 500(小型股參與度,站上 200 線=廣度好)",
    "momentum": "50 + (SPMO/SPY 的 63 日相對強度 − 1) × 250(動能因子贏大盤越多越高)",
    "term": "50 + (1 − VIX÷VIX3M) ÷ 0.30 × 50(<1 正價差平靜加分,>1 逆價差扣分)",
}
_TOOL_ZH = {"LEAP": "買長 call", "SHORT_CALL": "賣 call", "CSP": "賣 put 收租", "CASH": "持現觀望"}


def _zh(m: dict, v):
    if v is None:
        return ""
    return m.get(str(v), m.get(str(v).lower(), v))


# ---------------------------------------------------------------- SVG primitives
def _meter(pct, color, w=104, h=9):
    pct = 0 if pct is None else max(0.0, min(100.0, float(pct)))
    fw = round(pct / 100 * w, 1)
    return (f'<svg class="mtr" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect width="{w}" height="{h}" rx="2" fill="#21262d"/>'
            f'<rect width="{fw}" height="{h}" rx="2" fill="{color}"/></svg>')


def _gauge(score, w=300, h=20):
    x = max(0.0, min(100.0, float(score))) / 100 * w
    zones = [(0, 45, "#4a1d1d"), (45, 65, "#4a3d18"), (65, 100, "#173f24")]
    rects = "".join(f'<rect x="{a/100*w:.1f}" width="{(b-a)/100*w:.1f}" height="{h}" fill="{c}"/>'
                    for a, b, c in zones)
    return (f'<svg width="{w}" height="{h+7}" viewBox="0 0 {w} {h+7}">{rects}'
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h}" stroke="#f0f6fc" stroke-width="2"/>'
            f'<polygon points="{x-4:.1f},{h} {x+4:.1f},{h} {x:.1f},{h+6}" fill="#f0f6fc"/></svg>')


def _spark(vals, w=300, h=46):
    vals = [v for v in (vals or []) if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pts = " ".join(f"{i/(n-1)*w:.1f},{h-(v-lo)/rng*h:.1f}" for i, v in enumerate(vals))
    base = ""
    if lo <= 50 <= hi:
        y = h - (50 - lo) / rng * h
        base = f'<line x1="0" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" stroke="#30363d" stroke-dasharray="3 3"/>'
    last = vals[-1]
    col = "#3fb950" if last >= 65 else "#d29922" if last >= 45 else "#f85149"
    lx, ly = w, h - (last - lo) / rng * h
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">{base}'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.4" fill="{col}"/></svg>')


def _rs_bar(rs, w=150, h=13, lo=0.70, hi=1.30):
    if rs is None or rs != rs:
        return ""
    rc = max(lo, min(hi, float(rs)))
    c0 = (1.0 - lo) / (hi - lo) * w
    cv = (rc - lo) / (hi - lo) * w
    over = rc >= 1.0
    col = "#3fb950" if over else "#f85149"
    x, ww = min(c0, cv), abs(cv - c0)
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect width="{w}" height="{h}" rx="2" fill="#161b22"/>'
            f'<rect x="{x:.1f}" width="{ww:.1f}" height="{h}" fill="{col}" opacity="0.85"/>'
            f'<line x1="{c0:.1f}" x2="{c0:.1f}" y1="0" y2="{h}" stroke="#6e7681" stroke-width="1"/></svg>')


def _pips(n, total=3):
    n = int(n or 0)
    return '<span class="pips">' + "".join(
        f'<i class="pip{" on" if i < n else ""}"></i>' for i in range(total)) + "</span>"


def _dchip(label, v):
    if v is None:
        return f'<span class="dchip">{label} —</span>'
    arr = "▲" if v > 0 else "▼" if v < 0 else "·"
    cls = "up" if v > 0 else "dn" if v < 0 else ""
    return f'<span class="dchip {cls}">{label} {arr}{abs(v):.1f}</span>'


# ---------------------------------------------------------------- panels
def _options_block(cards: list) -> str:
    """大盤策略 — the SPY/QQQ/SPMO options recommendations (folded into the market panel)."""
    opts = [c for c in cards if c.get("tier") == "options"]
    if not opts:
        return ""
    blocks = ""
    for c in opts:
        expr = c.get("expression") or {}
        if expr.get("type") == "ERROR":
            blocks += f'<div class="obl"><b>{_esc(c.get("ticker"))}</b> <span class="err">ERROR</span></div>'
            continue
        score = c.get("score") or {}
        ranked = sorted(score.items(), key=lambda kv: -kv[1])
        rec = expr.get("recommended")
        top = ranked[0][1] if ranked else 0
        second = ranked[1][1] if len(ranked) > 1 else 0
        gap = top - second
        rationale = (f"領先次高 {gap:.0f} 分" if gap >= 10 else
                     f"僅領先 {gap:.0f} 分(接近,擇一)" if top > 0 else "全部偏弱")
        bars = ""
        for k, v in ranked:
            is_rec = (k == rec)
            col = "#58a6ff" if is_rec else "#484f58"
            bars += (f'<div class="orow{" rec" if is_rec else ""}">'
                     f'<span class="ok">{_esc(_zh(_TOOL_ZH, k))}<i class="dim tk2">{_esc(k)}</i></span>'
                     f'{_meter(v, col, w=110)}<span class="onum">{int(v)}</span></div>')
        rec_zh = _zh(_TOOL_ZH, rec)
        blocks += f"""<div class="obl">
          <div class="ohead"><b>{_esc(c.get('ticker'))}</b>
            <span class="rec">→ {_esc(rec_zh)}</span><span class="dim">{_esc(rationale)}</span></div>
          {bars}
          <div class="odrv">{_esc(expr.get('drivers'))}</div></div>"""
    formula = """<details class="fx"><summary>分數怎麼算?</summary>
      <div>先算四個 0–1 開關:<b>dip</b>=(10−RSI2)/10(RSI2&lt;10 才&gt;0)、
      <b>overbought</b>=(RSI2−70)/30、<b>iv_low</b>=(30%−IV rank)/30%、<b>iv_high</b>=(IV rank−70%)/30%。
      再組成四個 0–100 工具分,推薦=最高者:<br>
      · 買長 call = 100 × 站上200線 × dip(上升趨勢中的超賣回檔)<br>
      · 賣 call = 100 × 站上200線 × overbought(高點賣 call 收租)<br>
      · 賣 put 收租 = 100 × max(iv_low, iv_high)(IV 極低平靜收租 或 極高恐慌)<br>
      · 持現 = 100 × 跌破200線 × (0.5+0.5×iv_high)(只有跌破 200 線才啟動)</div></details>"""
    return f"""<div class="subhead">大盤策略 <span class="sub">SPY / QQQ / SPMO · 指數怎麼表達 · 推薦 = 分數最高的工具</span></div>
      <div class="opts">{blocks}</div>{formula}"""


def _panel_market(ms: dict | None, mc: dict, cards: list) -> str:
    caveats = "".join(f"<li>{_esc(c)}</li>" for c in (mc.get("caveats") or []))
    cav = f"<ul class='caveats'>{caveats}</ul>" if caveats else ""
    gate = mc.get("gate")
    opts = _options_block(cards)
    if not ms or ms.get("score") is None:      # fallback: no composite -> text only
        return f"""<section class="panel span2 {'gate-on' if gate else 'gate-off'}">
          <div class="phead">大盤 <span class="sub">Market</span>
            <span class="pasof">閘門={_esc(gate)} · {_esc(mc.get('asof'))}</span></div>
          <div class="drivers">{_esc(mc.get('drivers'))}</div>{cav}{opts}</section>"""

    score = ms["score"]
    scls = "off" if score >= 65 else "neu" if score >= 45 else "def"
    deltas = (_dchip("1日", ms.get("delta_1d")) + _dchip("1週", ms.get("delta_1w"))
              + _dchip("1月", ms.get("delta_1m")))
    fbars = ""
    fcol = {"off": "#3fb950", "neu": "#d29922", "def": "#f85149"}
    for f in ms.get("factors", []):
        sub = f["subscore"]
        c = fcol["off" if sub >= 65 else "neu" if sub >= 45 else "def"]
        tip = _esc(_FACTOR_FORMULA.get(f["name"], ""))
        fbars += f"""<div class="frow" title="{tip}">
          <div class="fname">{_esc(_zh(_FACTOR_ZH, f['name']))}<span class="fval">{_esc(f.get('value'))}</span></div>
          <div class="fbar">{_meter(sub, c)}<span class="fnum">{sub:.0f}</span>
            <span class="fwt">×{f['weight']:.2f} = {f['contribution']:.1f}</span></div></div>"""
    reg_formula = """<details class="fx"><summary>5 因子怎麼算?</summary><div>
      每個因子先算成 0–100 子分,再 × 權重加總:<br>
      · 趨勢 (0.30) = 50 + (SPY ÷ 200日均線 − 1) × 500 &nbsp; 夾 0–100<br>
      · 波動 (0.20) = (1 − VIX 的 252 日百分位) × 100<br>
      · 廣度 (0.20) = 50 + (IWM ÷ 200日均線 − 1) × 500<br>
      · 動能 (0.15) = 50 + (SPMO/SPY 63 日相對強度 − 1) × 250<br>
      · 期限 (0.15) = 50 + (1 − VIX÷VIX3M) ÷ 0.30 × 50<br>
      <i class="dim">這是把二元 gate 用同一組因子重表達成連續、可拆解的幅度;透明合成,非新驗證訊號。</i></div></details>"""
    return f"""<section class="panel span2 {'gate-on' if gate else 'gate-off'}">
      <div class="phead">大盤 <span class="sub">Market · risk-on 0–100</span>
        <span class="pasof">閘門={_esc(gate)} · {_esc(mc.get('asof'))}</span></div>
      <div class="mkt">
        <div class="mscore">
          <div class="bignum {scls}">{score:.0f}<span class="slash">/100</span></div>
          <div class="blabel {scls}">{_esc(ms.get('label'))} <span class="dim">{_esc(str(mc.get('gate_label','')).upper())}</span></div>
          {_gauge(score)}
          <div class="deltas">{deltas}</div>
        </div>
        <div class="mtrend">
          <div class="tlab">近 90 日走勢 <span class="dim">越高越 risk-on</span></div>
          {_spark(ms.get('sparkline'))}
        </div>
      </div>
      <div class="factors">{fbars}</div>{reg_formula}{cav}{opts}
    </section>"""


def _panel_rotation(rot: dict | None) -> str:
    if not rot:
        return ""
    rows = rot.get("rows", [])
    rmax = max((abs(r.get("rs63", 1) - 1) for r in rows), default=0.1)
    bars = ""
    for r in rows:
        g = "cyc" if r.get("group") == "cyc" else "def"
        bars += f"""<div class="rrow">
          <span class="rname">{_esc(r.get('name'))}<i class="tag {g}">{'景氣' if g=='cyc' else '防禦'}</i></span>
          {_rs_bar(r.get('rs63'))}
          <span class="rnum">{_esc(r.get('rs63'))}</span></div>"""
    tilt_on = "risk-on" in (rot.get("tilt") or "")
    chips = (f'<span class="chip {"up" if tilt_on else "dn"}">{"景氣領先" if tilt_on else "防禦領先"}</span>'
             f'<span class="chip">廣度 {_esc(rot.get("n_beating"))}/11</span>'
             f'<span class="chip">景氣 {_esc(rot.get("cyc_rs"))} / 防禦 {_esc(rot.get("def_rs"))}</span>'
             f'<span class="chip {"up" if rot.get("tech_leading") else "dn"}">科技{"領先" if rot.get("tech_leading") else "落後"}</span>')
    return f"""<section class="panel">
      <div class="phead">板塊輪動 <span class="sub">11 SPDR · RS vs SPY (基準 1.00)</span></div>
      <div class="chips">{chips}</div>
      <div class="rot">{bars}</div>
    </section>"""


def _panel_sectors(sectors: dict) -> str:
    if not sectors:
        return ""
    order = {"Hot": 0, "Warm": 1, "Cold": 2}
    rows = ""
    for key, sc in sorted(sectors.items(), key=lambda kv: order.get(kv[1].get("temperature"), 3)):
        temp = sc.get("temperature", "?")
        cls = _TEMP_CLASS.get(temp, "cold")
        rs = sc.get("rs_vs_market")
        div = sc.get("cap_equal_divergence")
        brd = sc.get("breadth_above50")
        brd_pct = f"{brd*100:.0f}%" if isinstance(brd, (int, float)) and brd == brd else "—"
        divtxt = f"{div*100:+.1f}pp" if isinstance(div, (int, float)) and div == div else "—"
        divcls = "warn" if isinstance(div, (int, float)) and div == div and abs(div) > 0.08 else ""
        rows += f"""<tr class="s-{cls}">
          <td class="skey"><b>{_esc(key)}</b> <span class="dim">{_esc(sc.get('parent'))}</span></td>
          <td><span class="temp {cls}">{_esc(_zh(_TEMP_ZH, temp))}</span></td>
          <td>{_pips(sc.get('layer1_score'))}</td>
          <td class="num">{_esc(rs)}</td>
          <td class="num {divcls}">{divtxt}</td>
          <td class="num">{brd_pct}</td>
          <td class="dim lead">{_esc(sc.get('leader'))} · {_esc(sc.get('coherence'))}</td></tr>"""
    return f"""<section class="panel">
      <div class="phead">板塊 <span class="sub">Phase 1 · 溫度 · 市值/等權背離</span></div>
      <table class="sec"><thead><tr><th>主題</th><th>溫度</th><th>L1</th><th>RS</th>
        <th>背離</th><th>廣度</th><th>領頭 · 一致性</th></tr></thead><tbody>{rows}</tbody></table>
    </section>"""


def _panel_longs(cards: list) -> str:
    longs = [c for c in cards if c.get("tier") == "long"]
    if not longs:
        return ""

    def _k(c):
        s = c.get("score")
        return -(s if isinstance(s, (int, float)) else -1)
    rows = ""
    for c in sorted(longs, key=_k):
        expr = c.get("expression") or {}
        tk = _esc(c.get("ticker"))
        if expr.get("type") == "ERROR":
            rows += f'<tr class="r-err"><td><b>{tk}</b></td><td colspan="6" class="err">ERROR: {_esc(expr.get("error"))}</td></tr>'
            continue
        th = c.get("thesis") or {}
        et = c.get("entry_timing") or {}
        ins = c.get("insider") or {}
        action = expr.get("action", "?")
        acls = _ACTION_CLASS.get(action, "watch")
        sc = c.get("score")
        sc_n = sc if isinstance(sc, (int, float)) else 0
        conf = th.get("confidence")
        conf = round(conf, 2) if isinstance(conf, (int, float)) else conf
        rsi2 = et.get("rsi2")
        rsi_v = rsi2 if isinstance(rsi2, (int, float)) else None
        rcol = "#3fb950" if (rsi_v is not None and rsi_v < 15) else "#8b949e"
        src = str(th.get("source") or "").removeprefix("thesis:")
        cyc = _zh(_CYCLE_ZH, th.get("cycle_stage"))
        blk = expr.get("blocked_by") or []
        ins_txt = ""
        if ins and ins.get("label") not in (None, "no-data"):
            ce = ins.get("conf_eff")
            clu = " ⑂" if ins.get("cluster") else ""
            ins_cls = "sell" if (isinstance(ins.get("score"), (int, float)) and ins["score"] < -0.1) else ""
            adj = f" →{ce}" if ce is not None else ""
            ins_txt = f'<span class="{ins_cls}">{_esc(ins.get("label"))} ({_esc(ins.get("score"))}{clu}){adj}</span>'
        drv = _esc(expr.get("drivers"))
        if blk:
            drv = f'<span class="blk">封鎖:{_esc(", ".join(blk))}</span> ' + drv
        rows += f"""<tr data-score="{sc_n}" data-rsi="{rsi_v if rsi_v is not None else 999}">
          <td class="tk"><b>{tk}</b><div class="dim">{_esc(c.get('sector'))} {_esc(_zh(_TEMP_ZH, c.get('sector_temp')))}</div></td>
          <td><span class="act {acls}">{_esc(_zh(_ACTION_ZH, action))}</span></td>
          <td class="scell">{_meter(sc_n, '#58a6ff', w=54)}<span class="snum">{_esc(sc)}</span></td>
          <td class="num">{_num(rsi_v)}<div class="dim" style="color:{rcol}">{_esc(_zh(_RSI_ZH, et.get('label')))}</div></td>
          <td class="thc">{_esc(th.get('verdict'))}<div class="dim">信念 {_esc(conf)} · {_esc(cyc)}{(' · '+_esc(src)) if src else ''}</div></td>
          <td class="ins">{ins_txt}</td>
          <td class="drv">{drv}</td></tr>"""
    return f"""<section class="panel span2">
      <div class="phead">tier-2 做多 <span class="sub">動作 = 結構資格 × RSI-2 擇時 · 點欄位排序</span></div>
      <table class="lng" id="lng"><thead><tr>
        <th data-sort="tk">代號</th><th>動作</th><th data-sort="num" data-key="score">分數 ▾</th>
        <th data-sort="num" data-key="rsi">RSI2</th><th>論點</th><th>內部人</th><th>驅動</th>
      </tr></thead><tbody>{rows}</tbody></table>
    </section>"""


_CSS = """
:root{--bg:#0a0e14;--pan:#0d1117;--fg:#c9d1d9;--dim:#8b949e;--line:#21262d;--line2:#30363d;
  --hot:#f85149;--warm:#d29922;--cold:#58a6ff;--buy:#3fb950;--watch:#d29922;--avoid:#6e7681;--acc:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:12px/1.5 "Noto Sans TC","Microsoft JhengHei",ui-monospace,SFMono-Regular,Menlo,Consolas,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:12px}
header{display:flex;align-items:baseline;gap:12px;padding:4px 2px 10px}
header h1{font-size:17px;margin:0;letter-spacing:3px;color:#f0f6fc}
header .gen{color:var(--dim);font-size:11px;margin-left:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.panel{background:var(--pan);border:1px solid var(--line2);border-radius:6px;padding:10px 12px;overflow:hidden}
.span2{grid-column:1 / -1}
.gate-on{border-top:2px solid var(--buy)}.gate-off{border-top:2px solid var(--avoid)}
.phead{display:flex;align-items:baseline;gap:8px;font-size:13px;font-weight:700;color:#f0f6fc;
  border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:8px}
.phead .sub{color:var(--dim);font-weight:400;font-size:11px}
.phead .pasof{margin-left:auto;color:var(--dim);font-weight:400;font-size:11px}
.drivers{color:var(--fg);opacity:.9;font-size:11.5px}
.caveats{margin:8px 0 0;padding-left:16px;color:var(--warm);font-size:11px}
/* market */
.mkt{display:grid;grid-template-columns:340px 1fr;gap:16px;align-items:center}
.bignum{font-size:46px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.bignum .slash{font-size:16px;color:var(--dim);font-weight:400}
.bignum.off{color:var(--buy)}.bignum.neu{color:var(--warm)}.bignum.def{color:var(--hot)}
.blabel{font-size:15px;font-weight:700;margin:2px 0 8px}
.blabel.off{color:var(--buy)}.blabel.neu{color:var(--warm)}.blabel.def{color:var(--hot)}
.deltas{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.dchip{background:#161b22;border:1px solid var(--line2);border-radius:4px;padding:2px 7px;font-size:11px;color:var(--dim)}
.dchip.up{color:var(--buy);border-color:#1f4a2c}.dchip.dn{color:var(--hot);border-color:#4a1f1f}
.mtrend .tlab{font-size:11px;color:var(--fg);margin-bottom:4px}
.mtrend svg{width:100%;height:46px}
.factors{margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:4px 22px}
.frow{display:flex;flex-direction:column;padding:3px 0;border-bottom:1px solid var(--line)}
.fname{display:flex;justify-content:space-between;font-size:11px}
.fname .fval{color:var(--dim)}
.fbar{display:flex;align-items:center;gap:7px;margin-top:2px}
.fnum{font-weight:700;font-variant-numeric:tabular-nums;width:22px}
.fwt{color:var(--dim);font-size:10.5px}
/* rotation */
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.chip{background:#161b22;border:1px solid var(--line2);border-radius:4px;padding:2px 7px;font-size:11px;color:var(--dim)}
.chip.up{color:var(--buy)}.chip.dn{color:var(--hot)}
.rot{display:flex;flex-direction:column;gap:2px}
.rrow{display:grid;grid-template-columns:96px 150px 44px;align-items:center;gap:8px;font-size:11px}
.rname{display:flex;align-items:center;gap:4px}
.tag{font-style:normal;font-size:9px;padding:0 4px;border-radius:3px}
.tag.cyc{background:#173f24;color:var(--buy)}.tag.def{background:#3a2a12;color:var(--warm)}
.rnum{text-align:right;font-variant-numeric:tabular-nums;color:var(--dim)}
/* tables */
table{width:100%;border-collapse:collapse}
th{text-align:left;color:var(--dim);font-weight:600;padding:4px 6px;border-bottom:1px solid var(--line2);white-space:nowrap;font-size:11px}
th[data-sort]{cursor:pointer;user-select:none}th[data-sort]:hover{color:#f0f6fc}
td{padding:5px 6px;border-bottom:1px solid var(--line);vertical-align:top;font-size:11px}
.num{text-align:right;font-variant-numeric:tabular-nums}
.dim{color:var(--dim);font-size:10.5px}
.temp{font-weight:700}.temp.hot{color:var(--hot)}.temp.warm{color:var(--warm)}.temp.cold{color:var(--cold)}
.pips{display:inline-flex;gap:2px}.pip{width:7px;height:7px;border-radius:2px;background:#21262d}
.pip.on{background:var(--warm)}
.warn{color:var(--warm)}.lead{max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.s-hot td{background:rgba(248,81,73,.05)}
/* options */
.opts{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.obl{background:#0a0e14;border:1px solid var(--line);border-radius:5px;padding:8px}
.ohead{display:flex;align-items:baseline;gap:6px;margin-bottom:6px}
.ohead .rec{color:var(--acc);font-weight:700}.ohead .dim{margin-left:auto}
.orow{display:flex;align-items:center;gap:6px;font-size:11px;padding:1px 0}
.orow.rec .ok{color:var(--acc);font-weight:700}
.ok{width:120px;display:flex;gap:5px;align-items:baseline}.ok .tk2{font-size:9.5px}
.onum{width:22px;text-align:right;font-variant-numeric:tabular-nums;color:var(--dim)}
.odrv{color:var(--dim);font-size:10.5px;margin-top:6px}
.subhead{margin:14px 0 8px;padding-top:10px;border-top:1px solid var(--line2);font-size:12.5px;font-weight:700;color:#f0f6fc}
.subhead .sub{color:var(--dim);font-weight:400;font-size:11px}
details.fx{margin-top:8px;font-size:11px}
details.fx summary{cursor:pointer;color:var(--acc);user-select:none;list-style:none}
details.fx summary::-webkit-details-marker{display:none}
details.fx summary::before{content:"▸ ";color:var(--dim)}
details.fx[open] summary::before{content:"▾ "}
details.fx>div{color:var(--dim);background:#0a0e14;border:1px solid var(--line);border-radius:5px;
  padding:8px 10px;margin-top:5px;line-height:1.7}
/* longs */
.act{padding:1px 8px;border-radius:4px;font-weight:700;font-size:11px;white-space:nowrap}
.act.buy{background:rgba(63,185,80,.18);color:var(--buy)}
.act.watch{background:rgba(210,153,34,.16);color:var(--watch)}
.act.avoid{background:rgba(110,118,129,.2);color:var(--avoid)}
.scell{display:flex;align-items:center;gap:6px}.snum{font-weight:700;font-variant-numeric:tabular-nums}
.tk{white-space:nowrap}.thc{max-width:210px}.drv{max-width:280px;color:var(--dim);font-size:10.5px}
.ins{font-size:10.5px;color:var(--dim);max-width:200px}.ins .sell{color:var(--hot)}
.blk{color:var(--avoid)}.err{color:var(--hot)}.r-err td{opacity:.6}
.mtr{vertical-align:middle}
footer{color:var(--dim);font-size:11px;margin-top:16px;border-top:1px solid var(--line2);padding-top:8px}
@media(max-width:900px){.grid{grid-template-columns:1fr}.mkt{grid-template-columns:1fr}
  .factors,.opts{grid-template-columns:1fr}}
"""

_JS = """
document.querySelectorAll('#lng th[data-sort]').forEach(function(th){
  th.addEventListener('click',function(){
    var tb=th.closest('table'),rows=[].slice.call(tb.querySelectorAll('tbody tr'));
    var key=th.getAttribute('data-key'),type=th.getAttribute('data-sort');
    var asc=th.dataset.asc==='1';th.dataset.asc=asc?'0':'1';
    rows.sort(function(a,b){
      var x,y;
      if(type==='num'){x=parseFloat(a.dataset[key]);y=parseFloat(b.dataset[key]);return asc?x-y:y-x;}
      x=a.cells[0].innerText;y=b.cells[0].innerText;return asc?x.localeCompare(y):y.localeCompare(x);
    });
    var body=tb.querySelector('tbody');rows.forEach(function(r){body.appendChild(r);});
  });
});
"""


def render(payload: dict) -> str:
    mc = payload.get("market") or {}
    cards = payload.get("cards") or []
    gen = payload.get("generated_at", "—")
    ms = payload.get("market_score")
    body = (_panel_market(ms, mc, cards)
            + _panel_rotation(payload.get("rotation"))
            + _panel_sectors(payload.get("sectors") or {})
            + _panel_longs(cards))
    return f"""<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Karst · {_esc(mc.get('asof'))}</title>
<style>{_CSS}</style></head><body><div class="wrap">
<header><h1>KARST</h1><span class="dim">決策台 · Phase 0→4</span>
  <span class="gen">產生於 {_esc(gen)}</span></header>
<div class="grid">{body}</div>
<footer>唯讀決策支援(NHITL)。分數為結構資格,非下單指令。
  資料:defeatbeta / yfinance · SEC EDGAR。更新頻率:每日。</footer>
</div><script>{_JS}</script></body></html>"""


def render_error(msg: str) -> str:
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>Karst</title>
<style>{_CSS}</style></head><body><div class="wrap">
<header><h1>KARST</h1></header>
<section class="panel gate-off"><div class="phead">尚無資料</div>
<div class="drivers">{_esc(msg)}</div></section>
<footer>執行 <code>python web/run_scan.py</code> 產生第一份掃描。</footer>
</div></body></html>"""
