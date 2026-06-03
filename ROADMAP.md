# Roadmap

Zephyr Workbench is evolving into a terminal-native architecture intelligence and validation platform.

The long-term goal is to support:

- architecture modeling
- validation
- architecture cognition
- diagram generation
- semantic architecture analysis
- AI-assisted architecture workflows
- architecture risk detection
- infrastructure documentation pipelines

---

## Current Focus

Current: v0.3.1 — MCP runtime contracts shipped.
Next:    mq-mcp Zephyr adapter — wire runtime.py into mq-mcp tool gateway.

Focus on machine-readable outputs, safe tool boundaries, and validation-first execution before adding broader review automation.

Current slice shipped: `validate --json` returns `zephyr-result.v1` envelopes for ok, warning, and error cases.

---

## v0.1.1 — Validation Stabilization

- [x] Stronger validation rules
- [x] Dependency validation
- [x] Circular dependency detection
- [x] Trust boundary validation
- [x] Architecture consistency checks
- [x] Improved markdown summaries
- [x] Normalize output formats
- [x] Mermaid rendering consistency
- [x] More enterprise examples (Intune + Entra, Citrix + IGEL, Zero Trust)

---

## v0.2.0 — Schema Expansion

- [x] Trust boundary support (`trust_boundaries` list, `trust_boundary` on components)
- [x] Risk scoring (severity × likelihood matrix, computed score in summary)
- [x] Richer component schema (`tags`, extended fields)
- [x] Mermaid subgraph rendering per trust boundary
- [x] Trust boundary validation (unknown reference warnings)
- [ ] Network topology modeling
- [ ] IAM / identity modeling
- [ ] Application dependency mapping
- [ ] Endpoint and device modeling
- [ ] Cloud provider abstractions
- [ ] Policy validation

---

## v0.3.0 — Architecture Intelligence

Introduce architecture cognition and semantic analysis.

- [ ] Semantic architecture search
- [ ] Architecture summarization
- [ ] Architecture drift detection
- [ ] Architecture comparison
- [ ] Dependency reasoning
- [ ] Architecture risk analysis
- [ ] AI-assisted architecture reviews
- [ ] YAML improvement suggestions
- [ ] Risk explanation workflows
- [ ] Architecture anti-pattern detection

---

## v0.3.1 — MCP Runtime Contracts

Make Zephyr easier to call safely from mq-mcp, agents, scripts, and local automation.

- [x] Normalize JSON result envelopes across validation, summary, diagram, diff, and search
- [x] Add explicit status, errors, warnings, artifacts, and metadata fields to `validate --json` output
- [x] Ensure CLI output can be consumed without parsing human-oriented terminal text
- [x] Document read-only tool contracts for architecture inspection
- [x] Define write-safe contracts for YAML suggestions and generated artifacts
- [x] Add contract tests for representative valid, warning, and error validation cases
- [x] Keep human CLI output stable while improving structured output

### mq-mcp Integration

Expose Zephyr as a safe tool runtime for agents and local MCP clients.

- [x] Stable JSON output contracts for validation, summary, diagram, diff, and search
- [x] Read-only MCP tools for inspecting architecture models (Python API in runtime.py)
- [x] Validation-first MCP tool flow: validate → summary/diagram/search
- [x] Explicit write controls for generated YAML suggestions (contracts.py + requires_write_intent)
- [x] Tool result schemas that agents can consume without parsing terminal text
- [x] Guardrails for risky operations: forbidden safety class blocks init/add from agent calls

---

## v0.4.0 — Diagram Intelligence

Bridge visual architecture and structured architecture models.

- [ ] Mermaid reverse parsing
- [ ] draw.io import experiments
- [ ] Image-to-architecture workflows
- [ ] Architecture OCR pipelines
- [ ] Component detection from diagrams

### mq-image-analyze Integration

```text
diagram.png
  ↓
mq-image-analyze
  ↓
Zephyr YAML
  ↓
validation
  ↓
Mermaid / HTML / report output
```

---

## v0.5.0 — Architecture Review Platform

- [ ] Architecture scoring
- [ ] Review templates
- [ ] Architecture review reports
- [ ] Architecture lifecycle tracking
- [ ] Change impact analysis
- [ ] Release architecture snapshots
- [ ] Architecture governance workflows

---

## v0.6.0 — Semantic Architecture Memory

- [ ] Architecture vector indexing
- [ ] Semantic architecture memory
- [ ] Architecture history tracking
- [ ] Architecture evolution analysis
- [ ] Cross-project architecture comparison

---

## Long-Term Vision

Zephyr Workbench becomes:

- Architecture cognition engine
- Infrastructure reasoning platform
- Architecture validation runtime
- AI-assisted architecture review system

**Not:**

- Generic diagram tool
- GUI-first modeling platform
- Enterprise bloatware

---

## Design Principles

**Terminal-first** — CLI remains primary interface.

**YAML-first** — Structured architecture definitions are the source of truth.

**Validation-first** — Architecture must be testable, reviewable, explainable, versionable.

**AI-assisted, not AI-controlled** — AI assists, explains, validates, summarizes. It does not autonomously redesign, silently modify, or hide reasoning.

---

## Non-Goals

Do NOT build:

- Electron apps or heavy GUI systems
- Drag-and-drop editors
- Autonomous architecture generation
- Black-box AI workflows
- Cloud-only platform dependencies

---

## Ecosystem Integration

| System | Role |
| --- | --- |
| mq-image-analyze | Visual architecture interpretation, diagram → YAML |
| repo-signal | Architecture repo cognition |
| mq-agent | Workflow orchestration |
| mq-mcp | Tool execution and runtime integration |
