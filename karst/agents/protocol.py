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

from ..fetch.common import repo_root
from ..schema import ContractError, canonical, digest

DECLARED = "research-protocol-v1"
MODES = ("research", "update", "review")
# The strategy sources this method is assembled from. The CLI takes these as its
# defaults; the method itself owns where its own content comes from.
MANDATE_FILE = repo_root() / "strategy" / "投資委託.md"
DISCIPLINE_FILE = repo_root() / "strategy" / "specs" / "六層分析紀律-v1.md"
MODEL_FILE = repo_root() / "strategy" / "投資決策模型.md"
DISCIPLINE_PREFIXES = ("L1", "L2", "L3", "L4", "L5", "L6", "反方")
COUNTER_PREFIX = "反方"


def sections_from_markdown(text, prefixes):
    """``### <prefix>...`` headings -> {prefix: body}; a prefix matches at most one section."""
    sections, current = {}, None
    for line in text.splitlines():
        if line.startswith("#"):
            heading = line[4:].strip() if line.startswith("### ") else None
            current = next((p for p in prefixes if heading and heading.startswith(p)), None)
            if current is not None and current in sections:
                raise ContractError(f"Discipline heading prefix is ambiguous: {current}")
            if current is not None:
                sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {key: "\n".join(body).strip() for key, body in sections.items() if "".join(body).strip()}


def _split_top_level(text, separator="、"):
    parts, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char in "(（":
            depth += 1
        elif char in ")）":
            depth = max(depth - 1, 0)
        elif char == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def questions_from_model(text):
    """The scenario questions the strategy names: each module's focus plus the五件事 list."""
    questions = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if "攻什麼" not in cells:
            continue
        column = cells.index("攻什麼")
        for row in lines[index + 2:]:
            if not row.strip().startswith("|"):
                break
            values = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if len(values) > column and values[column]:
                questions.append(values[column].replace("*", "").strip())
        break
    match = re.search(r"至少追查五件事[：:](.+?)。", text, re.S)
    if match:
        questions.extend(_split_top_level(match[1].replace("\n", "")))
    return [q for q in questions if q]


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
