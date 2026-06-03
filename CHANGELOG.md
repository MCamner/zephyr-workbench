# Changelog

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
