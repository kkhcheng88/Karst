"""Immutable file releases. Single writer, no database or network access."""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import calculations
from .packet import confined, load_bundle, read_json
from .page.render import VERSION as RENDERER_VERSION, render
from .schema import ContractError, canonical, digest, schema_hashes, validate


def verify_release(path):
    path = Path(path)
    manifest = validate("publication", read_json(path / "publication.json"))
    seen = set()
    for asset in manifest["files"]:
        if asset["path"] in seen:
            raise ContractError("Duplicate release asset")
        seen.add(asset["path"])
        data = confined(path, asset["path"]).read_bytes()
        if digest(data) != asset["sha256"] or len(data) != asset["bytes"]:
            raise ContractError("Published asset changed: " + asset["path"])
    actual = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    if actual != seen | {"publication.json"}:
        raise ContractError("Release contains unregistered files")
    return manifest


def publish(bundle, output, *, previous_publication_id=None):
    bundle, output = Path(bundle), Path(output)
    packet, records, research = load_bundle(bundle)
    calculated = calculations.calculate(research)
    pinned_schemas = schema_hashes(packet["contract_version"])
    payload = {"packet": packet, "evidence": records, "research": research,
               "schema_hashes": pinned_schemas, "renderer": RENDERER_VERSION,
               "calculator": calculations.VERSION, "previous": previous_publication_id}
    input_hash = digest(canonical(payload))
    publication_id = "pub-" + input_hash
    output.mkdir(parents=True, exist_ok=True)
    target = output / publication_id
    lock = output / ".publish.lock"
    try:
        descriptor = lock.open("x")
    except FileExistsError as exc:
        raise ContractError("Another publisher holds .publish.lock; inspect stale locks manually") from exc
    staging = None
    try:
        descriptor.close()
        if target.is_symlink():
            raise ContractError("Release target must not be a symlink")
        if target.exists():
            manifest = verify_release(target)
            if manifest["input_hash"] != input_hash or manifest["publication_id"] != publication_id:
                raise ContractError("Existing publication identity differs")
            return target
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=output))
        inputs = staging / "inputs"
        inputs.mkdir()
        reserved = {"packet.json", "research.json", "evidence.json"}
        for record in records:
            relative = record["artifact"]["path"]
            if relative.split("/")[0] in reserved:
                raise ContractError("Source path collides with bundle metadata")
            destination = confined(inputs, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = confined(bundle, relative).read_bytes()
            # Check again after copying: mutable input files cannot race publication.
            if digest(data) != record["artifact"]["sha256"] or len(data) != record["artifact"]["bytes"]:
                raise ContractError("Source changed during publication")
            destination.write_bytes(data)
        for name, value in (("packet", packet), ("evidence", records), ("research", research)):
            (inputs / f"{name}.json").write_bytes(canonical(value))
        (staging / "calculations.json").write_bytes(canonical(calculated))
        (staging / "index.html").write_text(
            render(packet, records, research, calculated, inputs), encoding="utf-8")
        assets = []
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                assets.append({"path": path.relative_to(staging).as_posix(),
                               "sha256": digest(data), "bytes": len(data)})
        manifest = {"contract_version": packet["contract_version"], "publication_id": publication_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "as_of": packet["as_of"], "target_date": research["target_date"],
                    "security": packet["security"], "mode": research["mode"],
                    "packet_id": packet["packet_id"], "research_id": research["research_id"],
                    "previous_publication_id": previous_publication_id,
                    "renderer_version": RENDERER_VERSION, "calculator_version": calculations.VERSION,
                    "schema_hashes": pinned_schemas, "dependencies": packet["dependencies"],
                    "input_hash": input_hash, "files": assets}
        validate("publication", manifest)
        (staging / "publication.json").write_bytes(canonical(manifest))
        verify_release(staging)
        staging.rename(target)
        staging = None
        return target
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()
