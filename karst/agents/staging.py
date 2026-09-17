"""One way to hand work to a worker: a new directory holding exactly what it may read.

Six-role tasks, the single main researcher and a targeted review all stage the same
way, so the isolation rule lives here instead of in three places that can drift: a
fresh directory that is not the bundle, only the allowed artifacts copied in, the
input, the output shape and the prompt written, and — if anything goes wrong —
nothing left behind. What differs between the three is the context they assemble,
not how it lands.

Isolation is still the runner's job. This limits what is staged; it cannot stop a
worker that is pointed at the repository anyway.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ..packet import confined
from ..schema import ContractError, canonical


def stage_task(bundle, evidence, *, destination, input_context, prompt_text, output_schema,
               prompt_name="prompt.md", extra_files=None):
    """Stage a NEW task directory and return it.

    ``evidence`` are the evidence records the worker may read (each with its
    ``artifact.path`` inside ``bundle``) — the ID list alone cannot locate a file,
    and every caller already holds the records it exported. ``extra_files`` maps a
    relative path inside the task directory to a source ``Path`` or to bytes.
    """
    destination = Path(destination).resolve()
    origin = Path(bundle).resolve()
    if destination == origin or origin.is_relative_to(destination):
        raise ContractError("Worker directory must be separate from its source bundle")
    canonical(input_context)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for record in evidence:
            relative = record["artifact"]["path"]
            target = confined(destination, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(confined(origin, relative), target)
        for relative, source in (extra_files or {}).items():
            target = confined(destination, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, (bytes, bytearray)):
                target.write_bytes(source)
            else:
                shutil.copyfile(Path(source), target)
        (destination / "input.json").write_bytes(canonical(input_context))
        (destination / "output.schema.json").write_bytes(canonical(output_schema))
        (destination / prompt_name).write_text(prompt_text, encoding="utf-8")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination
