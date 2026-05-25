# Changelog

## [Unreleased]

### Added

- Circular dependency detection: warns when flows form a directed cycle
- Dependency validation: warns about components with no flows (orphaned)
- Trust boundary validation: warns on unencrypted flows involving external-exposed components
- Architecture consistency: warns when deprecated components appear in active flows
- Architecture consistency: warns when high/critical risks have no mitigation defined

### Initial

- Initial release setup
