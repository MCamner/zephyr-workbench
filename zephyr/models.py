from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from zephyr.datamodel import COMPONENT_TYPES, SEVERITIES

ALLOWED_COMPONENT_TYPES = set(COMPONENT_TYPES)
ALLOWED_RISK_SEVERITIES = set(SEVERITIES)


@dataclass
class Meta:
    owner: str = ""
    version: str = ""
    criticality: str = ""
    environment: List[str] = field(default_factory=list)


@dataclass
class Component:
    name: str
    type: str
    description: str = ""
    domain: str = ""
    criticality: str = ""
    exposure: str = ""
    lifecycle: str = ""


@dataclass
class Flow:
    source: str
    target: str
    label: str = ""
    protocol: str = ""
    authentication: str = ""
    encryption: str = ""
    direction: str = ""


@dataclass
class Risk:
    id: str
    title: str
    severity: str
    description: str = ""
    mitigation: str = ""
    likelihood: str = ""
    impact: str = ""


@dataclass
class Control:
    name: str
    type: str
    applies_to: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Stakeholder:
    name: str
    role: str


@dataclass
class Architecture:
    name: str
    description: str = ""
    meta: Optional[Meta] = None
    components: List[Component] = field(default_factory=list)
    flows: List[Flow] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    controls: List[Control] = field(default_factory=list)
    stakeholders: List[Stakeholder] = field(default_factory=list)
