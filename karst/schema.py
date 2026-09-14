"""Canonical JSON Schema validation; references resolve only from packaged schemas."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

VERSION = "0.1.0"
KINDS = ("evidence", "packet", "research", "publication")
BASE = f"urn:karst:contract:{VERSION}:"


class ContractError(ValueError):
    """An input cannot safely be consumed under the selected contract."""


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(data: bytes):
    def bad_constant(value):
        raise ContractError(f"Non-finite JSON number: {value}")
    try:
        return json.loads(data, object_pairs_hook=_pairs, parse_constant=bad_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"Invalid JSON: {exc}") from exc


@lru_cache(maxsize=1)
def schemas():
    return {kind: decode(files("karst").joinpath(
        f"contracts/v0_1/{kind}.schema.json").read_bytes()) for kind in KINDS}


def schema_hashes():
    return {kind: digest(canonical(schema)) for kind, schema in schemas().items()}


@lru_cache(maxsize=1)
def validators():
    registry = Registry().with_resources(
        (BASE + kind, Resource.from_contents(schema)) for kind, schema in schemas().items()
    )
    result = {}
    for kind, schema in schemas().items():
        Draft202012Validator.check_schema(schema)
        result[kind] = Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
    return result


def validate(kind, value):
    if kind not in KINDS:
        raise ContractError(f"Unknown contract: {kind}")
    try:
        canonical(value)
    except (TypeError, ValueError) as exc:
        raise ContractError("Input must be finite JSON data") from exc
    errors = sorted(validators()[kind].iter_errors(value),
                    key=lambda error: str(list(error.absolute_path)))
    if errors:
        error = errors[0]
        path = "/".join(map(str, error.absolute_path)) or "<root>"
        raise ContractError(f"{kind}/{path}: {error.message}")
    return value
