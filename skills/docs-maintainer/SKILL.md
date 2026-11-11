---
name: docs-maintainer
description: Use when keeping Zephyr Workbench README, docs, case pages, command references, changelog, roadmap, or GitHub Pages demo consistent with code.
---

# Docs Maintainer

Keep Zephyr Workbench documentation accurate, practical, and easy to verify.

## Docs Surfaces

Check these in order when relevant:

- `README.md`
- `docs/index.html`
- `docs/case-macos-enterprise.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `examples/*.yaml`
- `.github/workflows/*.yml`

## Verify Claims Against Code

Before documenting behavior, confirm it in:

- `zephyr/cli.py` for commands and flags
- `zephyr/validation.py` for errors and warnings
- `zephyr/analyzer.py` for summary output
- `zephyr/diagram.py` for Mermaid, HTML, and PNG behavior
- `zephyr/templates.py` and `zephyr/init_wizard.py` for starter templates
- `schemas/architecture.schema.yaml` for model fields

## Common Checks

- README command table matches implemented commands.
- Quick start uses Python 3.11 and `pip install -e ".[dev]"`.
- Example file paths exist.
- GitHub Pages link and docs assets still exist.
- Schema, examples, and validation docs agree on allowed fields.
- Changelog and version language match `VERSION` and `pyproject.toml`.
- Generated `docs/zephyr-core.js` is in sync after core behavior changes.

## Verification

Use focused commands:

```bash
python -m zephyr.cli help
python -m zephyr.cli validate examples/macos-intune-windows-domain.yaml
python -m zephyr.cli run examples/macos-intune-windows-domain.yaml
python scripts/generate_js_core.py
python -m pytest -q tests/test_generate_js.py
node tests/browser_core.cjs
```

## Editing Guidance

Document only shipped behavior or behavior added in the same change. Prefer concise, runnable examples over broad product language. When code and docs disagree, fix the smaller wrong surface and mention what was verified.

## Reliability claims

Use `docs/tool-contracts.md` for runtime/write effects and `docs/reviews/2026-11-11-reliability.md`
for the bounded import, memory and browser recovery decisions. Keep command tables aligned
with CLI help, including governance, impact, snapshots, history and memory refresh.
Describe keyword matching as lexical search, deterministic reviews as rules, and raster
recognition with its supported shapes/connectors. Do not promote roadmap labels into
capability claims. Avoid hard-coded test counts; report an actual run when needed.
Generated sections of `docs/zephyr-core.js` cover enums, diagram styles and templates;
handwritten validation/diff logic also needs `node tests/browser_core.cjs`.
