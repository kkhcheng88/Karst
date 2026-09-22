"""Stage and apply an append-only reading release; Git/Pages deployment stays explicit.

Manifest: editions=[{report: <reader object>, provenance: <agent object>}],
optional desk=<reader desk object>, assets={filename: local_path}. No raw DB export.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from .build import build, load_reports, page_path, stamp, validate


def fingerprint(root):
    result = {}
    root = Path(root)
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Release trees cannot contain symlinks')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Existing edition or asset cannot be changed: {path.name}')
    path.write_bytes(data)


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def stage(content, manifest, output):
    content, output = Path(content).resolve(), Path(output).resolve()
    if (content == output or content.is_relative_to(output) or output.is_relative_to(content)
            or not content.is_dir() or output.exists()):
        raise ValueError('Stage into a new directory separate from existing content')
    if (not isinstance(manifest, dict) or set(manifest) - {'editions', 'desk', 'assets'}
            or not isinstance(manifest.get('editions'), list)):
        raise ValueError('Expected a release manifest with editions')
    base = fingerprint(content)
    reports = load_reports(content)
    output.mkdir(parents=True)
    candidate = output / 'content'
    shutil.copytree(content, candidate)
    # Freeze what was published before applying the new report or renderer output.
    before = output / 'before'
    build(content, before)
    for report in reports:
        archive = candidate / 'archives' / report['kind'] / report['slug'] / (stamp(report) + '.html')
        _write(archive, (before / page_path(report, archive=True)).read_bytes())
    editions = []
    for item in manifest['editions']:
        if not isinstance(item, dict) or set(item) != {'report', 'provenance'}:
            raise ValueError('Each edition requires report and provenance')
        report = validate(item['report'])
        if not isinstance(item['provenance'], dict) or not item['provenance']:
            raise ValueError('Nonempty agent provenance required')
        relative = Path('reports') / report['kind'] / report['slug'] / (stamp(report) + '.json')
        target = candidate / relative
        if target.exists():
            if json.loads(target.read_text(encoding='utf-8')) != report:
                raise ValueError('Published edition cannot be rewritten')
        else:
            previous = [r for r in reports if (r['kind'], r['slug']) == (report['kind'], report['slug'])]
            if any((datetime.fromisoformat(r['published_at']), r['revision']) >=
                   (datetime.fromisoformat(report['published_at']), report['revision']) for r in previous):
                raise ValueError('New editions must advance publication order')
            _write(target, _json(report))
        provenance = candidate / 'provenance' / report['kind'] / report['slug'] / stamp(report) / 'release.json'
        _write(provenance, _json(item['provenance']))
        reports.append(report)
        editions.append(relative.as_posix())
    for name, source in manifest.get('assets', {}).items():
        if Path(name).name != name or name in ('', '.', '..') or Path(name).suffix not in ('.png', '.json'):
            raise ValueError('Assets must be plain PNG/JSON filenames')
        source = Path(source)
        if source.is_symlink():
            raise ValueError('Asset symlinks refused')
        _write(candidate / 'assets' / name, source.read_bytes())
    if 'desk' in manifest:
        (candidate / 'desk.json').write_bytes(_json(manifest['desk']))
    summary = build(candidate, output / 'site')
    # Freeze the new editions as well. Waiting until the next release would let
    # a later renderer change their historical HTML before it was retained.
    for report in reports:
        archive = candidate / 'archives' / report['kind'] / report['slug'] / (stamp(report) + '.html')
        _write(archive, (output / 'site' / page_path(report, archive=True)).read_bytes())
    preserved = {}
    for path in before.glob('*/*/history/*/index.html'):
        rel = path.relative_to(before)
        if (output / 'site' / rel).read_bytes() != path.read_bytes():
            raise ValueError('Historical HTML changed')
        preserved[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {'schema_version': 1, 'base': base, 'candidate': fingerprint(candidate),
               'editions': editions, 'historical_html': preserved, 'build': summary,
               'status': 'staged_not_deployed'}
    (output / 'receipt.json').write_bytes(_json(receipt))
    return receipt


def apply(content, staged):
    content, staged = Path(content).resolve(), Path(staged).resolve()
    if content == staged or content.is_relative_to(staged) or staged.is_relative_to(content):
        raise ValueError('Stage and content must remain separate')
    receipt = json.loads((staged / 'receipt.json').read_text(encoding='utf-8'))
    candidate = staged / 'content'
    if fingerprint(candidate) != receipt['candidate']:
        raise ValueError('Staged content changed; stage and validate again')
    current = fingerprint(content)
    if current == receipt['candidate']:
        return {'status': 'already_applied', 'build': receipt['build']}
    if current != receipt['base']:
        raise ValueError('Source content changed since staging; rebase the release')
    # Validate with the current renderer as well, before touching the working tree.
    with tempfile.TemporaryDirectory() as check:
        build(candidate, Path(check) / 'site')
    with tempfile.TemporaryDirectory(prefix='reader-release-', dir=content.parent) as temp:
        replacement, backup = Path(temp) / 'replacement', Path(temp) / 'backup'
        shutil.copytree(candidate, replacement)
        if fingerprint(content) != receipt['base']:
            raise ValueError('Source changed during validation; rebase the release')
        content.rename(backup)
        try:
            replacement.rename(content)
        except BaseException:
            backup.rename(content)
            raise
    return {'status': 'applied_not_deployed', 'build': receipt['build']}


def verify_public(staged, base_url, edition, *, fetch=None):
    """Compare deployed bytes with the staged build, without advancing any state."""
    from urllib.parse import urlsplit, quote
    from urllib.request import urlopen
    parts = urlsplit(base_url)
    if parts.scheme != 'https' or not parts.netloc or parts.query or parts.fragment:
        raise ValueError('Expected an HTTPS site base URL without query or fragment')
    if not isinstance(edition, str) or not edition:
        raise ValueError('A release edition or commit is required')
    staged = Path(staged)
    receipt = json.loads((staged / 'receipt.json').read_text(encoding='utf-8'))
    if fingerprint(staged / 'content') != receipt['candidate']:
        raise ValueError('Staged content changed')
    # Rebuild rather than trusting potentially changed site bytes.
    with tempfile.TemporaryDirectory() as temp:
        site = Path(temp) / 'site'
        build(staged / 'content', site)
        paths = ['index.html']
        for relative in receipt['editions']:
            report = json.loads((staged / 'content' / relative).read_text(encoding='utf-8'))
            paths += [page_path(report), page_path(report, archive=True)]
        paths += [p.relative_to(site).as_posix() for p in (site / 'assets').glob('*')
                  if p.suffix in ('.json', '.png')]
        results = []
        for relative in sorted(set(paths)):
            url = base_url.rstrip('/') + '/' + relative + '?edition=' + quote(edition, safe='')
            try:
                if fetch:
                    actual = fetch(url)
                else:
                    with urlopen(url, timeout=25) as response:
                        actual = response.read()
                expected = (site / relative).read_bytes()
                results.append({'path': relative, 'matches_build': actual == expected,
                                'sha256': hashlib.sha256(actual).hexdigest()})
            except Exception as exc:
                results.append({'path': relative, 'matches_build': False, 'error': str(exc)})
    return {'status': 'verified' if all(r['matches_build'] for r in results) else 'verification_failed',
            'edition': edition, 'base_url': base_url, 'files': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('stage')
    prepare.add_argument('--content', required=True)
    prepare.add_argument('--manifest', required=True)
    prepare.add_argument('--out', required=True)
    promote = sub.add_parser('apply')
    promote.add_argument('--content', required=True)
    promote.add_argument('--staged', required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('--staged', required=True)
    verify.add_argument('--base-url', required=True)
    verify.add_argument('--edition', required=True)
    verify.add_argument('--receipt', required=True)
    args = parser.parse_args()
    if args.action == 'verify':
        result = verify_public(args.staged, args.base_url, args.edition)
        Path(args.receipt).write_bytes(_json(result))
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['status'] == 'verified' else 1)
    result = (stage(args.content, json.loads(Path(args.manifest).read_text(encoding='utf-8')), args.out)
              if args.action == 'stage' else apply(args.content, args.staged))
    print(json.dumps({k: v for k, v in result.items() if k not in ('base', 'candidate', 'historical_html')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
