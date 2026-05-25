from __future__ import annotations

DOMAINS = ["business", "application", "data", "technology"]

COMPONENT_TYPES = [
    "access-gateway",
    "access-policy",
    "actor",
    "application",
    "cloud-identity",
    "device-management",
    "endpoint",
    "identity",
    "identity-provider",
    "on-prem-identity",
    "on-prem-resource",
    "pki",
    "remote-access",
    "security-control",
]

SEVERITIES = ["low", "medium", "high", "critical"]
LIKELIHOODS = ["low", "medium", "high"]
IMPACTS = ["low", "medium", "high"]

CONTROL_TYPES = ["policy", "technical", "process"]
STAKEHOLDER_ROLES = ["owner", "user", "operator", "security"]

ENVIRONMENTS = ["prod", "test", "dev"]
CRITICALITIES = ["low", "medium", "high", "mission-critical"]
EXPOSURES = ["internal", "external"]
LIFECYCLES = ["planned", "active", "deprecated"]
FLOW_DIRECTIONS = ["inbound", "outbound", "bidirectional"]
AUTH_TYPES = ["none", "password", "mfa", "certificate"]
ENCRYPTION_TYPES = ["none", "tls", "ipsec"]

TYPE_TO_DOMAIN = {
    "actor": "business",
    "application": "application",
    "cloud-identity": "application",
    "device-management": "application",
    "identity": "application",
    "identity-provider": "application",
    "security-control": "application",
    "access-policy": "application",
    "endpoint": "technology",
    "access-gateway": "technology",
    "remote-access": "technology",
    "pki": "technology",
    "on-prem-identity": "data",
    "on-prem-resource": "data",
}

DEFAULT_VERSION = "v1"

RISK_SCORE_MATRIX: dict[tuple[str, str], int] = {
    ("low", "low"): 1,
    ("low", "medium"): 2,
    ("low", "high"): 3,
    ("medium", "low"): 2,
    ("medium", "medium"): 4,
    ("medium", "high"): 6,
    ("high", "low"): 3,
    ("high", "medium"): 6,
    ("high", "high"): 9,
    ("critical", "low"): 4,
    ("critical", "medium"): 8,
    ("critical", "high"): 12,
}

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
