"""Bounded public RSS discovery; summaries are leads, not full article evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import hashlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .common import html_to_text, utc_now, write_json, write_meta
from .port import scan
from ..packet import instant
from pathlib import Path

SOURCE = 'news_rss'
KINDS = ('news',)
MAX_BYTES = 2_000_000


def feed_urls(security):
    ticker = str(security['ticker']).upper()
    name = str(security.get('name') or ticker)
    name = re.sub(r'\s+(Corporation|Corp\.?|Inc\.?)$', '', name, flags=re.I)
    query = urllib.parse.urlencode({'q': '"' + name + '"', 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
    return [('yahoo', 'https://finance.yahoo.com/rss/headline?' + urllib.parse.urlencode({'s': ticker})),
            ('google', 'https://news.google.com/rss/search?' + query)]


def http_get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Karst public investment research/1.0'})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('RSS response exceeds byte limit')
    return raw


def parse_feed(raw):
    if len(raw) > MAX_BYTES or re.search(br'<!\s*(DOCTYPE|ENTITY)', raw, re.I):
        raise ValueError('Unsupported or oversized RSS document')
    root = ET.fromstring(raw)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Expected RSS channel, not an HTML error page')
    articles = []
    for item in root.findall('./channel/item'):
        title = html_to_text(item.findtext('title') or '').strip()
        url = (item.findtext('link') or '').strip()
        if not title or urllib.parse.urlsplit(url).scheme not in ('http', 'https'):
            continue
        stamp = item.findtext('pubDate')
        try:
            published = parsedate_to_datetime(stamp)
            if published.tzinfo is None:
                raise ValueError('Date has no timezone')
            published = published.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            published = None
        articles.append({'title': title, 'url': url, 'published_at': published,
                         'publisher': item.findtext('source'),
                         'summary': html_to_text(item.findtext('description') or '')[:2000],
                         'content_scope': 'RSS headline and supplied excerpt; full article not retrieved'})
    return articles


def fetch(security, out_dir, *, since=None, client=None):
    now = utc_now()
    cutoff = instant(now)
    start = instant(since) if since and 'T' in since else (
        datetime.fromisoformat(since).replace(tzinfo=timezone.utc) if since else cutoff - timedelta(days=3))
    if start.tzinfo is None or start > cutoff:
        raise ValueError('News since must be a past date or timezone-aware timestamp')
    getter = client or http_get
    destination = Path(out_dir) / SOURCE
    destination.mkdir(parents=True, exist_ok=True)
    urls = feed_urls(security)
    def retrieve(entry):
        provider, url = entry
        try:
            return provider, url, parse_feed(getter(url)), None
        except Exception as exc:
            return provider, url, [], f'{type(exc).__name__}: {exc}'
    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        results = list(pool.map(retrieve, urls))
    coverage, articles = [], {}
    for provider, url, items, error in results:
        selected = [item for item in items if item['published_at'] is None or
                    start <= instant(item['published_at']) <= cutoff]
        coverage.append({'provider': provider, 'url': url, 'status': 'error' if error else 'ok',
                         'error': error, 'items_returned': len(items), 'in_window': len(selected),
                         'undated': sum(a['published_at'] is None for a in selected),
                         'newest_published_at': max((a['published_at'] for a in items if a['published_at']), default=None)})
        for item in selected:
            # URL identity is conservative: syndicated near-duplicates remain visible
            # for the analyst to consolidate, instead of suppressing differing claims.
            articles.setdefault(item['url'], item)
    for url, item in sorted(articles.items()):
        key = hashlib.sha256(url.encode()).hexdigest()
        path = write_json(destination / (key + '.json'), item)
        published = item['published_at']
        write_meta(path, source=SOURCE, tool='rss_article', kind='news', source_id='src-rss-' + key,
                   params={'url': url, 'title': item['title'], 'author': item['publisher'], 'source_type': 'news'},
                   source_url=url, fetched_at=now, published_at=published,
                   published_at_precision='datetime' if published else 'unknown',
                   published_at_timezone=None, published_at_basis='RSS pubDate, publisher supplied' if published else 'RSS date missing or invalid',
                   truncated=True, known_gaps=['RSS excerpt only; read and verify the linked article before adopting its claims.'])
    write_json(destination / 'coverage.json', {
        'checked_at': now, 'since': start.isoformat(), 'scope': 'configured public RSS feeds; not exhaustive news coverage',
        'providers': coverage, 'successful_feeds': sum(r['status'] == 'ok' for r in coverage),
        'candidate_articles': len(articles), 'undated_articles': sum(a['published_at'] is None for a in articles.values()),
        'status': 'ok' if all(r['status'] == 'ok' for r in coverage) else
                  'partial' if any(r['status'] == 'ok' for r in coverage) else 'error'})
    if not any(r['status'] == 'ok' for r in coverage):
        raise RuntimeError('All configured news feeds failed; see coverage.json')
    return scan(destination, lambda meta: 'news')
