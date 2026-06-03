# Changelog

## [0.5.0] — 2026-06-03

- `zephyr/scoring.py`: `ArchitectureScore` datatype and `score_architecture()` — five-dimension quality scoring: risk health, control coverage, component maturity, structural health, definition completeness
- `zephyr score <file> [--json]`: new CLI command — overall score (0–100), grade (A–F), per-dimension breakdown with notes
- `zephyr/runtime.py`: `score_model()` added to stable Python API — returns `ZephyrResult` with `overall`, `grade`, and `dimensions`
- `zephyr/contracts.py`: `score` tool registered as `read-only` in the tool safety contract registry
- `tests/test_scoring.py`: 24 tests covering score shape, grade thresholds, dimension logic, serialization, and runtime API
- `zephyr/reporter.py`: `generate_report(arch, format)` — comprehensive review reports in Markdown and HTML combining score card, narrative, risk table, findings, dependency insights, and controls
- `zephyr report <file> [--format md|html] [--output <path>] [--json]`: new CLI command — generates full review report to stdout or file
- `zephyr/runtime.py`: `report_model()` added — returns `ZephyrResult` with report content or path artifact
- `zephyr/contracts.py`: `report_stdout` (read-only) and `report_file` (write-creating) registered in safety contract registry
- `tests/test_reporter.py`: 26 tests covering Markdown/HTML output, runtime API, file writing, and error handling

## [0.4.0] — 2026-06-03

- `zephyr/diagram_import.py`: parse Mermaid diagrams and draw.io XML into Zephyr architecture YAML
- `zephyr import <file> [--format auto|mermaid|drawio]`: import diagrams into a Zephyr YAML model
- `zephyr/runtime.py`: `import_diagram_model()` stable Python API for diagram import
- `tests/test_diagram_import.py`: Mermaid and draw.io parser coverage, YAML generation, and round-trip consistency
- `ROADMAP.md`, `CHANGELOG.md`, `VERSION`, and `pyproject.toml` updated to v0.4.0

## [0.3.2] — 2026-06-03

- `zephyr/intelligence.py`: architecture intelligence engine — `detect_antipatterns` (7 patterns: external bypass, unused IdP, uncontrolled critical component, monozone, incomplete risk definition, high blast radius, isolated security control), `suggest_improvements`, `analyze_risks`, `explain_risk`, `dependency_insights`, `narrative_summary`, `review_architecture`, `analyze_architecture`
- `zephyr analyze <file> [--json]`: full intelligence analysis — narrative, anti-patterns, suggestions, dependency insights, risk distribution
- `zephyr review <file> [--json]`: all findings in severity order (risk → warning → suggestion → note)
- `zephyr explain <file> <risk-id> [--json]`: contextual risk explanation with affected components and flows
- `zephyr search` enhanced: `has:field` (non-empty) and `no:field` (empty, alias for `missing=`) query syntax
- `runtime.py`: `analyze_model`, `review_model`, `explain_risk_model` added to Python API
- 38 new intelligence tests; full suite at 200 tests

## [0.3.1] — 2026-06-03

- `zephyr-result.v1` JSON envelope normalized across all commands: `validate`, `summary`, `diagram`, `diff`, `search` — all support `--json` and return consistent `status / errors / warnings / data / artifacts / metadata` shape
- `zephyr/result.py`: `ZephyrResult` dataclass — Python type for the envelope with `.ok`, `.failed`, `.to_dict()`
- `zephyr/runtime.py`: stable Python API — `validate_model`, `summary_model`, `diagram_model`, `diff_models`, `search_model` — returns `ZephyrResult`, no subprocess required
- `zephyr/contracts.py`: `ToolContract` registry classifying each tool as `read-only`, `write-creating`, or `forbidden`; `is_safe_for_agents()` and `requires_write_intent()` helpers
- `docs/tool-contracts.md`: reference documentation for all JSON envelopes, read-only vs write-creating tools, safe call pattern, and enum values
- 27 new contract tests covering `ZephyrResult`, all runtime functions, error paths, and the contracts registry

## [0.2.0] — 2026-05-25

- `TrustBoundary` model: named security zones declared at architecture level
- `trust_boundary` field on components: assign components to a named boundary
- `tags` field on components: free-form labels for filtering and documentation
- Risk scoring: severity × likelihood matrix, score shown in `zephyr summary` output
- Mermaid subgraph rendering: components grouped by trust boundary in generated diagrams
- Trust boundary validation: warns when a component references an undefined boundary name

## [0.1.1] — 2026-05-25

- Circular dependency detection: warns when flows form a directed cycle
- Dependency validation: warns about components with no flows (orphaned)
- Trust boundary validation: warns on unencrypted flows involving external-exposed components
- Architecture consistency: warns when deprecated components appear in active flows
- Architecture consistency: warns when high/critical risks have no mitigation defined
- Improved markdown summaries: component and flow detail tables added to `zephyr summary` output
- Normalized output format: validation status printed before warnings in all commands
- Mermaid rendering consistency: `%%` architecture name comment added to all generated diagrams
- Enterprise examples: `citrix-igel-desktop-delivery.yaml` and `zero-trust-access.yaml`

- Initial release setup
