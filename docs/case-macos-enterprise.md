# Case Study: macOS Enterprise Architecture (Intune + Entra ID + On-Prem AD)

## Overview

Modern enterprise environments are no longer single-stack.

They are hybrid by default:

* cloud identity (Entra ID)
* device management (Intune)
* legacy dependencies (on-prem AD)
* multiple trust boundaries (VPN, certificates, conditional access)

This case shows how Zephyr Workbench turns that complexity into a **structured, validated, and explainable architecture model**.

---

## The Problem

Architecture for modern workplace environments is typically:

* spread across slides, diagrams, and documents
* inconsistent between teams
* hard to validate before implementation
* difficult to reason about end-to-end

Key challenges in this scenario:

* How identity flows between Entra ID and on-prem AD
* How macOS devices establish trust (certificates, MDM, VPN)
* Where Conditional Access is enforced
* What happens if a critical component fails
* Whether dependencies are clearly defined

Traditional diagrams show *what exists* —
but not whether it is **correct, complete, or risky**.

---

## Scenario

This model represents a typical enterprise setup:

* macOS devices enrolled in Intune
* Identity managed in Entra ID
* Conditional Access enforcing access policies
* Certificate-based authentication for secure access
* VPN or secure gateway for internal resources
* Integration with on-prem Active Directory

---

## Zephyr Approach

Instead of drawing diagrams first, we define the architecture as **structured YAML**.

### Input Model (YAML)

```yaml
name: macos-intune-enterprise
description: macOS devices with Intune, Entra ID, Conditional Access and on-prem AD integration

components:
  - name: macbook
    type: endpoint

  - name: intune
    type: device-management

  - name: entra-id
    type: cloud-identity

  - name: conditional-access
    type: access-policy

  - name: vpn-gateway
    type: remote-access

  - name: active-directory
    type: on-prem-identity

  - name: certificate-authority
    type: pki

flows:
  - from: macbook
    to: intune
    label: enrolls device

  - from: macbook
    to: entra-id
    label: user sign-in

  - from: entra-id
    to: conditional-access
    label: policy evaluation

  - from: macbook
    to: vpn-gateway
    label: secure access

  - from: vpn-gateway
    to: active-directory
    label: resource access

  - from: certificate-authority
    to: macbook
    label: issues device certificate

risks:
  - id: R1
    title: VPN gateway as single point of failure
    severity: high

  - id: R2
    title: Certificate lifecycle not clearly defined
    severity: medium
```

---

## Validation Output

When running:

```
zephyr validate examples/macos-intune-enterprise.yaml
```

Example output:

```
Validation passed with warnings

Warnings:
- W1: only one remote-access component detected (vpn-gateway)
- W2: certificate dependency not explicitly linked to identity flow
```

### What this means

* The architecture is structurally valid
* But contains potential weaknesses that require attention
* Issues are detected **before implementation**, not after

---

## Generated Summary

```
Architecture: macos-intune-enterprise
Components: 7
Flows: 6
Risks: 2

Risks:
- [HIGH] R1: VPN gateway as single point of failure
- [MEDIUM] R2: Certificate lifecycle not clearly defined
```

### Why this matters

This turns architecture into:

* something measurable
* something comparable
* something reviewable in seconds

---

## Generated Diagram (Mermaid)

```
graph TD
    macbook["macbook (endpoint)"]
    intune["intune (device-management)"]
    entra["entra-id (cloud-identity)"]
    ca["conditional-access (access-policy)"]
    vpn["vpn-gateway (remote-access)"]
    ad["active-directory (on-prem-identity)"]
    pki["certificate-authority (pki)"]

    macbook -->|enrolls device| intune
    macbook -->|user sign-in| entra
    entra -->|policy evaluation| ca
    macbook -->|secure access| vpn
    vpn -->|resource access| ad
    pki -->|issues device certificate| macbook
```

---

## What Zephyr Reveals

From this model, an architect can immediately see:

### 1. Single Points of Failure

* VPN gateway is critical and unprotected
  → requires redundancy or alternative access path

### 2. Trust Dependencies

* Certificate authority is not clearly tied to identity validation
  → unclear trust chain

### 3. Flow Gaps

* Conditional Access is evaluated, but not enforced downstream
  → missing linkage in access path

### 4. Architecture Clarity

* All components and flows are explicit
  → no hidden assumptions

---

## Before vs After

### Before (traditional approach)

* Diagram exists
* Assumptions are implicit
* Risks are discussed verbally
* Validation happens late

### After (Zephyr)

* Architecture is defined as code
* Validation happens early
* Risks are explicit
* Output is consistent and repeatable

---

## Why This Matters

Zephyr changes architecture from:

> static documentation

into:

> executable, testable structure

This enables:

* faster reviews
* clearer decisions
* better risk visibility
* reusable architecture patterns

---

## When to Use This

This approach is especially useful for:

* enterprise workplace design
* identity and access architecture
* zero trust modeling
* hybrid cloud + on-prem environments
* architecture reviews and pre-studies

---

## Next Steps

* Extend the model with:

  * MFA components
  * device compliance states
  * multiple access paths

* Add validation rules for:

  * identity trust chains
  * certificate dependencies
  * policy enforcement coverage

* Integrate into:

  * architecture review workflows
  * CI pipelines for validation

---

## Takeaway

You don’t need more diagrams.

You need **structure before diagrams**.

Zephyr provides that structure.
