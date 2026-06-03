"""Zephyr Architecture Semantic Memory.

Maintains a multi-model index that enables semantic search and cross-project
comparison across architecture YAML files. The index is a lightweight
keyword-based "vector" store (no ML dependencies) — each model is represented
as a bag of extracted terms, and similarity is computed as term-overlap score.

v0.6.0 capabilities:
  Architecture vector indexing   — keyword extraction and index storage
  Semantic architecture memory   — multi-model index with add/remove/list
  Cross-project comparison       — structural similarity and pattern divergence

Index location: .zephyr/memory/index.json (relative to working directory,
or an explicit directory passed to each function).

Entry points:
  add_to_memory(path, index_dir=None) -> IndexedModel
  remove_from_memory(path, index_dir=None) -> None
  list_memory(index_dir=None) -> list[IndexedModel]
  search_memory(query, index_dir=None, top_k=10) -> list[SearchResult]
  compare_architectures(arch_a, arch_b, name_a, name_b) -> ComparisonResult
  default_index_dir() -> Path
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from zephyr.loader import architecture_from_data, load_architecture_data
from zephyr.models import Architecture
from zephyr.scoring import score_architecture


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class IndexedModel:
    path: str
    name: str
    indexed_at: str
    component_count: int
    flow_count: int
    risk_count: int
    component_types: list[str]   # sorted unique
    keywords: list[str]          # extracted search terms
    score: int | None
    grade: str | None

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "indexed_at": self.indexed_at,
            "component_count": self.component_count,
            "flow_count": self.flow_count,
            "risk_count": self.risk_count,
            "component_types": self.component_types,
            "keywords": self.keywords,
            "score": self.score,
            "grade": self.grade,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IndexedModel":
        return cls(
            path=d["path"],
            name=d["name"],
            indexed_at=d.get("indexed_at", ""),
            component_count=d.get("component_count", 0),
            flow_count=d.get("flow_count", 0),
            risk_count=d.get("risk_count", 0),
            component_types=d.get("component_types", []),
            keywords=d.get("keywords", []),
            score=d.get("score"),
            grade=d.get("grade"),
        )


@dataclass
class SearchResult:
    model: IndexedModel
    similarity: float        # 0.0 – 1.0
    matched_terms: list[str]

    def to_dict(self) -> dict:
        return {
            "model": self.model.to_dict(),
            "similarity": round(self.similarity, 3),
            "matched_terms": self.matched_terms,
        }


@dataclass
class ComparisonResult:
    model_a_name: str
    model_b_name: str
    shared_component_types: list[str]
    unique_to_a: list[str]
    unique_to_b: list[str]
    structural_similarity: float   # Jaccard on component-type sets
    shared_risk_themes: list[str]
    patterns_a: list[str]
    patterns_b: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "model_a": self.model_a_name,
            "model_b": self.model_b_name,
            "shared_component_types": self.shared_component_types,
            "unique_to_a": self.unique_to_a,
            "unique_to_b": self.unique_to_b,
            "structural_similarity": round(self.structural_similarity, 3),
            "shared_risk_themes": self.shared_risk_themes,
            "patterns_a": self.patterns_a,
            "patterns_b": self.patterns_b,
            "summary": self.summary,
        }


class MemoryError(Exception):
    pass


# ── Index storage ─────────────────────────────────────────────────────────────

def default_index_dir() -> Path:
    """Return the default memory index directory (.zephyr/memory/ in cwd)."""
    return Path.cwd() / ".zephyr" / "memory"


def _index_path(index_dir: Path | None) -> Path:
    return (index_dir or default_index_dir()) / "index.json"


def _load_index(index_dir: Path | None) -> list[IndexedModel]:
    p = _index_path(index_dir)
    if not p.exists():
        return []
    entries = json.loads(p.read_text(encoding="utf-8"))
    return [IndexedModel.from_dict(e) for e in entries]


def _save_index(models: list[IndexedModel], index_dir: Path | None) -> None:
    p = _index_path(index_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([m.to_dict() for m in models], indent=2), encoding="utf-8")


# ── Keyword extraction ("vector indexing") ────────────────────────────────────

_SPLIT_RE = re.compile(r"[\s\-_./,;:()\[\]]+")


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, filtering short tokens."""
    if not text:
        return []
    return [t.lower() for t in _SPLIT_RE.split(text) if len(t) >= 2]


def extract_keywords(arch: Architecture) -> list[str]:
    """Extract a deduplicated, sorted keyword list from an architecture model."""
    terms: set[str] = set()

    terms.update(_tokenize(arch.name))
    terms.update(_tokenize(arch.description))

    if arch.meta:
        terms.update(_tokenize(arch.meta.owner))
        terms.update(_tokenize(arch.meta.criticality))
        terms.update(arch.meta.environment)

    for c in arch.components:
        terms.update(_tokenize(c.name))
        terms.update(_tokenize(c.type))
        terms.update(_tokenize(c.description))
        terms.update(_tokenize(c.domain))
        terms.update(_tokenize(c.criticality))
        terms.update(_tokenize(c.exposure))
        terms.update(_tokenize(c.lifecycle))
        terms.update(_tokenize(c.trust_boundary))
        terms.update(t.lower() for t in c.tags)

    for r in arch.risks:
        terms.update(_tokenize(r.title))
        terms.update(_tokenize(r.description))
        terms.update(_tokenize(r.severity))

    for ctrl in arch.controls:
        terms.update(_tokenize(ctrl.name))
        terms.update(_tokenize(ctrl.type))
        terms.update(_tokenize(ctrl.description))

    for tb in arch.trust_boundaries:
        terms.update(_tokenize(tb.name))

    # Remove very common stop words
    _STOP = {"the", "and", "or", "of", "to", "in", "for", "on", "at", "by",
              "an", "a", "is", "be", "are", "was", "with", "not", "no"}
    terms -= _STOP
    return sorted(terms)


# ── Public API ────────────────────────────────────────────────────────────────

def add_to_memory(
    path: str | Path,
    index_dir: Path | None = None,
) -> IndexedModel:
    """Index an architecture YAML file into the memory store.

    Re-indexing an already-indexed path updates the entry.
    Raises MemoryError if the file cannot be loaded.
    """
    p = Path(path).resolve()
    try:
        data = load_architecture_data(str(p))
        arch = architecture_from_data(data)
    except Exception as exc:
        raise MemoryError(f"Cannot load architecture '{path}': {exc}") from exc

    try:
        sc = score_architecture(arch)
        score_val: int | None = sc.overall
        grade_val: str | None = sc.grade
    except Exception:
        score_val = None
        grade_val = None

    model = IndexedModel(
        path=str(p),
        name=arch.name,
        indexed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        component_count=len(arch.components),
        flow_count=len(arch.flows),
        risk_count=len(arch.risks),
        component_types=sorted({c.type for c in arch.components}),
        keywords=extract_keywords(arch),
        score=score_val,
        grade=grade_val,
    )

    models = [m for m in _load_index(index_dir) if m.path != str(p)]
    models.append(model)
    _save_index(models, index_dir)
    return model


def remove_from_memory(path: str | Path, index_dir: Path | None = None) -> None:
    """Remove an architecture from the memory index.

    Raises MemoryError if the path is not in the index.
    """
    p = str(Path(path).resolve())
    models = _load_index(index_dir)
    if not any(m.path == p for m in models):
        raise MemoryError(f"'{path}' is not in the memory index.")
    _save_index([m for m in models if m.path != p], index_dir)


def list_memory(index_dir: Path | None = None) -> list[IndexedModel]:
    """Return all indexed models, sorted by name."""
    return sorted(_load_index(index_dir), key=lambda m: m.name.lower())


def search_memory(
    query: str,
    index_dir: Path | None = None,
    top_k: int = 10,
) -> list[SearchResult]:
    """Search the memory index by query string.

    Returns results sorted by descending similarity (0 = no match, 1 = full match).
    Only returns models with similarity > 0.
    """
    query_terms = set(_tokenize(query))
    if not query_terms:
        return []

    results: list[SearchResult] = []
    for model in _load_index(index_dir):
        model_terms = set(model.keywords)
        matched = sorted(query_terms & model_terms)
        # Also boost for component_type exact matches
        type_match = [t for t in model.component_types if t.lower() in query_terms]
        matched = sorted(set(matched + type_match))
        if not matched:
            continue
        similarity = len(matched) / len(query_terms)
        results.append(SearchResult(model=model, similarity=similarity,
                                    matched_terms=matched))

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results[:top_k]


# ── Architectural pattern detection ──────────────────────────────────────────

_PATTERN_CHECKS = [
    ("gateway-backed",     lambda a: any(c.type == "access-gateway" for c in a.components)),
    ("identity-driven",    lambda a: any(c.type in {
        "identity", "identity-provider", "cloud-identity", "on-prem-identity"}
        for c in a.components)),
    ("data-centric",       lambda a: any(c.type == "data-store" for c in a.components)),
    ("zero-trust-capable", lambda a: bool(a.trust_boundaries) and any(
        c.type == "access-gateway" for c in a.components)),
    ("microservices",      lambda a: sum(1 for c in a.components if c.type == "service") >= 3),
    ("risk-modelled",      lambda a: len(a.risks) >= 2),
    ("control-rich",       lambda a: len(a.controls) >= 3),
    ("external-facing",    lambda a: any(c.exposure == "external" for c in a.components)),
]


def detect_patterns(arch: Architecture) -> list[str]:
    return [name for name, check in _PATTERN_CHECKS if check(arch)]


# ── Cross-project comparison ──────────────────────────────────────────────────

def compare_architectures(
    arch_a: Architecture,
    arch_b: Architecture,
    name_a: str = "",
    name_b: str = "",
) -> ComparisonResult:
    """Compare two architectures structurally and semantically."""
    na = name_a or arch_a.name
    nb = name_b or arch_b.name

    types_a = {c.type for c in arch_a.components}
    types_b = {c.type for c in arch_b.components}
    shared = sorted(types_a & types_b)
    only_a = sorted(types_a - types_b)
    only_b = sorted(types_b - types_a)

    union = types_a | types_b
    jaccard = len(shared) / len(union) if union else 1.0

    # Shared risk themes (words from risk titles appearing in both)
    words_a = {w for r in arch_a.risks for w in _tokenize(r.title)}
    words_b = {w for r in arch_b.risks for w in _tokenize(r.title)}
    shared_risk_themes = sorted(words_a & words_b - {"risk", "the", "and"})

    patterns_a = detect_patterns(arch_a)
    patterns_b = detect_patterns(arch_b)

    summary = _compare_summary(na, nb, shared, only_a, only_b, jaccard, patterns_a, patterns_b)

    return ComparisonResult(
        model_a_name=na,
        model_b_name=nb,
        shared_component_types=shared,
        unique_to_a=only_a,
        unique_to_b=only_b,
        structural_similarity=jaccard,
        shared_risk_themes=shared_risk_themes,
        patterns_a=patterns_a,
        patterns_b=patterns_b,
        summary=summary,
    )


def _compare_summary(
    na: str, nb: str,
    shared: list[str],
    only_a: list[str],
    only_b: list[str],
    jaccard: float,
    patterns_a: list[str],
    patterns_b: list[str],
) -> str:
    pct = round(jaccard * 100)
    parts = [f"Structural similarity: {pct}%."]
    if shared:
        parts.append(f"Shared component types: {', '.join(shared)}.")
    if only_a:
        parts.append(f"Only in {na}: {', '.join(only_a)}.")
    if only_b:
        parts.append(f"Only in {nb}: {', '.join(only_b)}.")
    shared_pats = sorted(set(patterns_a) & set(patterns_b))
    if shared_pats:
        parts.append(f"Common patterns: {', '.join(shared_pats)}.")
    return " ".join(parts)


# ── Human-readable output ────────────────────────────────────────────────────

def format_memory_list(models: list[IndexedModel]) -> str:
    if not models:
        return "Memory index is empty. Run: zephyr memory add <file>"
    lines = [f"Architecture memory ({len(models)} model(s)):", ""]
    for m in models:
        score_str = f"  score {m.score} ({m.grade})" if m.score is not None else ""
        lines.append(
            f"  {m.name:<30} {m.component_count:>3} components  "
            f"{m.risk_count:>2} risks{score_str}"
        )
        lines.append(f"    {m.path}")
    return "\n".join(lines)


def format_search_results(results: list[SearchResult], query: str) -> str:
    if not results:
        return f"No results for '{query}'."
    lines = [f"Search: '{query}'  ({len(results)} result(s))", ""]
    for r in results:
        sim_bar = "█" * round(r.similarity * 10) + "░" * (10 - round(r.similarity * 10))
        lines.append(f"  {sim_bar}  {r.similarity:.0%}  {r.model.name}")
        lines.append(f"    Matched: {', '.join(r.matched_terms[:8])}")
        lines.append(f"    {r.model.path}")
    return "\n".join(lines)


def format_comparison(result: ComparisonResult) -> str:
    pct = round(result.structural_similarity * 100)
    lines = [
        f"Comparison: {result.model_a_name}  ↔  {result.model_b_name}",
        f"Structural similarity: {pct}%",
        "",
        result.summary,
    ]
    if result.patterns_a or result.patterns_b:
        lines += ["", "Architectural patterns:"]
        all_pats = sorted(set(result.patterns_a) | set(result.patterns_b))
        for pat in all_pats:
            in_a = "✓" if pat in result.patterns_a else "✗"
            in_b = "✓" if pat in result.patterns_b else "✗"
            lines.append(f"  {in_a} / {in_b}  {pat}")
        lines.append(f"  ({result.model_a_name} / {result.model_b_name})")
    if result.shared_risk_themes:
        lines += ["", f"Shared risk themes: {', '.join(result.shared_risk_themes)}"]
    return "\n".join(lines)
