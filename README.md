# zephyr-workbench

Architecture workbench for modeling, analyzing, and visualizing infrastructure systems and flows.

## V1 scope

The first version is intentionally small:

- YAML in
- text summary out
- Mermaid diagram out
- CLI first

## Project structure

- `zephyr/` contains the Python package and CLI
- `examples/` contains sample architecture inputs
- `schemas/` contains a human-readable V1 schema reference
- `docs/diagrams/` is reserved for rendered outputs
- `tests/` contains lightweight checks

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m zephyr.cli summary examples/secure-workplace.yaml
python -m zephyr.cli diagram examples/secure-workplace.yaml --format mermaid
```

## Example output

```text
Architecture: secure-workplace
Components: 6
Flows: 5
Risks: 2

Risks:
- [HIGH] R1: Citrix Gateway single point of failure
- [MEDIUM] R2: MFA dependency not clearly documented
```
