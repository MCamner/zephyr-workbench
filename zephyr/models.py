from dataclasses import dataclass, field


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
    components: list[Component] = field(default_factory=list)
    flows: list[Flow] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)
