from __future__ import annotations

from zephyr.datamodel import DEFAULT_VERSION

# Each template is a complete, valid architecture dict.
# Name and output path are filled in at init time.

_TEMPLATES: dict[str, dict] = {
    "minimal": {
        "_description": "Smallest valid model — one actor, one app, one flow, one risk.",
        "name": "my-architecture",
        "description": "",
        "meta": {"version": DEFAULT_VERSION},
        "domains": ["business", "application", "data", "technology"],
        "components": [
            {"name": "user", "type": "actor", "domain": "business", "criticality": "low", "exposure": "internal", "lifecycle": "active"},
            {"name": "app", "type": "application", "domain": "application", "criticality": "medium", "exposure": "internal", "lifecycle": "active"},
        ],
        "flows": [
            {"from": "user", "to": "app", "label": "uses", "direction": "outbound"},
        ],
        "risks": [
            {"id": "R1", "title": "Access control not defined", "severity": "medium", "likelihood": "medium", "impact": "medium"},
        ],
        "controls": [],
        "stakeholders": [],
    },

    "hybrid-identity": {
        "_description": "Cloud identity + on-prem AD — Entra ID, Conditional Access, VPN, PKI.",
        "name": "hybrid-identity",
        "description": "Hybrid identity architecture with cloud and on-prem integration.",
        "meta": {"version": DEFAULT_VERSION, "owner": "", "environment": ["prod"], "criticality": "high"},
        "domains": ["business", "application", "data", "technology"],
        "components": [
            {"name": "user", "type": "actor", "domain": "business", "criticality": "low", "exposure": "internal", "lifecycle": "active"},
            {"name": "endpoint", "type": "endpoint", "domain": "technology", "criticality": "high", "exposure": "internal", "lifecycle": "active"},
            {"name": "entra-id", "type": "cloud-identity", "domain": "application", "criticality": "mission-critical", "exposure": "external", "lifecycle": "active"},
            {"name": "conditional-access", "type": "access-policy", "domain": "application", "criticality": "high", "exposure": "external", "lifecycle": "active"},
            {"name": "on-prem-ad", "type": "on-prem-identity", "domain": "data", "criticality": "mission-critical", "exposure": "internal", "lifecycle": "active"},
            {"name": "vpn", "type": "remote-access", "domain": "technology", "criticality": "high", "exposure": "external", "lifecycle": "active"},
            {"name": "pki", "type": "pki", "domain": "technology", "criticality": "high", "exposure": "internal", "lifecycle": "active"},
            {"name": "internal-resource", "type": "on-prem-resource", "domain": "data", "criticality": "medium", "exposure": "internal", "lifecycle": "active"},
        ],
        "flows": [
            {"from": "user", "to": "endpoint", "label": "signs in", "direction": "outbound"},
            {"from": "endpoint", "to": "entra-id", "label": "authenticates", "protocol": "https", "authentication": "mfa", "encryption": "tls", "direction": "outbound"},
            {"from": "entra-id", "to": "conditional-access", "label": "evaluate policy", "protocol": "https", "encryption": "tls", "direction": "outbound"},
            {"from": "endpoint", "to": "vpn", "label": "connect", "protocol": "ipsec", "authentication": "certificate", "encryption": "ipsec", "direction": "outbound"},
            {"from": "endpoint", "to": "pki", "label": "obtain certificate", "protocol": "https", "authentication": "certificate", "encryption": "tls", "direction": "outbound"},
            {"from": "vpn", "to": "internal-resource", "label": "access", "authentication": "certificate", "encryption": "tls", "direction": "outbound"},
        ],
        "risks": [
            {"id": "R1", "title": "Single VPN gateway creates availability risk", "severity": "high", "likelihood": "medium", "impact": "high", "mitigation": "Deploy redundant VPN gateways across availability zones."},
            {"id": "R2", "title": "Trust boundary between cloud and on-prem identity unclear", "severity": "high", "likelihood": "high", "impact": "high", "mitigation": "Implement Entra ID Kerberos and enforce Conditional Access for on-prem resource access."},
            {"id": "R3", "title": "Certificate expiry may silently break access", "severity": "medium", "likelihood": "medium", "impact": "high", "mitigation": "Configure auto-renewal via SCEP and alert on upcoming expirations."},
        ],
        "controls": [
            {"name": "enforce-mfa", "type": "technical", "applies_to": ["entra-id", "conditional-access"], "description": "Require MFA for all cloud identity authentication flows."},
            {"name": "cert-renewal", "type": "process", "applies_to": ["pki", "endpoint"], "description": "Quarterly certificate review with automated SCEP renewal."},
        ],
        "stakeholders": [
            {"name": "platform-team", "role": "owner"},
            {"name": "it-security", "role": "security"},
        ],
    },

    "zero-trust": {
        "_description": "Never trust, always verify — identity-first access with MFA and policy enforcement.",
        "name": "zero-trust",
        "description": "Zero-trust architecture: all access is authenticated, authorised, and encrypted.",
        "meta": {"version": DEFAULT_VERSION, "owner": "", "environment": ["prod"], "criticality": "mission-critical"},
        "domains": ["business", "application", "data", "technology"],
        "components": [
            {"name": "user", "type": "actor", "domain": "business", "criticality": "low", "exposure": "external", "lifecycle": "active"},
            {"name": "device", "type": "endpoint", "domain": "technology", "criticality": "high", "exposure": "external", "lifecycle": "active"},
            {"name": "device-management", "type": "device-management", "domain": "application", "criticality": "high", "exposure": "external", "lifecycle": "active"},
            {"name": "identity-provider", "type": "identity-provider", "domain": "application", "criticality": "mission-critical", "exposure": "external", "lifecycle": "active"},
            {"name": "mfa-service", "type": "security-control", "domain": "application", "criticality": "mission-critical", "exposure": "external", "lifecycle": "active"},
            {"name": "access-gateway", "type": "access-gateway", "domain": "technology", "criticality": "mission-critical", "exposure": "external", "lifecycle": "active"},
            {"name": "access-policy", "type": "access-policy", "domain": "application", "criticality": "high", "exposure": "external", "lifecycle": "active"},
            {"name": "protected-resource", "type": "application", "domain": "application", "criticality": "high", "exposure": "internal", "lifecycle": "active"},
        ],
        "flows": [
            {"from": "user", "to": "device", "label": "operates", "direction": "outbound"},
            {"from": "device", "to": "device-management", "label": "enroll and attest", "protocol": "https", "authentication": "certificate", "encryption": "tls", "direction": "outbound"},
            {"from": "device", "to": "identity-provider", "label": "authenticate", "protocol": "https", "authentication": "mfa", "encryption": "tls", "direction": "outbound"},
            {"from": "identity-provider", "to": "mfa-service", "label": "verify second factor", "protocol": "https", "encryption": "tls", "direction": "outbound"},
            {"from": "identity-provider", "to": "access-policy", "label": "evaluate trust signal", "protocol": "https", "encryption": "tls", "direction": "outbound"},
            {"from": "device", "to": "access-gateway", "label": "request access", "protocol": "https", "authentication": "certificate", "encryption": "tls", "direction": "outbound"},
            {"from": "access-gateway", "to": "protected-resource", "label": "forward authorised request", "protocol": "https", "encryption": "tls", "direction": "outbound"},
        ],
        "risks": [
            {"id": "R1", "title": "Identity provider is a single point of trust failure", "severity": "critical", "likelihood": "low", "impact": "high", "mitigation": "Deploy identity provider in high-availability configuration with failover."},
            {"id": "R2", "title": "Device attestation not enforced at access gateway", "severity": "high", "likelihood": "medium", "impact": "high", "mitigation": "Require device compliance signal from device-management before forwarding requests."},
            {"id": "R3", "title": "Access policy gaps may allow lateral movement", "severity": "high", "likelihood": "medium", "impact": "high", "mitigation": "Apply least-privilege policies per resource and review quarterly."},
        ],
        "controls": [
            {"name": "continuous-verification", "type": "technical", "applies_to": ["identity-provider", "access-gateway", "access-policy"], "description": "Re-verify identity and device posture on every request, not just at login."},
            {"name": "least-privilege-policy", "type": "policy", "applies_to": ["access-policy", "protected-resource"], "description": "Grant minimum required permissions per resource; no standing access."},
            {"name": "access-review", "type": "process", "applies_to": ["access-policy"], "description": "Quarterly review of all access policies and permission grants."},
        ],
        "stakeholders": [
            {"name": "security-team", "role": "security"},
            {"name": "platform-team", "role": "owner"},
            {"name": "end-users", "role": "user"},
        ],
    },
}


def list_templates() -> str:
    lines = ["Available templates:", ""]
    for name, template in _TEMPLATES.items():
        desc = template.get("_description", "")
        lines.append(f"  {name:<20}{desc}")
    lines.append("")
    lines.append("Usage: zephyr init --template <name>")
    return "\n".join(lines)


def get_template(name: str) -> dict | None:
    template = _TEMPLATES.get(name)
    if template is None:
        return None
    # return a copy without the internal _description key
    return {k: v for k, v in template.items() if not k.startswith("_")}


def template_names() -> list[str]:
    return list(_TEMPLATES.keys())
