"""
Shared graph model + concept canonicalization.

The symbolic (rule-based) and neural (LLM) pipelines were written independently
and emit prerequisite graphs in *different* JSON schemas with *different* naming
conventions:

    symbolic edge:  {"source": "binary tree", "target": "leaf node",
                     "type": "is_prerequisite_for", "confidence": 0.9}
    neural   edge:  {"from": "binary_tree", "to": "leaf_node",
                     "type": "domain_rule", "rule": "..."}

Before we can fuse them or score them against a gold standard, every concept
name has to be resolved to a single canonical id ("binary tree" / "binary_tree"
/ "BST" must all collapse to one node). This module owns that reconciliation:

    * `canonical()`  — deterministic concept-name normalization + alias map
    * `PrereqGraph`  — schema-agnostic in-memory graph (canonical ids)
    * `load_graph()` — read either pipeline's JSON into a `PrereqGraph`

Keeping the canonicalization deterministic (a documented alias table, no fuzzy
guessing at scoring time) is intentional: the evaluation numbers must be
reproducible and auditable, not dependent on a similarity threshold.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Relations that express a directed "learn A before B" dependency. Each
# pipeline uses its own vocabulary; we map everything to one of these.
PREREQUISITE = "is_prerequisite_for"
REFINES = "refines"
PART_OF = "is_part_of"
TEMPORAL = "temporal_precedence"

# Map every edge "type" string ever emitted by either pipeline onto a relation.
_RELATION_MAP = {
    # symbolic
    "is_prerequisite_for": PREREQUISITE,
    "refines": REFINES,
    "is_part_of": PART_OF,
    "temporal_precedence": TEMPORAL,
    # neural
    "domain_rule": PREREQUISITE,
    "causal": PREREQUISITE,
    "prerequisite": PREREQUISITE,
    "temporal": TEMPORAL,
}

# Default confidence by relation when a pipeline does not emit one (the neural
# graphs carry no confidence field). Mirrors the symbolic pipeline's own scale.
_DEFAULT_CONFIDENCE = {
    PREREQUISITE: 0.85,
    REFINES: 0.8,
    PART_OF: 0.7,
    TEMPORAL: 0.5,
}

# Alias table applied AFTER structural normalization (snake_case). Resolves
# acronyms and the symbolic-vs-neural naming split. Documented and small on
# purpose — this is the only place concept identity is decided.
_ALIASES = {
    "bfs": "breadth_first_search",
    "dfs": "depth_first_search",
    "bst": "binary_search_tree",
    "dag": "directed_acyclic_graph",
    "mcst": "minimum_cost_spanning_tree",
    "mst": "minimum_cost_spanning_tree",
    # neural drops the trailing "traversal" that the symbolic pipeline keeps
    "pre_order": "pre_order_traversal",
    "preorder": "pre_order_traversal",
    "preorder_traversal": "pre_order_traversal",
    "in_order": "in_order_traversal",
    "inorder": "in_order_traversal",
    "inorder_traversal": "in_order_traversal",
    "post_order": "post_order_traversal",
    "postorder": "post_order_traversal",
    "postorder_traversal": "post_order_traversal",
    "graph_traversal": "graph_traversal",
    "traversal_technique": "tree_traversal",
    "activation_record": "activation_record",
    "call_by_value": "call_by_value",
}


def canonical(name: str) -> str:
    """Normalize a concept name to a single canonical id.

    Lowercase -> hyphens/spaces/dots to underscores -> collapse repeats ->
    strip -> apply the alias table. Deterministic and idempotent.
    """
    s = name.strip().lower()
    s = re.sub(r"[\s\-./]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return _ALIASES.get(s, s)


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str = PREREQUISITE
    confidence: float = 0.85
    provenance: str = "unknown"  # "symbolic" | "neural" | "both"

    def key(self) -> tuple[str, str]:
        return (self.source, self.target)


@dataclass
class PrereqGraph:
    """Schema-agnostic prerequisite graph keyed on canonical concept ids."""

    video_id: str = ""
    method: str = ""  # "symbolic" | "neural" | "hybrid" | "gold"
    nodes: set[str] = field(default_factory=set)
    edges: list[Edge] = field(default_factory=list)
    # optional per-node metadata (first_mention seconds, mention_count)
    meta: dict[str, dict] = field(default_factory=dict)

    def add_edge(self, edge: Edge) -> None:
        self.nodes.add(edge.source)
        self.nodes.add(edge.target)
        self.edges.append(edge)

    def edge_keys(self) -> set[tuple[str, str]]:
        return {e.key() for e in self.edges}

    def prereq_edge_keys(self) -> set[tuple[str, str]]:
        """Directed dependency edges only (drop weak temporal-precedence)."""
        return {e.key() for e in self.edges if e.relation != TEMPORAL}

    def to_networkx(self):
        import networkx as nx

        g = nx.DiGraph()
        g.add_nodes_from(self.nodes)
        for e in self.edges:
            g.add_edge(e.source, e.target, relation=e.relation,
                       confidence=e.confidence, provenance=e.provenance)
        return g

    def to_prereq_dag(self):
        """Cycle-free DiGraph over prerequisite edges only (drops temporal).

        Weak temporal-precedence edges and any residual cycles (which can
        appear after canonicalization merges two raw nodes into one) are
        removed, so downstream consumers can rely on a true DAG.
        """
        import networkx as nx

        g = nx.DiGraph()
        g.add_nodes_from(self.nodes)
        for e in self.edges:
            if e.relation == TEMPORAL:
                continue
            g.add_edge(e.source, e.target, confidence=e.confidence)
        return _break_cycles(g)

    def to_json(self) -> dict:
        return {
            "video_id": self.video_id,
            "method": self.method,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes": [
                {"id": n, **self.meta.get(n, {})} for n in sorted(self.nodes)
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "confidence": round(e.confidence, 3),
                    "provenance": e.provenance,
                }
                for e in self.edges
            ],
            "topological_order": topological_order(self),
        }


def _coerce_edges(raw: dict) -> Iterable[tuple[str, str, str, float | None]]:
    """Yield (source, target, type, confidence|None) from either schema."""
    for e in raw.get("edges", []):
        src = e.get("source") or e.get("from")
        dst = e.get("target") or e.get("to")
        if not src or not dst:
            continue
        yield src, dst, e.get("type", ""), e.get("confidence")


def load_graph(path: str | Path, *, video_id: str = "", method: str = "") -> PrereqGraph:
    """Load a graph.json of either pipeline schema into a canonical PrereqGraph."""
    raw = json.loads(Path(path).read_text())
    g = PrereqGraph(video_id=video_id or raw.get("video_id", ""), method=method)

    # node metadata (symbolic graphs carry first_mention / mention_count)
    for nd in raw.get("nodes", []):
        cid = canonical(nd["id"])
        g.nodes.add(cid)
        meta = {}
        if "first_mention" in nd:
            meta["first_mention"] = nd["first_mention"]
        if "mention_count" in nd:
            meta["mention_count"] = nd["mention_count"]
        if meta:
            g.meta[cid] = meta

    for src, dst, etype, conf in _coerce_edges(raw):
        relation = _RELATION_MAP.get(etype, PREREQUISITE)
        c = conf if conf is not None else _DEFAULT_CONFIDENCE[relation]
        g.add_edge(Edge(canonical(src), canonical(dst), relation,
                        float(c), provenance=method or "unknown"))

    # neural graphs have no node list — derive nodes from edges + topo order
    for n in raw.get("topological_order", []):
        g.nodes.add(canonical(n))

    return g


def topological_order(g: PrereqGraph) -> list[str]:
    """Kahn topological sort over prerequisite edges; stable tie-break by name.

    Falls back gracefully if the graph still has a cycle (returns the partial
    order followed by the remaining nodes) — fusion is expected to break cycles
    first, but this keeps the function total.
    """
    import networkx as nx

    nxg = nx.DiGraph()
    nxg.add_nodes_from(g.nodes)
    for s, t in g.prereq_edge_keys():
        nxg.add_edge(s, t)
    try:
        return list(nx.lexicographical_topological_sort(nxg))
    except nx.NetworkXUnfeasible:
        order = [n for n in nx.lexicographical_topological_sort(_break_cycles(nxg))]
        return order


def _break_cycles(nxg):
    """Remove one edge per cycle until acyclic (used only as a safety net)."""
    import networkx as nx

    h = nxg.copy()
    while True:
        try:
            cycle = nx.find_cycle(h)
        except nx.NetworkXNoCycle:
            return h
        h.remove_edge(*cycle[0][:2])
