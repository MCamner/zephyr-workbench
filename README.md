# zephyr-workbench

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active-brightgreen)]()

**Model infrastructure. Understand flows. Generate architecture.**

CLI-based architecture workbench for modeling infrastructure, identity, and workplace systems using YAML, validation, summaries, and diagrams.

---

## 🔥 Case Study

Most architectures look right.  
Few are validated.

Zephyr models a real enterprise setup — **macOS + Intune + Entra ID + on-prem AD** — and exposes hidden risks instantly.

⚠️ Finds failure points  
🔐 Reveals trust gaps  
📐 Outputs summary + diagram in seconds  

👉 [View the full case](docs/case-macos-enterprise.md)

### Architecture preview

From model → validated → visualized:

![Architecture diagram](docs/case-diagram.png)

---

## ⚡ V1 at a glance

The first version is intentionally small and practical:

- YAML in  
- validation first  
- warnings for risky architecture patterns  
- text summary out  
- Mermaid diagram out  
- CLI first  

---

## 🚀 Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install -e ".[dev]"

python -m zephyr.cli init --minimal
python -m zephyr.cli run examples/macos-intune-windows-domain.yaml
```

👉 Fastest path:
- `init` → create model  
- `run` → validate + summary + diagram  

---

## 🎥 Demo

![Zephyr demo](docs/demo.gif)

Minimal init, end-to-end run, and diagram preview in one short terminal flow.

---

## 🧠 What it does

Zephyr Workbench helps you:

- describe infrastructure systems in a structured format  
- analyze components, flows, and risks  
- validate architecture models before rendering  
- generate architecture summaries  
- produce diagram-ready output  

Built for real-world architecture where **identity, endpoints, and trust boundaries matter**.

---

## 📐 Example output

```
Validation passed with warnings

Architecture: macos-intune-windows-domain
Components: 8
Flows: 6
Risks: 3

Risks:
- [HIGH] R1: VPN gateway as single point of failure
- [MEDIUM] R2: Certificate lifecycle not clearly defined
```

---

## 🎬 Generate diagrams

```bash
python -m zephyr.cli diagram examples/macos-intune-windows-domain.yaml --format mermaid
```

---

## 🧪 Real-world example

```bash
python -m zephyr.cli run examples/macos-intune-windows-domain.yaml
```

Models:

- macOS devices enrolled in Intune  
- Entra ID identity flows  
- Conditional Access  
- VPN and certificate-based access  
- on-prem Windows domain integration  

---

## 📦 Core model

Zephyr uses a simple structure:

- **components** → systems, endpoints, identities, controls  
- **flows** → interactions and dependencies  
- **risks** → weaknesses and failure points  

**Input:** YAML  
**Output:** structured, repeatable architecture data  

---

## 📐 V1 model contract

Required:

- `name`
- `components`
- `flows`

Optional:

- `description`
- `risks`

Validation includes:

- unique component names  
- valid flow references  
- allowed component types  
- risk severity validation  

Smart warnings:

- endpoint-to-endpoint flows  
- missing identity termination  
- single access-gateway patterns  

---

## 🧠 Why Zephyr

Architecture is usually:

- fragmented across slides  
- inconsistent between teams  
- hard to reason about  

Zephyr makes architecture:

> **executable, testable, and repeatable**

---

## 🏗️ Project structure

```
zephyr/      CLI and core logic
examples/    sample architectures
schemas/     model reference
tests/       validation and checks
docs/        case studies and assets
```

---

## 🧭 Philosophy

- model first, diagram later  
- structure over slides  
- simplicity over abstraction  
- built for real operations  

---

## 📄 Status

Early V1.

Current focus:

- stabilizing model contract  
- expanding validation  
- improving summary + diagram output  

---

## 📄 License

MIT
