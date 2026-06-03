"""Tests for zephyr/memory.py and runtime memory functions."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from zephyr.memory import (
    ComparisonResult,
    IndexedModel,
    MemoryError,
    SearchResult,
    add_to_memory,
    compare_architectures,
    default_index_dir,
    detect_patterns,
    extract_keywords,
    format_comparison,
    format_memory_list,
    format_search_results,
    list_memory,
    remove_from_memory,
    search_memory,
)
from zephyr.models import (
    Architecture, Component, Control, Flow, Meta, Risk, TrustBoundary,
)
from zephyr.runtime import (
    memory_add,
    memory_compare,
    memory_list,
    memory_remove,
    memory_search,
)


EXAMPLES = Path(__file__).parent.parent / "examples"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def idx_dir(tmp_path):
    return tmp_path / ".zephyr" / "memory"


def _arch_a() -> Architecture:
    return Architecture(
        name="platform-a",
        description="An API-gateway-backed platform",
        meta=Meta(owner="team-a", version="1.0"),
        components=[
            Component(name="gw", type="access-gateway", criticality="high",
                      description="API Gateway", exposure="external"),
            Component(name="api", type="service", criticality="high", description="Main API"),
            Component(name="db", type="data-store", criticality="medium", description="DB"),
        ],
        flows=[Flow(source="gw", target="api"), Flow(source="api", target="db")],
        trust_boundaries=[TrustBoundary(name="dmz")],
        risks=[Risk(id="R01", title="Injection risk", severity="high", mitigation="WAF")],
    )


def _arch_b() -> Architecture:
    return Architecture(
        name="platform-b",
        description="An identity-driven microservices platform",
        meta=Meta(owner="team-b", version="2.0"),
        components=[
            Component(name="idp", type="identity-provider", criticality="high",
                      description="Identity provider"),
            Component(name="svc1", type="service", criticality="medium"),
            Component(name="svc2", type="service", criticality="medium"),
            Component(name="svc3", type="service", criticality="low"),
            Component(name="cache", type="cache", criticality="low"),
        ],
        flows=[
            Flow(source="svc1", target="svc2"),
            Flow(source="svc2", target="svc3"),
        ],
    )


def _write_arch(tmp_path: Path, arch: Architecture, name: str) -> Path:
    import yaml as _yaml
    data = {
        "name": arch.name,
        "description": arch.description,
        "components": [
            {"name": c.name, "type": c.type, "criticality": c.criticality,
             "description": c.description}
            for c in arch.components
        ],
        "flows": [{"from": f.source, "to": f.target} for f in arch.flows],
    }
    p = tmp_path / name
    p.write_text(_yaml.dump(data), encoding="utf-8")
    return p


# ── extract_keywords ──────────────────────────────────────────────────────────

def test_extract_keywords_returns_sorted_list():
    kws = extract_keywords(_arch_a())
    assert kws == sorted(kws)


def test_extract_keywords_includes_component_types():
    kws = extract_keywords(_arch_a())
    assert "service" in kws or "api" in kws


def test_extract_keywords_includes_arch_name():
    kws = extract_keywords(_arch_a())
    assert "platform" in kws


def test_extract_keywords_no_duplicates():
    kws = extract_keywords(_arch_a())
    assert len(kws) == len(set(kws))


def test_extract_keywords_min_length():
    kws = extract_keywords(_arch_a())
    assert all(len(k) >= 2 for k in kws)


# ── detect_patterns ───────────────────────────────────────────────────────────

def test_detect_gateway_backed():
    assert "gateway-backed" in detect_patterns(_arch_a())


def test_detect_identity_driven():
    assert "identity-driven" in detect_patterns(_arch_b())


def test_detect_microservices():
    assert "microservices" in detect_patterns(_arch_b())


def test_detect_zero_trust_capable():
    assert "zero-trust-capable" in detect_patterns(_arch_a())


def test_detect_no_false_gateway():
    assert "gateway-backed" not in detect_patterns(_arch_b())


# ── add_to_memory ─────────────────────────────────────────────────────────────

def test_add_returns_indexed_model(tmp_path, idx_dir):
    p = _write_arch(tmp_path, _arch_a(), "a.yaml")
    m = add_to_memory(p, index_dir=idx_dir)
    assert isinstance(m, IndexedModel)


def test_add_stores_name(tmp_path, idx_dir):
    p = _write_arch(tmp_path, _arch_a(), "a.yaml")
    m = add_to_memory(p, index_dir=idx_dir)
    assert m.name == "platform-a"


def test_add_stores_component_count(tmp_path, idx_dir):
    p = _write_arch(tmp_path, _arch_a(), "a.yaml")
    m = add_to_memory(p, index_dir=idx_dir)
    assert m.component_count == 3


def test_add_writes_index_file(tmp_path, idx_dir):
    p = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(p, index_dir=idx_dir)
    assert (idx_dir / "index.json").exists()


def test_add_updates_existing_entry(tmp_path, idx_dir):
    p = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(p, index_dir=idx_dir)
    add_to_memory(p, index_dir=idx_dir)
    models = list_memory(idx_dir)
    assert len(models) == 1


def test_add_missing_file_raises(tmp_path, idx_dir):
    with pytest.raises(MemoryError, match="Cannot load"):
        add_to_memory(tmp_path / "nonexistent.yaml", index_dir=idx_dir)


# ── list_memory ───────────────────────────────────────────────────────────────

def test_list_empty_when_no_index(idx_dir):
    assert list_memory(idx_dir) == []


def test_list_returns_added_models(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    pb = _write_arch(tmp_path, _arch_b(), "b.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    add_to_memory(pb, index_dir=idx_dir)
    models = list_memory(idx_dir)
    assert len(models) == 2


def test_list_sorted_by_name(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    pb = _write_arch(tmp_path, _arch_b(), "b.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    add_to_memory(pb, index_dir=idx_dir)
    names = [m.name for m in list_memory(idx_dir)]
    assert names == sorted(names, key=str.lower)


# ── remove_from_memory ────────────────────────────────────────────────────────

def test_remove_reduces_count(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    remove_from_memory(pa, index_dir=idx_dir)
    assert list_memory(idx_dir) == []


def test_remove_missing_raises(tmp_path, idx_dir):
    with pytest.raises(MemoryError, match="not in the memory index"):
        remove_from_memory(tmp_path / "ghost.yaml", index_dir=idx_dir)


# ── search_memory ─────────────────────────────────────────────────────────────

def test_search_returns_list(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    results = search_memory("gateway", index_dir=idx_dir)
    assert isinstance(results, list)


def test_search_finds_matching_model(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    results = search_memory("gateway", index_dir=idx_dir)
    assert len(results) >= 1
    assert isinstance(results[0], SearchResult)


def test_search_empty_query_returns_empty(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    assert search_memory("", index_dir=idx_dir) == []


def test_search_no_match_returns_empty(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    results = search_memory("xyznotfound", index_dir=idx_dir)
    assert results == []


def test_search_similarity_between_0_and_1(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    for r in search_memory("platform api", index_dir=idx_dir):
        assert 0.0 <= r.similarity <= 1.0


def test_search_sorted_descending(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    pb = _write_arch(tmp_path, _arch_b(), "b.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    add_to_memory(pb, index_dir=idx_dir)
    results = search_memory("gateway api platform", index_dir=idx_dir)
    scores = [r.similarity for r in results]
    assert scores == sorted(scores, reverse=True)


# ── compare_architectures ─────────────────────────────────────────────────────

def test_compare_returns_comparison_result():
    result = compare_architectures(_arch_a(), _arch_b())
    assert isinstance(result, ComparisonResult)


def test_compare_shared_service_type():
    result = compare_architectures(_arch_a(), _arch_b())
    assert "service" in result.shared_component_types


def test_compare_unique_to_a():
    result = compare_architectures(_arch_a(), _arch_b())
    assert "access-gateway" in result.unique_to_a or "data-store" in result.unique_to_a


def test_compare_unique_to_b():
    result = compare_architectures(_arch_b(), _arch_a())
    assert "identity-provider" in result.unique_to_a  # arch_b is now A in this call


def test_compare_jaccard_range():
    result = compare_architectures(_arch_a(), _arch_b())
    assert 0.0 <= result.structural_similarity <= 1.0


def test_compare_identical_similarity_1():
    result = compare_architectures(_arch_a(), _arch_a())
    assert result.structural_similarity == 1.0


def test_compare_summary_non_empty():
    result = compare_architectures(_arch_a(), _arch_b())
    assert len(result.summary) > 0


def test_compare_to_dict_keys():
    d = compare_architectures(_arch_a(), _arch_b()).to_dict()
    for key in ("model_a", "model_b", "shared_component_types", "unique_to_a",
                "unique_to_b", "structural_similarity", "patterns_a", "patterns_b", "summary"):
        assert key in d


# ── format functions ──────────────────────────────────────────────────────────

def test_format_memory_list_empty():
    text = format_memory_list([])
    assert "empty" in text.lower() or "Memory index" in text


def test_format_memory_list_shows_name(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    models = [add_to_memory(pa, index_dir=idx_dir)]
    text = format_memory_list(models)
    assert "platform-a" in text


def test_format_search_results_no_match():
    text = format_search_results([], "ghost")
    assert "No results" in text


def test_format_search_results_shows_name(tmp_path, idx_dir):
    pa = _write_arch(tmp_path, _arch_a(), "a.yaml")
    add_to_memory(pa, index_dir=idx_dir)
    results = search_memory("platform", index_dir=idx_dir)
    text = format_search_results(results, "platform")
    assert "platform-a" in text


def test_format_comparison_contains_similarity():
    result = compare_architectures(_arch_a(), _arch_b())
    text = format_comparison(result)
    assert "%" in text


# ── runtime functions ─────────────────────────────────────────────────────────

def test_runtime_memory_add_ok():
    result = memory_add(EXAMPLES / "identity-flow.yaml")
    assert result.ok or result.status in ("ok", "warning")
    assert result.command == "memory-add"


def test_runtime_memory_add_missing_error():
    result = memory_add("nonexistent.yaml")
    assert result.failed


def test_runtime_memory_list_ok():
    result = memory_list()
    assert result.ok
    assert "models" in result.data


def test_runtime_memory_remove_missing_error():
    result = memory_remove("nonexistent.yaml")
    assert result.failed


def test_runtime_memory_search_returns_results():
    result = memory_search("identity gateway")
    assert result.ok
    assert "results" in result.data
    assert "query" in result.data


def test_runtime_memory_compare_ok():
    result = memory_compare(
        EXAMPLES / "identity-flow.yaml",
        EXAMPLES / "zero-trust-access.yaml",
    )
    assert result.ok
    assert "structural_similarity" in result.data


def test_runtime_memory_compare_missing_file_error():
    result = memory_compare("nonexistent.yaml", EXAMPLES / "identity-flow.yaml")
    assert result.failed
