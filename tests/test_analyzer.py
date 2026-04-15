from zephyr.analyzer import load_architecture, summarize_architecture, summarize_architecture_data


def test_load_and_summarize() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")
    summary = summarize_architecture(architecture)

    assert architecture.name == "secure-workplace"
    assert "Architecture: secure-workplace" in summary
    assert "Risks:" in summary


def test_summarize_architecture_data_returns_structured_counts() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")

    summary = summarize_architecture_data(architecture)

    assert summary["name"] == "secure-workplace"
    assert summary["components"] == 6
    assert summary["flows"] == 5
    assert summary["risks"] == 2
    assert summary["risk_details"][0]["id"] == "R1"
