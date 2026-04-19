from zephyr.models import Architecture

_TYPE_TO_CLASS = {
    "actor": "actor",
    "endpoint": "endpoint",
    "identity": "identity",
    "identity-provider": "identity",
    "cloud-identity": "identity",
    "on-prem-identity": "identity",
    "access-gateway": "gateway",
    "remote-access": "gateway",
    "access-policy": "policy",
    "security-control": "policy",
    "device-management": "mgmt",
    "pki": "mgmt",
    "application": "app",
    "on-prem-resource": "app",
}

_CLASS_DEFS = {
    "actor":    "fill:#d4edda,stroke:#28a745,color:#000",
    "endpoint": "fill:#e2e3e5,stroke:#6c757d,color:#000",
    "identity": "fill:#e2d9f3,stroke:#6f42c1,color:#000",
    "gateway":  "fill:#fff3cd,stroke:#fd7e14,color:#000",
    "policy":   "fill:#cce5ff,stroke:#004085,color:#000",
    "mgmt":     "fill:#d1ecf1,stroke:#0c5460,color:#000",
    "app":      "fill:#f8d7da,stroke:#721c24,color:#000",
}


def _node_id(name: str) -> str:
    return name.replace("-", "_").replace(" ", "_")


def _flow_label(label: str, authentication: str, encryption: str) -> str:
    parts = [p for p in [label, authentication, encryption] if p]
    return " | ".join(parts) if parts else ""


def to_mermaid(architecture: Architecture) -> str:
    lines = ["graph TD"]
    lines.append("")

    # classDef blocks
    for class_name, style in _CLASS_DEFS.items():
        lines.append(f"    classDef {class_name} {style}")
    lines.append("")

    # nodes
    class_assignments: list[tuple[str, str]] = []
    for component in architecture.components:
        node_id = _node_id(component.name)
        lines.append(f'    {node_id}["{component.name} ({component.type})"]')
        css_class = _TYPE_TO_CLASS.get(component.type)
        if css_class:
            class_assignments.append((node_id, css_class))

    if class_assignments:
        lines.append("")
        for node_id, css_class in class_assignments:
            lines.append(f"    class {node_id} {css_class}")

    lines.append("")

    # edges
    for flow in architecture.flows:
        source = _node_id(flow.source)
        target = _node_id(flow.target)
        label = _flow_label(flow.label, flow.authentication, flow.encryption)
        if label:
            lines.append(f"    {source} -->|{label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)
