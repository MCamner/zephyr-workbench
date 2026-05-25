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

Stabilize the core architecture model and validation engine before expanding into advanced AI-assisted workflows.

---

## v0.1.1 — Validation Stabilization

- [x] Stronger validation rules
- [x] Dependency validation
- [x] Circular dependency detection
- [x] Trust boundary validation
- [x] Architecture consistency checks
- [ ] Improved markdown summaries
- [ ] Normalize output formats
- [ ] Mermaid rendering consistency
- [ ] More enterprise examples (Intune + Entra, Citrix + IGEL, Zero Trust)

---

## v0.2.0 — Schema Expansion

- [ ] Richer infrastructure schemas
- [ ] Network topology modeling
- [ ] Trust boundary support
- [ ] IAM / identity modeling
- [ ] Application dependency mapping
- [ ] Endpoint and device modeling
- [ ] Cloud provider abstractions
- [ ] Risk scoring
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

## v0.4.0 — Diagram Intelligence

Bridge visual architecture and structured architecture models.

- [ ] Mermaid reverse parsing
- [ ] draw.io import experiments
- [ ] Image-to-architecture workflows
- [ ] Architecture OCR pipelines
- [ ] Component detection from diagrams

### mq-image-analyze Integration

```
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
|---|---|
| mq-image-analyze | Visual architecture interpretation, diagram → YAML |
| repo-signal | Architecture repo cognition |
| mq-agent | Workflow orchestration |
| mq-mcp | Tool execution and runtime integration |
