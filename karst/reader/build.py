"""Build an allowlisted static reader, without importing the research service.

Inputs are explicitly authored public summaries, not arbitrary research payloads.
Only escaped HTML, bundled CSS, and explicitly referenced PNGs leave the builder.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.parse import unquote, urlsplit

KINDS = {"stocks": "個股", "themes": "主題與價值鏈", "market": "市場"}
SECTIONS = {
    "judgment": "🎯 目前判斷", "fundamentals": "🏢 基本面",
    "valuation": "💰 估值", "technicals": "📈 技術走勢", "plan": "🧭 交易計劃",
}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MACHINE = re.compile(r"(?:ev-|pub-|receipt-|packet-)[a-f0-9]{16,}|\b[a-f0-9]{64}\b|github_pat_|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY", re.I)


def keys(obj, required, optional=()):
    if not isinstance(obj, dict) or set(obj) - set(required) - set(optional) or set(required) - set(obj):
        raise ValueError(f"Unexpected or missing fields; expected {sorted(required)}")


def text(value):
    if not isinstance(value, str) or not value.strip() or MACHINE.search(value):
        raise ValueError("Expected human-readable text without internal identifiers or credentials")
    return escape(value, quote=True)


def safe_slug(value):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise ValueError("Unsafe page name")
    return value


def source_url(value):
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.query:
        raise ValueError("Sources must use public HTTPS URLs without credentials or query strings")
    return text(value)


def stamp(r):
    return f"{r['published_at'][:10]}-r{r['revision']}"


def page_path(r, archive=False):
    suffix = f"history/{stamp(r)}/" if archive else ""
    return f"{r['kind']}/{r['slug']}/{suffix}index.html"


def validate(r):
    keys(r, {"schema_version", "public", "kind", "slug", "name", "published_at", "as_of", "revision", "review_status", "verdict", "summary", "change", "action", "metrics", "sections", "related", "sources"}, {"symbol", "review_by"})
    if r['schema_version'] != 1 or r['public'] is not True or r['kind'] not in KINDS:
        raise ValueError("Only approved reader schema 1 reports are publishable")
    safe_slug(r['slug'])
    if type(r['revision']) is not int or r['revision'] < 1:
        raise ValueError("Positive revision required")
    published = datetime.fromisoformat(r['published_at'])
    if published.tzinfo is None or date.fromisoformat(r['as_of']) > published.date():
        raise ValueError("Publication needs a timezone and cannot precede its data cutoff")
    if 'review_by' in r and date.fromisoformat(r['review_by']) < date.fromisoformat(r['as_of']):
        raise ValueError("Invalid plan review date")
    for field in ('name', 'review_status', 'verdict', 'summary', 'change', 'action'):
        text(r[field])
    if 'symbol' in r:
        text(r['symbol'])
    for m in r['metrics']:
        keys(m, {'label', 'value', 'note'})
        for v in m.values():
            text(v)
    seen = []
    for s in r['sections']:
        keys(s, {'key', 'paragraphs'}, {'rows', 'figure', 'title'})
        safe_slug(s['key'])
        if s['key'] in seen:
            raise ValueError("Duplicate section")
        seen.append(s['key'])
        text(s.get('title', SECTIONS.get(s['key'], s['key'])))
        if not s['paragraphs']:
            raise ValueError("Empty sections are not publishable")
        for p in s['paragraphs']:
            keys(p, {'text'}, {'lead'})
            text(p['text'])
            if 'lead' in p:
                text(p['lead'])
        for row in s.get('rows', []):
            keys(row, {'label', 'value', 'note'})
            for v in row.values():
                text(v)
        if 'figure' in s:
            f = s['figure']
            keys(f, {'file', 'alt', 'caption'})
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.png', f['file']):
                raise ValueError("Only named PNG assets are supported")
            text(f['alt'])
            text(f['caption'])
    if r['kind'] == 'stocks' and seen != list(SECTIONS):
        raise ValueError("Stock reports must preserve the five agreed sections")
    for rel in r['related']:
        keys(rel, {'kind', 'slug', 'label'})
        if rel['kind'] not in KINDS:
            raise ValueError("Unknown related-page kind")
        safe_slug(rel['slug'])
        text(rel['label'])
    for s in r['sources']:
        keys(s, {'label', 'url'})
        text(s['label'])
        source_url(s['url'])
    return r


def load_reports(content):
    reports, names = [], set()
    for path in sorted((content / 'reports').glob('*/*/*.json')):
        if path.is_symlink() or not path.resolve().is_relative_to(content.resolve()):
            raise ValueError("Report paths must remain within the content directory")
        r = validate(json.loads(path.read_text(encoding='utf-8')))
        expected = Path('reports') / r['kind'] / r['slug'] / f'{stamp(r)}.json'
        if path.relative_to(content) != expected:
            raise ValueError("Filename must match the report identity and publication date")
        identity = (r['kind'], r['slug'], stamp(r))
        if identity in names:
            raise ValueError("Duplicate edition")
        names.add(identity)
        reports.append(r)
    if not reports:
        raise ValueError("No public reports found")
    subjects = {(r['kind'], r['slug']) for r in reports}
    for r in reports:
        if any((v['kind'], v['slug']) not in subjects for v in r['related']):
            raise ValueError("Related page does not exist")
    return sorted(reports, key=lambda r: (datetime.fromisoformat(r['published_at']), r['revision']), reverse=True)


def wrap(title, body, path, active=''):
    prefix = '../' * (len(PurePosixPath(path).parts) - 1)
    nav = ''.join(f'<a href="{prefix}{dest}"'+(' aria-current="page"' if name == active else '')+f'>{label}</a>' for name, dest, label in [('home','index.html','研究總覽'),('themes','themes/index.html','主題與價值鏈'),('updates','updates/index.html','更新紀錄')])
    return f'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{text(title)} · Karst</title><meta name="description" content="Karst 投資研究：最新判斷、基本面、估值、技術走勢與交易計劃。">
<link rel="stylesheet" href="{prefix}assets/reader.css"></head><body>
<a class="skip" href="#main">跳到內容</a><header class="site-header"><div class="nav-wrap"><a class="brand" href="{prefix}index.html">KARST<span>投資研究</span></a><nav aria-label="主選單">{nav}</nav></div></header>
<main id="main">{body}</main><footer>Karst 投資研究<span>分析以各頁標示的資料日期為準；價格與判斷不會即時更新。</span></footer></body></html>'''


def metrics(items):
    return '<dl class="metrics">' + ''.join(f'<div><dt>{text(m["label"])}</dt><dd>{text(m["value"])}</dd><small>{text(m["note"])}</small></div>' for m in items) + '</dl>' if items else ''


def card(r, prefix=''):
    label = f'{r.get("symbol", "")} {r["name"]}'.strip()
    return f'''<article class="card"><div class="eyebrow">{KINDS[r['kind']]} · 資料截至 {r['as_of']}</div>
<h3><a href="{prefix}{page_path(r)}">{text(label)} <span aria-hidden="true">↗</span></a></h3><p class="verdict">{text(r['verdict'])}</p><p>{text(r['summary'])}</p><div class="card-foot"><span>{text(r['action'])}</span><small>{text(r['review_status'])}</small></div></article>'''


def history_items(reports, prefix):
    return ''.join(f'<li><time>{r["published_at"][:10]}</time><div><a href="{prefix}{page_path(r, True)}">{text(r.get("symbol", r["name"]))} · {text(r["verdict"])}</a><p>{text(r["change"])}</p><small>目前行動：{text(r["action"])}</small></div></li>' for r in reports)


def report_page(r, versions, archive=False):
    path = page_path(r, archive)
    prefix = '../' * (len(PurePosixPath(path).parts) - 1)
    title = f'{r.get("symbol", "")} {r["name"]}'.strip()
    archive_note = f'<aside class="archive-note">這是當時的分析快照。<a href="{prefix}{page_path(r)}">查看最新分析 →</a></aside>' if archive else ''
    body = archive_note + f'''<div class="eyebrow">{KINDS[r['kind']]} / 資料截至 {r['as_of']}</div><h1>{text(title)}</h1>
<p class="deck">{text(r['verdict'])}</p><p class="meta">更新於 {r['published_at'][:10]} · {text(r['review_status'])}</p>
<div class="change"><span>這次更新</span><p>{text(r['change'])}</p></div>{metrics(r['metrics'])}
<nav class="contents" aria-label="本頁內容">''' + ''.join(f'<a href="#{s["key"]}">{text(s.get("title", SECTIONS.get(s["key"],s["key"])))}</a>' for s in r['sections']) + '</nav><div class="report-body">'
    for s in r['sections']:
        body += f'<section id="{s["key"]}"><h2>{text(s.get("title", SECTIONS.get(s["key"],s["key"])))}</h2>'
        for p in s['paragraphs']:
            body += '<p>' + (f'<strong>{text(p["lead"])} </strong>' if 'lead' in p else '') + text(p['text']) + '</p>'
        if s.get('rows'):
            body += '<div class="table-wrap"><table><thead><tr><th>觀察項目</th><th>水平／判斷</th><th>如何理解</th></tr></thead><tbody>' + ''.join(f'<tr><th scope="row">{text(row["label"])}</th><td>{text(row["value"])}</td><td>{text(row["note"])}</td></tr>' for row in s['rows']) + '</tbody></table></div>'
        if s.get('figure'):
            f = s['figure']
            body += f'<figure><a href="{prefix}assets/{f["file"]}" aria-label="放大圖表"><img src="{prefix}assets/{f["file"]}" alt="{text(f["alt"])}" loading="lazy"></a><figcaption>{text(f["caption"])}</figcaption></figure>'
        body += '</section>'
    body += '</div>'
    if 'review_by' in r:
        body += f'<p class="review-note">計劃最遲於 {r["review_by"]} 重評；重大業績或價格結構改變則提早檢視。</p>'
    if r['related']:
        body += '<section class="related"><h2>延伸閱讀</h2>' + ''.join(f'<a href="{prefix}{v["kind"]}/{v["slug"]}/index.html">{text(v["label"])} →</a>' for v in r['related']) + '</section>'
    body += '<details><summary>資料來源</summary><ul class="sources">' + ''.join(f'<li><a href="{source_url(s["url"])}" rel="noreferrer">{text(s["label"])}</a></li>' for s in r['sources']) + '</ul></details>'
    body += '<details><summary>歷次分析</summary><ol class="timeline">' + history_items(versions, prefix) + '</ol></details>'
    return path, wrap(title, body, path)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.links.extend(a[k] for k in ('href', 'src') if k in a)
        if 'id' in a:
            self.ids.add(a['id'])


def check_output(output):
    """Reject broken local links and files outside the public output contract."""
    for p in output.rglob('*'):
        if p.is_symlink():
            raise ValueError("Symlinks cannot be published")
        if not p.is_file():
            continue
        if p.suffix not in {'.html', '.css', '.png'}:
            raise ValueError(f"Unexpected public file: {p.name}")
        if p.suffix == '.html':
            html = p.read_text(encoding='utf-8')
            if MACHINE.search(html):
                raise ValueError("Internal identifiers in public HTML")
            parser = Links()
            parser.feed(html)
            for link in parser.links:
                u = urlsplit(link)
                if u.scheme:
                    if u.scheme != 'https':
                        raise ValueError("Unsupported external URL")
                    continue
                if u.netloc or u.path.startswith('/'):
                    raise ValueError("Public links must be relative to support project Pages")
                target = (p.parent / unquote(u.path)).resolve() if u.path else p.resolve()
                if not target.is_relative_to(output.resolve()) or not target.is_file():
                    raise ValueError(f"Broken internal link: {link}")
                if u.fragment:
                    target_parser = Links()
                    target_parser.feed(target.read_text(encoding='utf-8'))
                    if u.fragment not in target_parser.ids:
                        raise ValueError(f"Broken anchor: {link}")


def build(content, output):
    content, output = Path(content).resolve(), Path(output).resolve()
    if output == content or content.is_relative_to(output) or output.is_relative_to(content):
        raise ValueError("Output must be separate from content")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be empty; never publish an existing directory wholesale")
    reports = load_reports(content)
    groups = defaultdict(list)
    for r in reports:
        groups[(r['kind'], r['slug'])].append(r)
    latest = [group[0] for group in groups.values()]
    output.mkdir(parents=True, exist_ok=True)
    (output / 'assets').mkdir()
    shutil.copyfile(Path(__file__).with_name('reader.css'), output / 'assets/reader.css')
    assets = set()
    for r in reports:
        for s in r['sections']:
            if s.get('figure'):
                name = s['figure']['file']
                asset = content / 'assets' / name
                if asset.is_symlink() or not asset.resolve().is_relative_to(content):
                    raise ValueError("Unsafe asset path")
                if not asset.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError("Expected PNG image")
                assets.add(name)
    for name in sorted(assets):
        shutil.copyfile(content / 'assets' / name, output / 'assets' / name)
    pages = {}
    for r in latest:
        p, html = report_page(r, groups[(r['kind'], r['slug'])])
        pages[p] = html
    for r in reports:
        p, html = report_page(r, groups[(r['kind'], r['slug'])], archive=True)
        pages[p] = html
    home = '<div class="eyebrow">投資研究 · 持續更新</div><h1>先看判斷，再看機會。</h1><p class="deck">個股、主題與價值鏈，一處追蹤。</p><p class="intro">每份分析保留基本面、估值與技術走勢的分野，最後落到可執行的交易計劃。</p>'
    for kind in KINDS:
        selected = [r for r in latest if r['kind'] == kind]
        if selected:
            home += f'<section class="listing"><div class="section-head"><h2>{KINDS[kind]}</h2><span>{len(selected)} 份最新分析</span></div><div class="cards">' + ''.join(card(r) for r in selected) + '</div></section>'
    home += '<section class="listing"><div class="section-head"><h2>最近更新</h2><a href="updates/index.html">查看全部 →</a></div><ol class="timeline">' + history_items(reports[:5], '') + '</ol></section>'
    pages['index.html'] = wrap('研究總覽', home, 'index.html', 'home')
    themes = '<div class="eyebrow">由產業看公司</div><h1>主題與價值鏈</h1><p class="deck">同一個故事，不同公司的受惠程度可以很不同。</p><div class="cards">' + ''.join(card(r, '../') for r in latest if r['kind'] == 'themes') + '</div>'
    pages['themes/index.html'] = wrap('主題與價值鏈', themes, 'themes/index.html', 'themes')
    updates = '<div class="eyebrow">判斷如何演變</div><h1>更新紀錄</h1><p class="deck">改了甚麼、為甚麼改、現在怎樣做。</p><ol class="timeline">' + history_items(reports, '../') + '</ol>'
    pages['updates/index.html'] = wrap('更新紀錄', updates, 'updates/index.html', 'updates')
    for path, html in pages.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding='utf-8')
    check_output(output)
    return {'pages': len(pages), 'reports': len(reports), 'assets': len(assets)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.content, args.output)))
