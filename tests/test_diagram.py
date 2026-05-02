from __future__ import annotations

from zephyr.analyzer import load_architecture
from zephyr.diagram import to_html, to_mermaid


def test_to_mermaid_contains_nodes_and_edges() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")

    diagram = to_mermaid(architecture)

    assert 'user["user (actor)"]' in diagram
    assert "user -->|signs in| igel" in diagram


def test_to_html_is_valid_html_with_mermaid_content() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")

    html = to_html(architecture)

    assert "<!DOCTYPE html>" in html
    assert "<title>secure-workplace</title>" in html
    assert "mermaid.min.js" in html
    assert 'class="mermaid"' in html
    assert 'user["user (actor)"]' in html


def test_to_html_includes_description_when_present() -> None:
    architecture = load_architecture("examples/macos-intune-windows-domain.yaml")

    html = to_html(architecture)

    assert 'class="description"' in html
    assert "Enterprise macOS" in html


def test_to_html_omits_description_block_when_empty() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")

    html = to_html(architecture)

    assert 'class="description"' not in html


def test_to_html_contains_mermaid_graph() -> None:
    architecture = load_architecture("examples/macos-intune-windows-domain.yaml")

    html = to_html(architecture)

    assert "graph TD" in html
    assert "classDef" in html
