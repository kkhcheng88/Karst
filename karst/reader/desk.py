"""Public market desk projection: dated prices, rotation and thesis events."""
from datetime import date
import json
import math

from .build import keys, text, safe_slug, source_url, KINDS


def load(content, reports):
    path = content / 'desk.json'
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValueError('Unsafe desk path')
    d = json.loads(path.read_text(encoding='utf-8'))
    keys(d, {'schema_version','as_of','price_as_of','summary','method','market','groups','events'}, {'participation'})
    if d['schema_version'] != 1 or date.fromisoformat(d['price_as_of']) > date.fromisoformat(d['as_of']):
        raise ValueError('Invalid desk date or version')
    text(d['summary']); text(d['method'])
    available = {(r['kind'],r['slug']) for r in reports}
    def link(obj):
        safe_slug(obj['slug'])
        if (obj['kind'],obj['slug']) not in available:
            raise ValueError('Desk link has no research page')
    keys(d['market'], {'kind','slug','title','summary'})
    link(d['market']); text(d['market']['title']); text(d['market']['summary'])
    if 'participation' in d:
        p = d['participation']
        keys(p, {'summary', 'rows'})
        text(p['summary'])
        if not isinstance(p['rows'], list) or not p['rows']:
            raise ValueError('Market comparison rows required')
        for row in p['rows']:
            keys(row, {'name','role','return1','return5','excess5','excess20','rsi14'})
            text(row['name']); text(row['role'])
            for key in ('return1','return5','excess5','excess20','rsi14'):
                v = row[key]
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v)):
                    raise ValueError('Market comparison values must be finite or null')
            if row['rsi14'] is not None and not 0 <= row['rsi14'] <= 100:
                raise ValueError('RSI must be between zero and 100')
    seen = set()
    for g in d['groups']:
        keys(g, {'kind','slug','name','members','state','assessment','windows','breadth','rsi','beta','spark'})
        link(g)
        if (g['kind'],g['slug']) in seen:
            raise ValueError('Duplicate desk group')
        seen.add((g['kind'],g['slug']))
        for k in ('name','members','state','assessment','breadth','rsi','beta'):
            text(g[k])
        if set(g['windows']) != {'1','5','20'}:
            raise ValueError('Desk requires daily, weekly and monthly windows')
        for values in g['windows'].values():
            keys(values, {'return_pct','excess_pp'})
            for v in values.values():
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v)):
                    raise ValueError('Momentum value must be finite or null')
        previous = None
        for p in g['spark']:
            keys(p, {'date','value'})
            day = date.fromisoformat(p['date'])
            if day > date.fromisoformat(d['price_as_of']) or previous is not None and day <= previous:
                raise ValueError('Spark dates must be ordered and not future')
            previous = day
            if type(p['value']) not in (int,float) or not math.isfinite(p['value']) or p['value'] <= 0:
                raise ValueError('Invalid RS ratio')
    for event in d['events']:
        keys(event, {'date','when','status','title','impact','kind','slug','source'})
        link(event)
        for k in ('when','title','impact'): text(event[k])
        source_url(event['source'])
        if event['status'] not in ('confirmed','window','unscheduled'):
            raise ValueError('Invalid event certainty')
        if event['status']=='confirmed' and not event['date']:
            raise ValueError('Confirmed events need a date')
        if event['status']=='unscheduled' and event['date'] is not None:
            raise ValueError('Unscheduled events cannot invent a date')
        if event['date'] is not None: date.fromisoformat(event['date'])
    return d


def number(value, suffix):
    if value is None:
        return '<span class="neutral">—</span>'
    color = 'positive' if value > 0 else 'negative' if value < 0 else 'neutral'
    return f'<span class="{color}">{value:+.2f}{suffix}</span>'


def spark(points):
    if len(points) < 2:
        return '—'
    low, high = min(p['value'] for p in points), max(p['value'] for p in points)
    span = max(high-low, .01)
    coords = [(4+i*132/(len(points)-1), 35-(p['value']-low)/span*30) for i,p in enumerate(points)]
    line = ' '.join(f'{x:.2f},{y:.2f}' for x,y in coords)
    title = f'相對 SPY，每日收市；{points[0]["date"]} = 100，{points[-1]["date"]} = {points[-1]["value"]:.2f}'
    dots = ''.join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3"><title>{p["date"]}：{p["value"]:.2f}</title></circle>' for (x,y),p in zip(coords,points))
    return f'<svg class="rs-spark" viewBox="0 0 140 40" role="img" aria-label="{text(title)}"><title>{text(title)}</title><polyline points="{line}"/>{dots}</svg>'


def rotation(d, prefix=''):
    body = '<section class="rotation"><div class="section-heading"><h2>哪些方向正在轉強？</h2><label>觀察窗口 <select data-rotation-window><option value="1">最近一日</option><option value="5" selected>近一週 · 5 日</option><option value="20">近一月 · 20 日</option></select></label></div>'
    body += f'<p>{text(d["summary"])} <span class="muted">收市：{d["price_as_of"]}</span></p>'
    body += '<div class="table-wrap"><table class="rotation-table"><thead><tr><th>價值鏈／代表組</th><th>短線狀態</th><th>相對 SPY<br><small>百分點差</small></th><th>本身升跌</th><th>參與度<br><small>高於 20 日線</small></th><th>每日 RS<br><small>近 20 日</small></th></tr></thead><tbody>'
    for g in d['groups']:
        body += f'<tr><th scope="row"><a href="{prefix}{g["kind"]}/{g["slug"]}/index.html">{text(g["name"])}</a><small>{text(g["members"])}</small></th><td><strong>{text(g["state"])}</strong><small>{text(g["assessment"])}</small></td>'
        for field,suffix in [('excess_pp',' pp'),('return_pct','%')]:
            body += '<td class="momentum-value">'
            for n in ('1','5','20'):
                body += f'<span data-window="{n}"'+(' hidden' if n!='5' else '')+'>'+number(g['windows'][n][field],suffix)+'</span>'
            body += '</td>'
        body += f'<td>{text(g["breadth"])}</td><td>{spark(g["spark"])}</td></tr>'
    body += '</tbody></table></div><p class="table-note">狀態以近 5 日相對強弱配合近 20 日位置判讀；切換窗口只改數值。RS 線上升代表跑贏 SPY。高於 20 日線的家數反映參與度。</p>'
    body += '<details><summary>RSI、Beta 與計算口徑</summary><div class="table-wrap"><table><thead><tr><th>代表組</th><th>成員 RSI14 中位數</th><th>Beta · 63 個交易日</th></tr></thead><tbody>'
    for g in d['groups']:
        body += f'<tr><th>{text(g["name"])}</th><td>{text(g["rsi"])}</td><td>{text(g["beta"])}</td></tr>'
    return body+'</tbody></table></div><p>'+text(d['method'])+'</p></details></section>'


def events(d, prefix=''):
    # Expired confirmed events leave the upcoming list at the next authored build;
    # no browser-clock-dependent rewriting of a published snapshot.
    upcoming = [e for e in d['events'] if e['date'] is None or e['date']>=d['as_of']]
    upcoming.sort(key=lambda e:(e['date'] is None,e['date'] or '',e['title']))
    body = '<section class="event-desk"><h2>下一個會改變判斷的事件</h2><div class="table-wrap"><table><thead><tr><th>時間</th><th>事件</th><th>要檢驗甚麼</th></tr></thead><tbody>'
    labels={'confirmed':'已公告','window':'交付窗口','unscheduled':'日期待公布'}
    for e in upcoming:
        body += f'<tr><td>{text(e["when"])}<small>{labels[e["status"]]}</small></td><th scope="row"><a href="{prefix}{e["kind"]}/{e["slug"]}/index.html">{text(e["title"])}</a> <a class="event-source" href="{source_url(e["source"])}">來源</a></th><td>{text(e["impact"])}</td></tr>'
    return body+'</tbody></table></div></section>'


def participation(d):
    if not d.get('participation'):
        return ''
    p = d['participation']
    body = '<section><h2>升勢有沒有擴散？</h2><p>'+text(p['summary'])+'</p>'
    body += '<div class="table-wrap"><table><thead><tr><th>市場參照</th><th>最近一日</th><th>近5日</th><th>5日相對SPY</th><th>20日相對SPY</th><th>RSI14</th></tr></thead><tbody>'
    for r in p['rows']:
        body += '<tr><th>'+text(r['name'])+'<small>'+text(r['role'])+'</small></th>'
        for key, suffix in (('return1','%'),('return5','%'),('excess5',' pp'),('excess20',' pp')):
            body += '<td>'+number(r[key], suffix)+'</td>'
        body += '<td>'+('—' if r['rsi14'] is None else f'{r["rsi14"]:.1f}')+'</td></tr>'
    return body+'</tbody></table></div><p class="table-note">同一收市日的價格比較，不含股息；相對表現以百分點差表示。這是風格與參與度的代理，並非全市場上漲家數。</p></section>'


def market(d, latest):
    from .workbench import wrap, listing
    body='<div class="eyebrow">MARKET → VALUE CHAIN → STOCK</div><h1>市場與輪動</h1>'
    if d:
        m=d['market']
        body+=f'<section class="market-brief"><h2><a href="{m["slug"]}/index.html">{text(m["title"])}</a></h2><p>{text(m["summary"])}</p></section>'
        body+=participation(d)+rotation(d,'../')+events(d,'../')
    body+='<section><h2>市場研究</h2>'+listing([r for r in latest if r['kind']=='market'],'../')+'</section>'
    return wrap('市場與輪動',body,'market/index.html','market')
