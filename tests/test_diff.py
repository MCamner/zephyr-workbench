from zephyr.diff import ArchitectureDiff, Change, diff_architectures, format_diff
from zephyr.models import Architecture, Component, Control, Flow, Risk, Stakeholder


def _arch(**kwargs) -> Architecture:
    defaults = dict(name="test", components=[], flows=[], risks=[], controls=[], stakeholders=[])
    return Architecture(**{**defaults, **kwargs})


# ── diff_architectures ───────────────────────────────────────────────────────

def test_identical_architectures_produce_empty_diff() -> None:
    a = _arch(components=[Component(name="vpn", type="remote-access")])
    diff = diff_architectures(a, a)
    assert diff.is_empty()


def test_added_component_detected() -> None:
    a = _arch(components=[Component(name="vpn", type="remote-access")])
    b = _arch(components=[
        Component(name="vpn", type="remote-access"),
        Component(name="idp", type="identity-provider"),
    ])
    diff = diff_architectures(a, b)
    assert len(diff.components) == 1
    assert diff.components[0].status == "added"
    assert "idp" in diff.components[0].label


def test_removed_component_detected() -> None:
    a = _arch(components=[
        Component(name="vpn", type="remote-access"),
        Component(name="idp", type="identity-provider"),
    ])
    b = _arch(components=[Component(name="vpn", type="remote-access")])
    diff = diff_architectures(a, b)
    assert len(diff.components) == 1
    assert diff.components[0].status == "removed"
    assert "idp" in diff.components[0].label


def test_modified_component_field_detected() -> None:
    a = _arch(components=[Component(name="vpn", type="remote-access", criticality="low")])
    b = _arch(components=[Component(name="vpn", type="remote-access", criticality="high")])
    diff = diff_architectures(a, b)
    assert len(diff.components) == 1
    assert diff.components[0].status == "modified"
    assert diff.components[0].fields == [("criticality", "low", "high")]


def test_added_flow_detected() -> None:
    a = _arch(flows=[])
    b = _arch(flows=[Flow(source="a", target="b", label="connects")])
    diff = diff_architectures(a, b)
    assert len(diff.flows) == 1
    assert diff.flows[0].status == "added"


def test_modified_flow_authentication_detected() -> None:
    a = _arch(flows=[Flow(source="a", target="b", label="sign-in", authentication="password")])
    b = _arch(flows=[Flow(source="a", target="b", label="sign-in", authentication="mfa")])
    diff = diff_architectures(a, b)
    assert len(diff.flows) == 1
    assert diff.flows[0].status == "modified"
    assert diff.flows[0].fields == [("authentication", "password", "mfa")]


def test_risk_severity_change_detected() -> None:
    a = _arch(risks=[Risk(id="R1", title="Gateway SPOF", severity="medium")])
    b = _arch(risks=[Risk(id="R1", title="Gateway SPOF", severity="high")])
    diff = diff_architectures(a, b)
    assert len(diff.risks) == 1
    assert diff.risks[0].status == "modified"
    assert diff.risks[0].fields == [("severity", "medium", "high")]


def test_control_applies_to_change_detected() -> None:
    a = _arch(controls=[Control(name="mfa-policy", type="technical", applies_to=["vpn"])])
    b = _arch(controls=[Control(name="mfa-policy", type="technical", applies_to=["vpn", "idp"])])
    diff = diff_architectures(a, b)
    assert len(diff.controls) == 1
    assert diff.controls[0].status == "modified"
    assert diff.controls[0].fields[0][0] == "applies_to"


def test_stakeholder_role_change_detected() -> None:
    a = _arch(stakeholders=[Stakeholder(name="ops-team", role="operator")])
    b = _arch(stakeholders=[Stakeholder(name="ops-team", role="owner")])
    diff = diff_architectures(a, b)
    assert len(diff.stakeholders) == 1
    assert diff.stakeholders[0].status == "modified"


# ── format_diff ──────────────────────────────────────────────────────────────

def test_format_diff_no_changes() -> None:
    a = _arch()
    diff = diff_architectures(a, a, source="v1.yaml", target="v2.yaml")
    output = format_diff(diff)
    assert "No changes detected." in output
    assert "v1.yaml → v2.yaml" in output


def test_format_diff_shows_symbols() -> None:
    a = _arch(components=[Component(name="vpn", type="remote-access")])
    b = _arch(components=[
        Component(name="vpn", type="remote-access", criticality="high"),
        Component(name="idp", type="identity-provider"),
    ])
    diff = diff_architectures(a, b)
    output = format_diff(diff)
    assert "  + idp" in output
    assert "  ~ vpn" in output
    assert "criticality" in output


def test_format_diff_lists_unchanged_sections() -> None:
    a = _arch(components=[Component(name="vpn", type="remote-access")])
    b = _arch(components=[Component(name="idp", type="identity-provider")])
    diff = diff_architectures(a, b)
    output = format_diff(diff)
    assert "No changes: flows, risks, controls, stakeholders" in output
