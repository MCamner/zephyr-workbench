---
name: architecture-model-maintainer
description: Use when creating, editing, validating, or reviewing Zephyr architecture YAML models, schemas, templates, rules, risks, controls, flows, and diagrams.
---

# Architecture Model Maintainer

Use this skill for Zephyr's domain model: architecture YAML, validation rules, summaries, diffs, search, and diagrams.

## Core Files

- `examples/*.yaml` for real models
- `schemas/architecture.schema.yaml` for documented structure
- `zephyr/models.py` and `zephyr/datamodel.py` for Python model shape
- `zephyr/loader.py` for YAML parsing and normalization
- `zephyr/validation.py` for errors and warnings
- `zephyr/analyzer.py` for summaries
- `zephyr/diagram.py` for Mermaid, HTML, and PNG rendering
- `zephyr/templates.py` for starter models
- `tests/test_validation.py`, `tests/test_rules.py`, `tests/test_templates.py`, and `tests/test_diagram.py`

## Model Quality Checks

For architecture YAML, verify:

- top-level `name`, `components`, and `flows` exist
- component names are unique and flow endpoints reference existing components
- component, risk, control, stakeholder, and environment fields match allowed values
- risks have useful severity, likelihood, impact, and mitigation when known
- controls use `applies_to` values that exist in the model
- trust boundaries and identity flows are explicit enough to explain risk
- custom `rules.require` warnings are intentional and documented by the model

## Change Workflow

When adding or changing a model field:

1. Update model/dataclass loading behavior.
2. Update validation and warnings.
3. Update schema.
4. Update templates and examples if users should see the field.
5. Update summary, search, diff, or diagram behavior if the field is user-visible.
6. Add or update focused tests.
7. Update docs if command output or model authoring guidance changes.

## Verification

```bash
python -m zephyr.cli validate examples/macos-intune-windows-domain.yaml
python -m zephyr.cli summary examples/macos-intune-windows-domain.yaml
python -m zephyr.cli diagram examples/macos-intune-windows-domain.yaml --format mermaid
pytest -q tests/test_validation.py tests/test_rules.py tests/test_templates.py tests/test_diagram.py
```

## Guardrails

- Do not loosen validation just to make a weak model pass.
- Prefer warnings for risky patterns and errors for impossible or structurally invalid models.
- Keep Mermaid output deterministic so tests and diffs stay useful.
- Preserve existing YAML style and naming conventions in examples.

## Regression gates from the reliability review

- Compare every persisted model field, including architecture `domains`/`rules`, risk mitigation/scope, component tags/boundaries and boundary definitions. Check Python/JS diffs, JSON serialization and history counts together.
- Risk scope is explicit: `components` names, `flows` objects (`from`, `to`, optional `label`), and `controls` names. Reject unknown references. Legacy risks may have empty scope; do not infer affected systems from criticality.
- Import must validate before writing and return an error envelope on failure. Raster recognition is bounded to rectangular boxes and straight centered arrows; use a real OCR smoke check before claiming recognition works. Unsupported shapes and unclear directions require review, not invented connections.
- Memory tests must isolate the default index. Search is keyword overlap; freshness uses source hashes. Graph similarity uses typed directed two-hop fingerprints, not an isomorphism proof.
- Register new runtime operations in `zephyr/contracts.py`, including exact write effects. A classification does not enforce authorization itself.

Evidence: `tests/test_review_regressions.py`, `tests/test_image_import.py`, `tests/browser_core.cjs`.
Run these alongside the affected module tests. Use this workflow for model/runtime changes;
a README-only wording correction needs only a check against the implemented behavior.
