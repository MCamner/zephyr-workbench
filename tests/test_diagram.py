from zephyr.analyzer import load_architecture
from zephyr.diagram import to_mermaid


def test_to_mermaid_contains_nodes_and_edges() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")

    diagram = to_mermaid(architecture)

    assert 'user["user (actor)"]' in diagram
    assert "user -->|signs in| igel" in diagram
