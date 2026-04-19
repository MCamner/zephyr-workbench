from zephyr.reference import build_reference


def test_reference_contains_all_sections() -> None:
    output = build_reference()
    for section in ("Component", "Flow", "Risk", "Control", "Stakeholder", "Architecture meta"):
        assert section in output


def test_reference_contains_key_values() -> None:
    output = build_reference()
    assert "access-gateway" in output
    assert "mission-critical" in output
    assert "certificate" in output
    assert "mfa" in output
    assert "ipsec" in output
    assert "bidirectional" in output


def test_reference_lines_fit_within_80_chars() -> None:
    output = build_reference()
    for line in output.splitlines():
        assert len(line) <= 80, f"Line too long ({len(line)}): {line!r}"
