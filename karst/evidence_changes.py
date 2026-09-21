"""Compare preserved evidence without treating encoding/CIK spelling as news."""
import gzip
import re

from .identity import entity_ids
from .packet import confined
from .schema import digest


def equivalent(before, after, root):
    if not before or before.get('source_id') != after.get('source_id'):
        return False
    if before.get('status') != 'ok' or after.get('status') != 'ok':
        return False
    ignored = {'contract_version', 'fetched_at', 'evidence_id', 'source_version', 'supersedes', 'artifact'}
    def metadata(record):
        value = {k: v for k, v in record.items() if k not in ignored}
        value['entity_ids'] = entity_ids(value.get('entity_ids') or ())
        return value
    if metadata(before) != metadata(after):
        return False
    left, right = before['artifact'], after['artifact']
    if left['sha256'] == right['sha256'] and left['bytes'] == right['bytes']:
        return True
    edgar_html = (before.get('source') == after.get('source') == 'edgar'
                  and before.get('kind') == after.get('kind') == 'filing'
                  and before.get('media_type') == after.get('media_type') == 'text/html')
    if not (left['path'].endswith('.gz') or right['path'].endswith('.gz') or edgar_html):
        return False
    try:
        bodies = []
        for asset in (left, right):
            raw = confined(root, asset['path']).read_bytes()
            if digest(raw) != asset['sha256'] or len(raw) != asset['bytes']:
                return False
            bodies.append(gzip.decompress(raw) if asset['path'].endswith('.gz') else raw)
        if edgar_html:
            # SEC delivery injects an empty external JavaScript loader with a
            # changing relative URL. Preserve exact source bytes, but do not call
            # that loader an amended filing. No inline code, XBRL attributes,
            # visible text or other markup is normalized.
            loader = br'<script\s+type="text/javascript"\s+src="/[^"<>\s]+"\s*>\s*</script>'
            bodies = [re.sub(loader, b'', body) for body in bodies]
        return bodies[0] == bodies[1]
    except (OSError, ValueError, EOFError):
        return False
