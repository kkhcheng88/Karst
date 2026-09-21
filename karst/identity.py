"""Conservative entity spelling normalization, not inferred security matching."""
import re


def entity_id(value):
    value = str(value)
    match = re.fullmatch(r'cik:(\d{1,10})', value, re.I)
    return 'cik:' + match[1].zfill(10) if match else value


def entity_ids(values):
    return tuple(sorted({entity_id(value) for value in values}))


def security_record(security):
    return {**security, **{key: entity_id(security[key])
                          for key in ('issuer_id', 'security_id') if security.get(key)}}
