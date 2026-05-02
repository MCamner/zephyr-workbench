from __future__ import annotations

from zephyr.analyzer import load_architecture
from zephyr.models import Architecture, Component, Control, Flow, Risk, Stakeholder
from zephyr.search import search_architecture


def _arch(**kwargs) -> Architecture:
    defaults = dict(name="test", components=[], flows=[], risks=[], controls=[], stakeholders=[])
    return Architecture(**{**defaults, **kwargs})


def test_search_by_type() -> None:
    arch = _arch(components=[
        Component(name="vpn", type="remote-access"),
        Component(name="idp", type="identity-provider"),
    ])
    result = search_architecture(arch, "type=remote-access")
    assert "vpn" in result
    assert "idp" not in result


def test_search_by_severity() -> None:
    arch = _arch(risks=[
        Risk(id="R1", title="Critical risk", severity="high"),
        Risk(id="R2", title="Low risk", severity="low"),
    ])
    result = search_architecture(arch, "severity=high")
    assert "R1" in result
    assert "R2" not in result


def test_search_missing_field() -> None:
    arch = _arch(risks=[
        Risk(id="R1", title="No mitigation", severity="high", mitigation=""),
        Risk(id="R2", title="Has mitigation", severity="high", mitigation="Fix it."),
    ])
    result = search_architecture(arch, "missing=mitigation")
    assert "R1" in result
    assert "R2" not in result


def test_search_no_results() -> None:
    arch = _arch(components=[Component(name="vpn", type="remote-access")])
    result = search_architecture(arch, "type=actor")
    assert "No results" in result


def test_search_by_encryption() -> None:
    arch = _arch(flows=[
        Flow(source="a", target="b", label="unencrypted", encryption="none"),
        Flow(source="a", target="c", label="encrypted", encryption="tls"),
    ])
    result = search_architecture(arch, "encryption=none")
    assert "unencrypted" in result
    assert "enc:tls" not in result


def test_search_on_real_example() -> None:
    arch = load_architecture("examples/macos-intune-windows-domain.yaml")
    result = search_architecture(arch, "type=endpoint")
    assert "macbook" in result
