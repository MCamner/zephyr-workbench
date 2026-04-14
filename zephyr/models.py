from dataclasses import dataclass, field
from typing import List

ALLOWED_COMPONENT_TYPES = {
    "actor",
    "access-gateway",
    "access-policy",
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
}

ALLOWED_RISK_SEVERITIES = {"low", "medium", "high", "critical"}


@dataclass
class Component:
    name: str
    type: str


@dataclass
class Flow:
    source: str
    target: str
    label: str = ""


@dataclass
class Risk:
    id: str
    title: str
    severity: str


@dataclass
class Architecture:
    name: str
    description: str = ""
    components: List[Component] = field(default_factory=list)
    flows: List[Flow] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
