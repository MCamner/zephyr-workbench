# Zephyr Tool Contracts

Reference for agents, MCP servers, and scripts that call Zephyr commands.

---

## JSON Envelope — `zephyr-result.v1`

All `--json` outputs use a shared envelope:

```json
{
  "status": "ok" | "warning" | "error",
  "errors": ["..."],
  "warnings": ["..."],
  "data": { ... },
  "artifacts": [ { "type": "...", ... } ],
  "metadata": {
    "command": "validate" | "summary" | "diagram" | "diff" | "search",
    "source": "<path>",
    "schema_version": "zephyr-result.v1"
  }
}
```

**Status values:**

| Status    | Meaning                                              |
| --------- | ---------------------------------------------------- |
| `ok`      | Command succeeded, no issues                         |
| `warning` | Succeeded but findings require attention             |
| `error`   | Command failed; `errors` list is non-empty           |

**Exit codes:**

| Code | Meaning                               |
| ---- | ------------------------------------- |
| `0`  | ok or warning                         |
| `1`  | error, or diff detected changes       |

---

## Read-Only Tools

These commands never write files or modify state. Safe to call freely from agents.

### `validate <file> --json`

Validates a YAML architecture model.

```json
{
  "status": "ok" | "warning" | "error",
  "errors": ["missing required top-level field: name"],
  "warnings": ["component 'X' has no flows (orphaned)"],
  "data": {
    "name": "my-architecture",
    "valid": true,
    "summary": { "components": 5, "flows": 4, "risks": 1, ... }
  },
  "artifacts": []
}
```

- `status: "ok"` — valid, no warnings
- `status: "warning"` — valid but warnings present; `data.valid` is still `true`
- `status: "error"` — invalid; `data.valid` is `false`; exit code 1

### `summary <file> --json`

Returns a structured summary without running full validation warnings.

```json
{
  "status": "ok",
  "data": {
    "name": "my-architecture",
    "description": "...",
    "meta": { "owner": "...", "version": "...", "criticality": "...", "environment": ["prod"] },
    "components": 5,
    "flows": 4,
    "risks": 2,
    "controls": 1,
    "stakeholders": 2,
    "trust_boundaries": 1,
    "risk_details": [
      { "id": "R1", "title": "...", "severity": "high", "likelihood": "medium",
        "impact": "high", "mitigation": "...", "score": 9 }
    ],
    "control_details": [{ "name": "...", "type": "technical", "applies_to": ["svc-a"] }],
    "stakeholder_details": [{ "name": "...", "role": "owner" }],
    "boundary_details": [{ "name": "...", "description": "..." }]
  },
  "artifacts": []
}
```

### `diagram <file> --format mermaid --json`

Returns Mermaid diagram content without writing a file.

```json
{
  "status": "ok",
  "data": {},
  "artifacts": [
    { "type": "diagram", "format": "mermaid", "content": "graph TD\n..." }
  ]
}
```

With `--output <path>`: artifact has `"path"` instead of `"content"` (file is written).

```json
{ "type": "diagram", "format": "mermaid", "path": "output/arch.mmd" }
```

### `search <file> <query> --json`

Filters components, flows, risks, controls, and stakeholders by field value.

Query syntax: `field=value` or `missing=field`, comma-separated for AND.

```json
{
  "status": "ok",
  "data": {
    "query": "type=endpoint",
    "total": 3,
    "components": [
      { "name": "...", "type": "endpoint", "criticality": "high",
        "exposure": "external", "lifecycle": "active" }
    ],
    "flows": [
      { "from": "...", "to": "...", "label": "...",
        "authentication": "mfa", "encryption": "tls" }
    ],
    "risks": [
      { "id": "R1", "title": "...", "severity": "high",
        "likelihood": "medium", "mitigation": "..." }
    ],
    "controls": [{ "name": "...", "type": "technical", "applies_to": ["svc"] }],
    "stakeholders": [{ "name": "...", "role": "owner" }]
  },
  "artifacts": []
}
```

`total: 0` means no results — status is still `"ok"`.

### `diff <file-a> <file-b> --json`

Compares two architecture models. Exit code 1 if changes exist, 0 if identical.

```json
{
  "status": "ok" | "warning",
  "data": {
    "source": "v1.yaml",
    "target": "v2.yaml",
    "changed": false,
    "meta": null,
    "components": [
      { "status": "added" | "removed" | "modified", "label": "svc-b (endpoint)", "fields": [
          { "field": "criticality", "old": "low", "new": "high" }
        ]
      }
    ],
    "flows": [ ... ],
    "risks": [ ... ],
    "controls": [ ... ],
    "stakeholders": [ ... ]
  },
  "artifacts": []
}
```

- `status: "ok"` → `data.changed: false`
- `status: "warning"` → `data.changed: true`; exit code 1

---

## Write-Creating Tools

These commands produce files. Callers must have explicit write intent before invoking.

| Command                          | Writes                          | Notes                                   |
| -------------------------------- | ------------------------------- | --------------------------------------- |
| `diagram <file> --output <path>` | Diagram file at `<path>`        | Also returns JSON envelope with `--json` |
| `run <file> --output-dir <dir>`  | Diagram file in `<dir>/`        | No `--json` flag; human-readable only   |
| `init [--output <path>]`         | New YAML architecture file      | Interactive wizard; no `--json`         |
| `add <file>`                     | Modifies existing YAML in place | Interactive; no `--json`                |

### Guardrails for write operations

- `diagram --output` overwrites without confirmation if path exists — callers should check path first
- `run` overwrites the diagram file silently — same caution applies
- `init` and `add` are interactive and not suitable for non-interactive agent calls

---

## Safe Call Pattern (Validation-First)

Recommended flow for agents before any analysis or rendering:

```
1. validate <file> --json        → check status == "ok" or "warning"
2. summary <file> --json         → read data for analysis
3. diagram <file> --format mermaid --json   → get diagram content if needed
4. search <file> <query> --json  → filter specific elements
```

Never skip step 1. If `status == "error"`, abort and surface `errors` to the user.

---

## Enum Reference

Use `zephyr reference` (human-readable) or parse directly for valid field values.

| Field              | Valid values                                                                                    |
| ------------------ | ----------------------------------------------------------------------------------------------- |
| `component.type`   | `access-gateway`, `access-policy`, `actor`, `application`, `cloud-identity`, `device-management`, `endpoint`, `identity`, `identity-provider`, `on-prem-identity`, `on-prem-resource`, `pki`, `remote-access`, `security-control` |
| `risk.severity`    | `low`, `medium`, `high`, `critical`                                                             |
| `flow.encryption`  | `none`, `tls`, `ipsec`                                                                          |
| `flow.authentication` | `none`, `password`, `mfa`, `certificate`                                                     |
| `component.exposure` | `internal`, `external`                                                                         |
| `component.lifecycle` | `planned`, `active`, `deprecated`                                                             |
| `meta.criticality` | `low`, `medium`, `high`, `mission-critical`                                                     |
| `meta.environment` | `prod`, `test`, `dev`                                                                           |
