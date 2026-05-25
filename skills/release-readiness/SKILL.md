---
name: release-readiness
description: Use when preparing Zephyr Workbench for release by checking versioning, changelog, docs, tests, CI, package metadata, and generated assets.
---

# Release Readiness

Validate that Zephyr Workbench is safe to tag, publish, or announce.

## Always Inspect

- `git status --short`
- `VERSION`
- `pyproject.toml`
- `CHANGELOG.md`
- `README.md`
- `.github/workflows/ci.yml`
- `.github/workflows/architecture-check.yml`
- `docs/`
- `examples/`
- `tests/`

## Check For

- Version mismatch between `VERSION`, `pyproject.toml`, changelog, and docs.
- Missing changelog entry for user-facing CLI, schema, validation, template, docs, or demo changes.
- README examples that no longer run.
- Example architecture files that fail validation.
- Stale generated `docs/zephyr-core.js`.
- Tests not covering changed validation, diagram, diff, search, add, init, or template behavior.
- Dirty generated artifacts in `output/` that are not intentional release assets.

## Recommended Verification

```bash
pytest -q
python -m zephyr.cli validate examples/secure-workplace.yaml
python -m zephyr.cli validate examples/identity-flow.yaml
python -m zephyr.cli validate examples/macos-intune-windows-domain.yaml
python -m zephyr.cli validate examples/macos-intune-secure-access.yaml
python -m zephyr.cli validate examples/igel-os12-infrastructure.yaml
python -m zephyr.cli validate examples/pki-infrastructure.yaml
python -m zephyr.cli summary examples/secure-workplace.yaml
python -m zephyr.cli diagram examples/secure-workplace.yaml --format mermaid
python scripts/generate_js_core.py
git diff --exit-code docs/zephyr-core.js
```

## Output

Report release readiness as:

- status: ready, blocked, or uncertain
- blockers
- files changed
- checks run
- checks not run and why
- next concrete action
