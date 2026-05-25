# Changelog

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
