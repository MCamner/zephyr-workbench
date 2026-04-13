from zephyr.analyzer import load_architecture, summarize_architecture


def test_load_and_summarize() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")
    summary = summarize_architecture(architecture)

    assert architecture.name == "secure-workplace"
    assert "Architecture: secure-workplace" in summary
    assert "Risks:" in summary
