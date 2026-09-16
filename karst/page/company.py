"""The company data room: one page per company, above the individual research pages.

Self-contained escaped HTML, no scripts and no remote assets — the same rules as
``render.py``. It answers three questions a release page cannot: what is registered
for this company, which research versions exist and what each one concluded, and
what is still outstanding (pending supplements, the latest review).

Identity arrives as a parameter; nothing here is specific to one stock.
"""
from __future__ import annotations

import os
from html import escape
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote

VERSION = "0.1.0"


def e(value):
    return escape(str(value), quote=True)


def _link(publication_path, releases):
    if not publication_path:
        return None
    try:
        relative = os.path.relpath(str(publication_path), str(releases))
    except ValueError:  # different drive on Windows: no relative link is possible
        return None
    return quote(relative.replace(os.sep, "/"), safe="/")


def _cited_by(store, subject):
    """evidence_id -> the research versions that actually read or cited it."""
    from ..publish import cited_evidence_ids  # noqa: PLC0415 - avoid an import cycle

    used = {}
    for row in store.list_research(subject):
        try:
            ids = cited_evidence_ids(row["payload"])
        except (KeyError, TypeError):
            continue
        for evidence_id in ids:
            used.setdefault(evidence_id, []).append(row["version_id"])
    return used


def _table(headers, rows, empty):
    if not rows:
        return f'<p class="muted">{e(empty)}</p>'
    head = "".join(f"<th>{e(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_company_index(store, bundle, security, releases):
    """One company's data room, rendered from the store and the bundle it was built from."""
    from .. import service  # noqa: PLC0415 - service imports publish imports this package

    subject = security.get("security_id") or security.get("issuer_id") or security["ticker"]
    context = service.get_research_context(store, bundle, subject)
    cited = _cited_by(store, subject)
    css = files("karst").joinpath("page/style.css").read_text(encoding="utf-8")

    versions = []
    for row in context["versions"]:
        headline = row.get("headline") or {}
        change = (headline.get("change_since_last") or {}).get("text") if isinstance(headline, dict) else None
        href = _link(row["publication_path"], releases)
        page = f'<a href="{e(href)}">開啟</a>' if href else '<span class="muted">未發布</span>'
        versions.append([e(row["as_of"] or row["created_at"]), e(row.get("rating") or "未提供"),
                         e(row.get("execution_state") or "未提供"),
                         e(change or "未提供"), page,
                         f'<span class="muted">{e(row["status"])} · {e(row.get("model") or "未記模型")}</span>'])

    sources = []
    for record in context["sources"]:
        users = cited.get(record["evidence_id"], [])
        sources.append([f'<code>{e(record["evidence_id"])}</code>', e(record["source"]),
                        e(record["kind"]), e(record["published_at"] or "未知"),
                        e(record["fetched_at"]), e(record["status"]),
                        e(f"{len(users)} 個版本" if users else "未被引用")])

    review = context.get("latest_review")
    out = [f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
           f'style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; form-action \'none\'">'
           f'<title>{e(security["ticker"])} 資料室 · Karst</title><style>{css}</style></head><body>'
           f'<div class="banner">公司資料室 · 證據與研究版本索引,判斷見各版研究頁</div>'
           f'<main><header><div class="brand">KARST / DATA ROOM</div>'
           f'<h1>{e(security["ticker"])} <span>{e(security.get("name") or "")}</span></h1>'
           f'<p class="muted">{e(subject)} · {e(security.get("currency") or "")} · '
           f'研究版本 {len(context["versions"])} · 已登記來源 {len(context["sources"])}</p></header>']

    out.append('<section><h2>研究版本</h2>')
    out.append(_table(("資料截止", "評級", "執行狀態", "與上次相比", "頁面", "狀態／模型"),
                      versions, "本公司未有已保存的研究版本。"))
    out.append('</section><section><h2>待補請求</h2>')
    if context["pending_supplements"]:
        out.append("<ul>" + "".join(
            f'<li>{e(request["question"])}<br><span class="muted">{e(request["layer"])} · '
            f'{e(request["reason"])}</span></li>' for request in context["pending_supplements"]) + "</ul>")
    else:
        out.append('<p class="muted">沒有未處理的補查請求。</p>')
    out.append('</section><section><h2>最新覆核</h2>')
    if review:
        challenge = review.get("strongest_challenge")
        out.append(f'<p>裁決:{e(review["verdict"])}<br>{e(review["reasoning"])}</p>')
        out.append(f'<p>最強挑戰({e(challenge["target_layer"])} · {e(challenge["severity"])}):'
                   f'{e(challenge["claim"])}</p>' if challenge else
                   '<p class="muted">覆核沒有提出具體挑戰。</p>')
        out.append(f'<p class="muted">任務 {e(review["job_id"])} · 針對 {e(review["research_id"])} · '
                   f'新補查請求 {review["new_evidence_requests"]} 項</p>')
    else:
        open_jobs = [row for row in context["reviews"] if row["status"] != "done"]
        pending = f"(尚有 {len(open_jobs)} 個未完成覆核任務)" if open_jobs else ""
        out.append(f'<p class="muted">未有已完成的覆核結果{pending}。</p>')
    out.append('</section><section><h2>證據清單</h2>')
    out.append('<p class="muted">此處只列登記索引與狀態;原文隨各版發布包保存,查不到只代表本地未登記。</p>')
    out.append(_table(("證據", "來源", "種類", "公開", "取得", "狀態", "被引用"),
                      sources, "本 bundle 未登記任何來源。"))
    out.append(f'</section><footer>資料室 Renderer {VERSION} · 主體 {e(subject)}<br>'
               '本頁只索引已保存的證據與研究版本,不重新計算任何判斷。</footer></main></body></html>')
    return "".join(out)
