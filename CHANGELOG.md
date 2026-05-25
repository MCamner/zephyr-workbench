# Changelog

## [0.1.1] — 2026-05-25

### Added

- Circular dependency detection: warns when flows form a directed cycle
- Dependency validation: warns about components with no flows (orphaned)
- Trust boundary validation: warns on unencrypted flows involving external-exposed components
- Architecture consistency: warns when deprecated components appear in active flows
- Architecture consistency: warns when high/critical risks have no mitigation defined
- Improved markdown summaries: component and flow detail tables added to `zephyr summary` output
- Normalized output format: validation status printed before warnings in all commands
- Mermaid rendering consistency: `%%` architecture name comment added to all generated diagrams
- Enterprise examples: `citrix-igel-desktop-delivery.yaml` and `zero-trust-access.yaml`

### Initial

- Initial release setup
