from dataclasses import dataclass, field
from typing import List

from zephyr.datamodel import COMPONENT_TYPES, SEVERITIES

ALLOWED_COMPONENT_TYPES = set(COMPONENT_TYPES)
ALLOWED_RISK_SEVERITIES = set(SEVERITIES)


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
