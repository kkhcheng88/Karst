"""Human reader v2. Content remains authored; rendering never makes investment calls."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path, PurePosixPath

from .build import text, source_url, page_path, SECTIONS, KINDS, history_items


def wrap(title, body, path, active=""):
    from .build import wrap as legacy
    html = legacy(title, body, path, active)
    prefix = "../" * (len(PurePosixPath(path).parts) - 1)
    css = sha256(Path(__file__).with_name("workbench.css").read_bytes()).hexdigest()[:12]
    js = sha256(Path(__file__).with_name("workbench.js").read_bytes()).hexdigest()[:12]
    return html.replace("</head>", f'<link rel="stylesheet" href="{prefix}assets/workbench.css?v={css}">'
                        f'<script defer src="{prefix}assets/workbench.js?v={js}"></script></head>')


def table(columns, rows):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th scope="col">{text(c)}</th>' for c in columns) + \
           '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{text(c)}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def is_research(r):
    return r.get("overview", {}).get("coverage") != "engineering" and "工程樣本" not in r["review_status"]


def listing(reports, prefix=""):
    rows = []
    for r in reports:
        o = r.get("overview", {})
        name = f'{r.get("symbol", "")} {r["name"]}'.strip()
        rows.append(f'<tr data-kind="{r["kind"]}" data-action="{text(o.get("action_state", "watch"))}" data-date="{r["published_at"]}" data-name="{text(name)}">'
                    f'<th scope="row"><a href="{prefix}{page_path(r)}">{text(name)}</a><small>{text(o.get("chain", KINDS[r["kind"]]))}</small></th>'
                    f'<td><strong>{text(r["verdict"])}</strong><span class="row-summary">{text(r["summary"])}</span></td>'
                    f'<td>{text(r["action"])}</td><td>{text(o.get("change", r["change"]))}</td>'
                    f'<td>{text(o.get("next_event", "見研究頁的觀察條件"))}<small>{r["as_of"]}</small></td></tr>')
    return '''<div class="list-controls"><label>搜尋<input type="search" data-search placeholder="股票、主題或關鍵字"></label>
<label>範圍<select data-kind-filter><option value="">全部</option><option value="stocks">股票</option><option value="themes">價值鏈</option><option value="market">市場</option></select></label>
<label>行動<select data-action-filter><option value="">全部</option><option value="ready">有入場方案</option><option value="watch">觀望</option><option value="avoid">避開</option><option value="radar">研究雷達</option></select></label>
<label>排序<select data-sort><option value="recent">研究更新</option><option value="name">股票／主題</option></select></label></div>''' + \
        '<div class="table-wrap research-list"><table><thead><tr><th>股票／主題</th><th>目前判斷</th><th>行動</th><th>最近變化</th><th>下次檢驗／資料日</th></tr></thead><tbody>' + ''.join(rows) + \
        '</tbody></table></div><p class="no-results" hidden>沒有符合條件的研究。</p><div class="pagination"><button data-prev>上一頁</button><span data-count aria-live="polite"></span><button data-next>下一頁</button></div>'


def home(latest, dashboard=None):
    selected = [r for r in latest if is_research(r)]
    body = '<div class="eyebrow">KARST RESEARCH</div><h1>投資追蹤</h1>'
    if dashboard:
        from .desk import rotation, events
        m = dashboard['market']
        body += f'<section class="market-brief"><div class="eyebrow">市場 · {dashboard["price_as_of"]} 收市</div><h2><a href="{m["kind"]}/{m["slug"]}/index.html">{text(m["title"])}</a></h2><p>{text(m["summary"])}</p></section>'
        body += rotation(dashboard) + events(dashboard)
    body += '<section><h2>研究最新變化</h2>' + listing(selected) + '</section>'
    return wrap("研究總覽", body, "index.html", "home")


def network(graph):
    # Semantic columns work without JS; selecting a company highlights its actual
    # economic links in the relation list instead of drawing unreadable spaghetti.
    groups = {}
    for node in graph["nodes"]:
        groups.setdefault(node["role"], []).append(node)
    body = '<div class="chain-map">'
    for role, nodes in groups.items():
        body += f'<div class="chain-stage"><h3>{text(role)}</h3>'
        for node in nodes:
            body += f'<button class="chain-node" data-node="{text(node["key"])}" aria-pressed="false">{text(node["label"])}</button>'
        body += '</div>'
    body += '</div><button class="chain-reset">全部關係</button><ul class="chain-edges">'
    labels = {n["key"]: n["label"] for n in graph["nodes"]}
    for edge in graph["edges"]:
        basis = "文件關係" if edge["basis"] == "documented" else "研究推論"
        # Competition and complementarity have no supplier-to-customer direction.
        connector = " · " if edge.get("relation_type") in ("competes", "complements") else " → "
        body += f'<li data-from="{text(edge["from"])}" data-to="{text(edge["to"])}"><strong>{text(labels[edge["from"]])}{connector}{text(labels[edge["to"]])}</strong><span>{text(edge["label"])}</span><a href="{source_url(edge["source"])}">{basis}</a></li>'
    return body + '</ul>'


def report(r, versions, *, archive=False, check=None):
    path = page_path(r, archive)
    prefix = "../" * (len(PurePosixPath(path).parts) - 1)
    title = f'{r.get("symbol", "")} {r["name"]}'.strip()
    body = (f'<aside class="archive-note">這是當時的分析快照。<a href="{prefix}{page_path(r)}">查看最新分析 →</a></aside>' if archive else '')
    body += f'<div class="eyebrow">{text(r.get("overview",{}).get("chain",KINDS[r["kind"]]))} · 資料截至 {r["as_of"]}</div><h1>{text(title)}</h1>'
    order = ["judgment", "plan", "fundamentals", "valuation", "technicals"] if r["kind"] == "stocks" else [s["key"] for s in r["sections"]]
    by_key = {s["key"]: s for s in r["sections"]}
    body += '<nav class="contents" aria-label="本頁內容">' + ''.join(f'<a href="#{k}">{text(by_key[k].get("title",SECTIONS.get(k,k)))}</a>' for k in order) + '</nav><div class="report-body">'
    for key in order:
        s = by_key[key]
        body += f'<section id="{key}" class="section-{key}"><h2>{text(s.get("title",SECTIONS.get(key,key)))}</h2>'
        for p in s["paragraphs"]:
            body += '<p>' + (f'<strong>{text(p["lead"])} </strong>' if p.get("lead") else '') + text(p["text"]) + '</p>'
        if key == "plan" and r["metrics"]:
            body += '<dl class="decision-context">' + ''.join(f'<div><dt>{text(m["label"])}</dt><dd>{text(m["value"])}</dd><small>{text(m["note"])}</small></div>' for m in r["metrics"]) + '</dl>'
        if s.get("rows"):
            body += table(s.get("row_headers", ["觀察", "目前狀態", "對判斷的影響"]), [[v["label"],v["value"],v["note"]] for v in s["rows"]])
        for t in s.get("tables", []):
            rendered = table(t["columns"],t["rows"])
            if t.get("note"):
                rendered += f'<p class="table-note">{text(t["note"])}</p>'
            body += f'<details><summary>{text(t["title"])}</summary>{rendered}</details>' if t.get("collapsed",False) else f'<h3>{text(t["title"])}</h3>{rendered}'
        if s.get("network"):
            body += network(s["network"])
        if s.get("chart"):
            body += f'<div class="interactive-chart" data-chart="{prefix}assets/{s["chart"]}"><div class="chart-tools" hidden><label>週期<select data-period><option value="D">日線</option><option value="W">週線</option><option value="M">月線</option></select></label><label><input type="checkbox" data-ma checked>均線</label><label><input type="checkbox" data-levels checked>支阻</label><button data-fit>全貌</button></div><p class="chart-reading" aria-live="polite"></p><div class="chart-canvas" hidden></div><p class="chart-status">互動圖載入中；下方可查看靜態圖。</p></div>'
        if s.get("figure"):
            f = s["figure"]
            figure = f'<figure><a href="{prefix}assets/{f["file"]}"><img src="{prefix}assets/{f["file"]}" alt="{text(f["alt"])}" loading="lazy"></a><figcaption>{text(f["caption"])}</figcaption></figure>'
            body += f'<details class="static-chart" open><summary>靜態圖</summary>{figure}</details>' if s.get("chart") else figure
        body += '</section>'
    body += '</div>'
    body += f'<section class="investment-change"><h2>與上次相比</h2><p>{text(r["change"])}</p></section>'
    if r["related"]:
        body += '<section class="related"><h2>相關研究</h2>' + ''.join(f'<a href="{prefix}{x["kind"]}/{x["slug"]}/index.html">{text(x["label"])}</a>' for x in r["related"]) + '</section>'
    body += '<details><summary>資料來源與研究資訊</summary><ul class="sources">' + ''.join(f'<li><a href="{source_url(x["url"])}">{text(x["label"])}</a></li>' for x in r["sources"]) + f'</ul><p>{text(r["review_status"])} · 更新於 {r["published_at"][:10]}</p>'
    if check and not archive:
        body += f'<p>{text(check["checked_at"][:10])}：{text(check["summary"])}</p>'
    body += '</details><details><summary>歷次分析</summary><ol class="timeline">' + history_items(versions,prefix) + '</ol></details>'
    if any(s.get("chart") for s in r["sections"]):
        body += f'<p class="chart-attribution">TradingView Lightweight Charts™ · Copyright (с) 2025 TradingView, Inc. <a href="https://www.tradingview.com/">TradingView</a> · <a href="{prefix}assets/chart-license.html">授權</a></p><script defer src="{prefix}assets/lightweight-charts-5.2.1.js"></script><script defer src="{prefix}assets/chart.js"></script>'
    return path, wrap(title,body,path)
