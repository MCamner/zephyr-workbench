# zephyr-workbench

> Architecture workbench for modeling, analyzing, and visualizing infrastructure systems and flows.

Zephyr Workbench is a practical tool for turning architecture ideas into structured models, risk analysis, and diagram-ready output.

It is designed for real-world infrastructure work — especially where identity, endpoint, access, trust boundaries, and operational dependencies matter.

---

## Why

Architecture work often lives in scattered notes, diagrams, and mental models.

Zephyr Workbench aims to make that work more structured by giving you a simple way to:

* describe a system
* analyze dependencies and risks
* generate architecture summaries
* produce diagram-ready output

---

## V1 focus

The first version will focus on:

* YAML-based architecture input
* CLI analysis commands
* Mermaid diagram generation
* structured summaries for architecture reviews
* export-friendly output for documentation and draw.io workflows

---

## Example use cases

* model a Citrix + IGEL + identity flow
* map trust boundaries in a secure workplace design
* identify single points of failure
* generate a first-pass architecture summary
* produce Mermaid diagrams from a simple system definition

---

## Example workflow

Define an environment in YAML:

```yaml
name: secure-workplace
components:
  - igel
  - citrix-gateway
  - active-directory
  - entra-id
  - mfa
flows:
  - user -> igel
  - igel -> citrix-gateway
  - citrix-gateway -> active-directory
  - active-directory -> mfa
```

Run analysis:

```bash
zephyr analyze examples/secure-workplace.yaml
```

Generate a diagram:

```bash
zephyr diagram examples/secure-workplace.yaml --format mermaid
```

---

## Planned commands

```bash
zephyr analyze <file>
zephyr summary <file>
zephyr diagram <file> --format mermaid
zephyr export <file> --format drawio
```

---

## Output goals

Zephyr Workbench should help produce:

* architecture summaries
* dependency views
* risk observations
* Mermaid diagrams
* draw.io-friendly structure

---

## Project direction

This is not a generic note-taking tool or another dashboard.

The goal is to build a focused architecture workbench for:

* infrastructure
* identity
* endpoint architecture
* access flows
* secure workplace design

---

## Initial structure

```text
zephyr-workbench/
├── README.md
├── examples/
│   ├── secure-workplace.yaml
│   └── identity-flow.yaml
├── schemas/
│   └── architecture.schema.yaml
├── docs/
│   └── diagrams/
├── zephyr/
│   ├── __init__.py
│   ├── cli.py
│   ├── analyzer.py
│   ├── diagram.py
│   └── models.py
└── tests/
```

---

## Status

Early project setup.

The current goal is to define the model, CLI shape, and first useful outputs before expanding into richer export or UI options.

---

## License

MIT

