---
name: repo-aware
description: Use when inspecting, explaining, planning, reviewing, or changing zephyr-workbench with repo-specific context.
---

# Repo Aware

Use this skill to ground work in zephyr-workbench's actual structure before changing code or docs.

## What This Repo Is

Zephyr Workbench is a Python 3.11 CLI for modeling infrastructure, identity, and workplace architectures with YAML, validation, summaries, diffs, search, and Mermaid or HTML diagrams.

Primary surfaces:

- `zephyr/` for CLI and core logic
- `examples/` for architecture models
- `schemas/architecture.schema.yaml` for model shape
- `docs/` for GitHub Pages, case study, JS demo, and media
- `tests/` for pytest coverage
- `.github/workflows/` for CI and model validation

## First Inspection

Start with the smallest relevant check:

```bash
git status --short
sed -n '1,220p' README.md
sed -n '1,220p' pyproject.toml
find zephyr tests examples docs schemas -maxdepth 2 -type f | sort
```

If CLI behavior matters, inspect `zephyr/cli.py` plus the module behind the command. If model behavior matters, inspect `zephyr/models.py`, `zephyr/datamodel.py`, `zephyr/loader.py`, `zephyr/validation.py`, and tests for the same feature.

## Local Verification

Prefer lightweight checks:

```bash
pytest -q
python -m zephyr.cli validate examples/secure-workplace.yaml
python -m zephyr.cli summary examples/secure-workplace.yaml
python -m zephyr.cli diagram examples/secure-workplace.yaml --format mermaid
```

When docs or the browser demo change, also run:

```bash
python scripts/generate_js_core.py
git diff --exit-code docs/zephyr-core.js
```

## Guardrails

- Preserve the CLI's simple, dependency-light design.
- Keep YAML examples valid and copy-pasteable.
- Update tests when changing validation, parsing, rendering, templates, or command output.
- Do not invent commands, flags, schema fields, or workflow behavior without checking implementation.
- Keep generated output in `output/` out of scope unless the task explicitly asks for it.
