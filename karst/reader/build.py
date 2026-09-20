"""Build an allowlisted static reader, without importing the research service.

Inputs are explicitly authored public summaries, not arbitrary research payloads.
Only explicit reader HTML, bundled scripts/styles and selected public chart data leave the builder.
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
    keys(r, {"schema_version", "public", "kind", "slug", "name", "published_at", "as_of", "revision", "review_status", "verdict", "summary", "change", "action", "metrics", "sections", "related", "sources"}, {"symbol", "review_by", "overview"})
    if r['schema_version'] not in (1, 2) or r['public'] is not True or r['kind'] not in KINDS:
        raise ValueError("Only approved reader schema 1/2 reports are publishable")
    if 'overview' in r:
        keys(r['overview'], {'chain', 'change', 'next_event', 'action_state', 'coverage'})
        for value in r['overview'].values():
            text(value)
        if r['overview']['action_state'] not in ('ready', 'watch', 'avoid', 'radar') or r['overview']['coverage'] not in ('research', 'radar', 'engineering'):
            raise ValueError('Unknown overview state')
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
        keys(s, {'key', 'paragraphs'}, {'rows', 'figure', 'title', 'tables', 'row_headers', 'chart', 'network'} if r['schema_version'] == 2 else {'rows', 'figure', 'title'})
        if 'row_headers' in s:
            if not isinstance(s['row_headers'], list) or len(s['row_headers']) != 3:
                raise ValueError('Three row headers required')
            for value in s['row_headers']:
                text(value)
        for table in s.get('tables', []):
            keys(table, {'title', 'columns', 'rows'}, {'collapsed', 'note'})
            if 'note' in table:
                text(table['note'])
            text(table['title'])
            if not isinstance(table['columns'], list) or not 2 <= len(table['columns']) <= 8 or not isinstance(table['rows'], list):
                raise ValueError('Invalid table shape')
            if 'collapsed' in table and type(table['collapsed']) is not bool:
                raise ValueError('collapsed must be boolean')
            for value in table['columns']:
                text(value)
            for row in table['rows']:
                if not isinstance(row, list) or len(row) != len(table['columns']):
                    raise ValueError('Table row width mismatch')
                for value in row:
                    text(value)
        if 'chart' in s:
            if not isinstance(s['chart'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.json', s['chart']) or not s.get('figure'):
                raise ValueError('Interactive chart requires a named JSON asset and static fallback')
        if 'network' in s:
            graph = s['network']
            keys(graph, {'nodes', 'edges'})
            node_ids = set()
            for node in graph['nodes']:
                keys(node, {'key', 'label', 'role'})
                safe_slug(node['key'])
                if node['key'] in node_ids:
                    raise ValueError('Duplicate graph node')
                node_ids.add(node['key'])
                text(node['label']); text(node['role'])
            for edge in graph['edges']:
                keys(edge, {'from', 'to', 'label', 'basis', 'source'}, {'relation_type'})
                if edge.get('relation_type', 'supplies') not in ('supplies', 'customer', 'finances', 'competes', 'complements', 'exposed_to'):
                    raise ValueError('Unknown economic relationship type')
                if edge['from'] not in node_ids or edge['to'] not in node_ids or edge['basis'] not in ('documented', 'inference'):
                    raise ValueError('Invalid graph relationship')
                text(edge['label']); source_url(edge['source'])
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


def load_checks(content, reports):
    """Human check notes have their own history; they never create research editions."""
    editions = {(r['kind'], r['slug'], stamp(r)): r for r in reports}
    checks = {}
    for path in sorted((content / 'checks').glob('*/*/*.json')):
        if path.is_symlink() or not path.resolve().is_relative_to(content):
            raise ValueError("Unsafe check path")
        check = json.loads(path.read_text(encoding='utf-8'))
        keys(check, {'schema_version', 'public', 'kind', 'slug', 'report_edition', 'checked_at', 'summary'})
        if check['schema_version'] != 1 or check['public'] is not True:
            raise ValueError("Only approved check notes are publishable")
        safe_slug(check['slug'])
        text(check['summary'])
        key = (check['kind'], check['slug'], check['report_edition'])
        if key not in editions:
            raise ValueError("Check must refer to an existing report edition")
        at = datetime.fromisoformat(check['checked_at'])
        if at.tzinfo is None or at < datetime.fromisoformat(editions[key]['published_at']):
            raise ValueError("Check cannot precede its research edition")
        if path.parent != content / 'checks' / check['kind'] / check['slug']:
            raise ValueError("Check path must match its subject")
        if key not in checks or at > datetime.fromisoformat(checks[key]['checked_at']):
            checks[key] = check
    return checks


def report_page(r, versions, archive=False, check=None):
    if r['schema_version'] == 2:
        from .workbench import report
        return report(r, versions, archive=archive, check=check)
    path = page_path(r, archive)
    prefix = '../' * (len(PurePosixPath(path).parts) - 1)
    title = f'{r.get("symbol", "")} {r["name"]}'.strip()
    archive_note = f'<aside class="archive-note">這是當時的分析快照。<a href="{prefix}{page_path(r)}">查看最新分析 →</a></aside>' if archive else ''
    body = archive_note + f'''<div class="eyebrow">{KINDS[r['kind']]} / 資料截至 {r['as_of']}</div><h1>{text(title)}</h1>
<p class="deck">{text(r['verdict'])}</p><p class="meta">更新於 {r['published_at'][:10]} · {text(r['review_status'])}</p>
'''
    if check and not archive:
        body += f'<aside class="change"><span>最近追蹤 · {text(check["checked_at"][:10])}</span><p>{text(check["summary"])}</p></aside>'
    body += f'''<div class="change"><span>這次更新</span><p>{text(r['change'])}</p></div>{metrics(r['metrics'])}
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
        if p.suffix not in {'.html', '.css', '.png', '.js', '.json'}:
            raise ValueError(f"Unexpected public file: {p.name}")
        if p.suffix == '.json':
            from .interactive import validate as validate_chart
            validate_chart(json.loads(p.read_text(encoding='utf-8')))
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
    checks = load_checks(content, reports)
    groups = defaultdict(list)
    for r in reports:
        groups[(r['kind'], r['slug'])].append(r)
    latest = [group[0] for group in groups.values()]
    output.mkdir(parents=True, exist_ok=True)
    (output / 'assets').mkdir()
    shutil.copyfile(Path(__file__).with_name('reader.css'), output / 'assets/reader.css')
    for name in ('workbench.css', 'workbench.js'):
        shutil.copyfile(Path(__file__).with_name(name), output / 'assets' / name)
    assets = set()
    chart_assets = set()
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
            if s.get('chart'):
                from .interactive import validate as validate_chart
                name = s['chart']
                asset = content / 'assets' / name
                if asset.is_symlink() or not asset.resolve().is_relative_to(content):
                    raise ValueError('Unsafe chart path')
                chart = validate_chart(json.loads(asset.read_text(encoding='utf-8')))
                if chart['as_of'] > r['as_of']:
                    raise ValueError('Chart cutoff is later than its research')
                chart_assets.add(name)
    for name in sorted(assets):
        shutil.copyfile(content / 'assets' / name, output / 'assets' / name)
    for name in sorted(chart_assets):
        shutil.copyfile(content / 'assets' / name, output / 'assets' / name)
    if chart_assets:
        package = Path(__file__).parent
        shutil.copyfile(package / 'chart.js', output / 'assets/chart.js')
        shutil.copyfile(package / 'vendor/lightweight-charts-5.2.1.js', output / 'assets/lightweight-charts-5.2.1.js')
        license_text = (package / 'vendor/LICENSE').read_text() + '\n' + (package / 'vendor/NOTICE').read_text()
        (output / 'assets/chart-license.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Lightweight Charts license</title><pre>' + escape(license_text) + '</pre></html>',encoding='utf-8')
    pages = {}
    for r in latest:
        p, html = report_page(r, groups[(r['kind'], r['slug'])],
                              check=checks.get((r['kind'], r['slug'], stamp(r))))
        pages[p] = html
    for r in reports:
        # Freeze history as it stood at publication, not a list of future editions.
        known = [v for v in groups[(r['kind'], r['slug'])]
                 if (v['published_at'], v['revision']) <= (r['published_at'], r['revision'])]
        p, html = report_page(r, known, archive=True)
        saved = content / 'archives' / r['kind'] / r['slug'] / (stamp(r) + '.html')
        if saved.exists():
            if saved.is_symlink() or not saved.resolve().is_relative_to(content):
                raise ValueError('Unsafe retained archive')
            html = saved.read_text(encoding='utf-8')
        pages[p] = html
    from . import workbench
    pages['index.html'] = workbench.home(latest)
    themes = '<div class="eyebrow">KARST RESEARCH</div><h1>價值鏈追蹤</h1>' + workbench.listing([r for r in latest if r['kind'] == 'themes' and workbench.is_research(r)], '../')
    pages['themes/index.html'] = workbench.wrap('主題與價值鏈', themes, 'themes/index.html', 'themes')
    updates = '<div class="eyebrow">判斷如何演變</div><h1>更新紀錄</h1><ol class="timeline">' + history_items([r for r in reports if workbench.is_research(r)], '../') + '</ol>'
    pages['updates/index.html'] = wrap('更新紀錄', updates, 'updates/index.html', 'updates')
    for path, html in pages.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding='utf-8')
    check_output(output)
    return {'pages': len(pages), 'reports': len(reports), 'assets': len(assets), 'interactive_charts': len(chart_assets)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.content, args.output)))
