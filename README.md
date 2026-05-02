# zephyr-workbench

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![CI](https://github.com/MCamner/zephyr-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/MCamner/zephyr-workbench/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/MCamner/zephyr-workbench)

**Model infrastructure. Understand flows. Generate architecture.**

CLI-based architecture workbench for modeling infrastructure, identity, and workplace systems using YAML, validation, summaries, and diagrams.

---

## Case Study

Most architectures look right.
Few are validated.

Zephyr models a real enterprise setup — **macOS + Intune + Entra ID + on-prem AD** — and exposes hidden risks instantly.

- Finds failure points
- Reveals trust gaps
- Outputs summary + diagram in seconds

[View the full case](docs/case-macos-enterprise.md)

### Architecture preview

From model → validated → visualized:

![Architecture diagram](docs/case-diagram.png)

---

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

```bash
zephyr init --minimal          # create a model interactively
zephyr run examples/macos-intune-windows-domain.yaml
```

**Fastest path:** `init` → create model, `run` → validate + summary + diagram

---

## Demo

![Zephyr demo](docs/demo.gif)

Minimal init, end-to-end run, and diagram preview in one short terminal flow.

---

## What it does

Zephyr Workbench helps you:

- Describe infrastructure systems in a structured YAML format
- Validate models before rendering — errors block, warnings inform
- Generate structured summaries: components, flows, risks, controls, stakeholders
- Produce Mermaid or HTML diagrams
- Diff two models to see what changed
- Search across components, flows, and risks by field value

Built for real-world architecture where **identity, endpoints, and trust boundaries matter**.

---

## Commands

| Command | What it does |
| ------- | ------------ |
| `zephyr run <file>` | Validate + summary + diagram in one step |
| `zephyr validate <file>` | Check for errors and warnings |
| `zephyr summary <file>` | Print structured summary (`--json` for machine output) |
| `zephyr diagram <file>` | Generate diagram (`--format mermaid\|html\|png`) |
| `zephyr diff <a> <b>` | Compare two models, exits 1 if changes exist |
| `zephyr add <file>` | Add components, flows, risks, controls, or stakeholders interactively |
| `zephyr search <file> <query>` | Filter by field, e.g. `type=endpoint`, `severity=high`, `missing=mitigation` |
| `zephyr init` | Create a new model (wizard or `--template <name>`) |
| `zephyr templates` | List available starter templates |
| `zephyr reference` | Show all valid field values |
| `zephyr help` | Full usage guide |

### Useful flags

```bash
zephyr run <file> --format html --open      # open diagram in browser immediately
zephyr run <file> --format html --watch     # live-reload on file changes
zephyr summary <file> --json               # machine-readable output
zephyr diagram <file> --format png         # PNG export (requires mmdc)
```

---

## Example output

```text
zephyr run examples/macos-intune-windows-domain.yaml
```

```text
Validation passed

Architecture: macos-intune-windows-domain
Owner:        platform-team
Version:      v1
Criticality:  mission-critical
Environment:  prod
Components:   8
Flows:        6
Risks:        3
Controls:     3
Stakeholders: 3

Risks:
- [HIGH] R1: Unclear trust boundary between Entra-managed identity and on-prem domain access
  likelihood: high | impact: high
  Mitigation: Implement Entra ID Kerberos to bridge cloud and on-prem identity.

- [MEDIUM] R2: Certificate dependency not documented for secure access
  likelihood: medium | impact: high
  Mitigation: Configure SCEP-based auto-renewal via Intune.

Diagram generated: output/macos-intune-windows-domain.mmd
```

---

## Model structure

Every model is a YAML file. The full schema is at `schemas/architecture.schema.yaml`.

**Required:**

```yaml
name: my-architecture
components:
  - name: api
    type: application
flows:
  - from: api
    to: api
    label: self
```

**Optional top-level fields:**

| Field | Description |
| ----- | ----------- |
| `description` | Free-text description shown in summary |
| `meta` | Owner, version, criticality, environment |
| `risks` | Weaknesses with severity, likelihood, impact, mitigation |
| `controls` | Technical, policy, or process measures with `applies_to` |
| `stakeholders` | People or teams with roles |
| `rules` | Per-model required fields that generate warnings |

**Example with meta:**

```yaml
meta:
  owner: platform-team
  version: v1
  criticality: mission-critical
  environment: [prod]
```

**Example rules block:**

```yaml
rules:
  require:
    component: [criticality, domain]
    risk: [mitigation]
```

---

## Validation

**Errors** block the pipeline:

- Missing required fields (`name`, `components`, `flows`)
- Invalid field values (component type, risk severity, etc.)
- Duplicate component names or risk IDs
- Flow references to non-existent components

**Warnings** flag risky patterns:

- Endpoint-to-endpoint flows
- Single access-gateway (SPOF)
- MFA flow targeting a non-identity component
- Custom per-model rules via `rules.require`

---

## Project structure

```text
zephyr/      CLI and core logic
  loader.py      YAML loading and model construction
  validation.py  Validation rules and warnings
  analyzer.py    Summary generation
  diagram.py     Mermaid and HTML rendering
  diff.py        Model comparison
  search.py      Field filtering
  add.py         Interactive item addition
  init_wizard.py Model creation wizard
  templates.py   Starter templates
  reference.py   Valid field values
examples/    Sample architectures
schemas/     Field reference (architecture.schema.yaml)
tests/       88 tests
docs/        Case studies and assets
```

---

## Why Zephyr

Architecture is usually:

- Fragmented across slides
- Inconsistent between teams
- Hard to reason about
- Difficult to validate before implementation

Zephyr makes architecture:

> **Executable, testable, and repeatable**

Define once → validate → analyze → visualize → reuse.

---

## Philosophy

- Model first, diagram later
- Structure over slides
- Simplicity over abstraction
- Built for real operations

---

## License

MIT
