from zephyr.models import Architecture


def _node_id(name: str) -> str:
    return name.replace("-", "_").replace(" ", "_")


def to_mermaid(architecture: Architecture) -> str:
    lines = ["graph TD"]

    for component in architecture.components:
        node_id = _node_id(component.name)
        lines.append(f'    {node_id}["{component.name} ({component.type})"]')

    for flow in architecture.flows:
        source = _node_id(flow.source)
        target = _node_id(flow.target)
        if flow.label:
            lines.append(f"    {source} -->|{flow.label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)
