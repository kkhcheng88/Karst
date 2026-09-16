"""One versioned copy of the research method: mandate, discipline, questions, template.

Content comes from the strategy sources themselves (`strategy/投資委託.md`,
`strategy/specs/六層分析紀律-v1.md`, `strategy/投資決策模型.md`) plus the mode
template in `prompts/`. Nothing here restates a rule that lives in those files,
and no role or output shape names a provider.
"""
from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

from ..pipeline import (DISCIPLINE_FILE, DISCIPLINE_PREFIXES, MANDATE_FILE, MODEL_FILE,
                        questions_from_model, sections_from_markdown)
from ..schema import ContractError, canonical, digest

DECLARED = "research-protocol-v1"
MODES = ("research", "update", "review")


def _declared_version(text):
    match = re.search(r"v\d+(?:\.\d+)*", text.splitlines()[0] if text.splitlines() else "")
    if not match:
        raise ContractError("Strategy source must declare a version on its first line")
    return match[0]


def _steps(template):
    """The numbered list under the template's `## 步驟` heading; one source, not a copy."""
    steps, inside = [], False
    for line in template.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().startswith("步驟")
        elif inside:
            match = re.fullmatch(r"\d+\.\s+(.+)", line.strip())
            if match:
                steps.append(match[1])
    if not steps:
        raise ContractError("Mode template must list its steps under 步驟")
    return steps


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def get_research_protocol(mode, version=None):
    """Return the exact method content for this mode; a retry pins the same version.

    version may be the declared string, the content digest, or a previously
    returned version object. A mismatch raises rather than silently serving new rules.
    """
    if mode not in MODES:
        raise ContractError(f"Unknown research mode: {mode}")
    mandate = _read(MANDATE_FILE)
    strategy = _read(MODEL_FILE)
    discipline = sections_from_markdown(_read(DISCIPLINE_FILE), DISCIPLINE_PREFIXES)
    questions = questions_from_model(strategy)
    if not questions:
        raise ContractError("Strategy source lists no scenario questions")
    template = files("karst.agents").joinpath(f"prompts/{mode}.md").read_text(encoding="utf-8")
    text = "\n\n".join([
        template,
        "# 研究委託（正本）\n\n" + mandate.strip(),
        "# 六層分析紀律（正本節錄）\n\n" + "\n\n".join(
            f"## {key}\n\n{body}" for key, body in sorted(discipline.items())),
        "# 情境問題（由策略正本取出）\n\n" + "\n".join(f"- {q}" for q in questions),
    ])
    from .research import ANALYSIS_SCHEMA  # local import: research.py pins this protocol
    from .review import REVIEW_RESULT_SCHEMA
    output_schema = REVIEW_RESULT_SCHEMA if mode == "review" else ANALYSIS_SCHEMA
    steps = _steps(template)
    content = {"mode": mode, "text": text, "output_schema": output_schema, "steps": steps}
    protocol = {
        "version": {"declared": DECLARED, "digest": digest(canonical(content)),
                    "mandate": _declared_version(mandate), "strategy": _declared_version(strategy)},
        **content,
    }
    if version is not None and version not in (
            DECLARED, protocol["version"]["digest"], protocol["version"]):
        raise ContractError("Requested protocol version is not the current content; pin it explicitly")
    return protocol
