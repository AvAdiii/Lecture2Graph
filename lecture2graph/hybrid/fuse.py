"""
Neuro-symbolic fusion.

The two extractors have complementary failure modes (measured in
`evaluation/benchmark.py`):

    * symbolic (regex + hand-authored domain rules), high precision, low
      recall. It only emits edges it has a rule for, so it misses
      application-level concepts ("web_crawler", "activation_record") that the
      lecturer mentions but no rule anticipates.

    * neural (Llama-3.3-70B), higher recall, lower precision. It discovers
      novel concepts and reasoned edges but also hallucinates relationships and
      drops structural sub-concepts.

`fuse()` combines them into one DAG that keeps symbolic precision while
absorbing neural recall:

    1. Canonicalize + union both edge sets (see `lecture2graph.graphs`).
    2. Reconcile each directed pair:
         - agreed by both       -> provenance "both", confidence boosted via
                                   noisy-OR  1 - (1-c_sym)(1-c_neu)
         - single source        -> kept at (slightly discounted) confidence
    3. Resolve direction conflicts (A->B vs B->A): keep the higher-confidence
       edge, drop the contradiction.
    4. Break any residual cycles by removing the lowest-confidence edge on each
       cycle (same principle as the symbolic pipeline's DAG verifier), then
       emit a topological order.

Output: data/<video>/graph.hybrid.json in the unified schema.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lecture2graph.graphs import (
    Edge,
    PrereqGraph,
    PREREQUISITE,
    TEMPORAL,
    load_graph,
)

# A single-source edge is trusted less than one both extractors agree on.
_SINGLE_SOURCE_DISCOUNT = 0.9


def _noisy_or(a: float, b: float) -> float:
    return 1.0 - (1.0 - a) * (1.0 - b)


def fuse(symbolic: PrereqGraph, neural: PrereqGraph,
         video_id: str = "") -> PrereqGraph:
    """Fuse a symbolic and a neural prerequisite graph into one DAG."""
    # Index best edge per (src,target) within each source graph.
    def best_by_key(g: PrereqGraph) -> dict[tuple[str, str], Edge]:
        out: dict[tuple[str, str], Edge] = {}
        for e in g.edges:
            if e.relation == TEMPORAL:
                continue  # weak temporal-precedence edges are not fused
            k = e.key()
            if k not in out or e.confidence > out[k].confidence:
                out[k] = e
        return out

    sym = best_by_key(symbolic)
    neu = best_by_key(neural)

    merged: dict[tuple[str, str], Edge] = {}
    for k in set(sym) | set(neu):
        se, ne = sym.get(k), neu.get(k)
        if se and ne:
            conf = _noisy_or(se.confidence, ne.confidence)
            # prefer the symbolic relation label (typed, hand-curated)
            relation = se.relation
            merged[k] = Edge(k[0], k[1], relation, conf, provenance="both")
        else:
            e = se or ne
            prov = "symbolic" if se else "neural"
            merged[k] = Edge(k[0], k[1], e.relation,
                             e.confidence * _SINGLE_SOURCE_DISCOUNT, prov)

    # Resolve direction conflicts: A->B vs B->A, keep the stronger one.
    resolved: dict[tuple[str, str], Edge] = {}
    dropped_conflicts = 0
    for k, e in merged.items():
        rev = (k[1], k[0])
        if rev in merged:
            if merged[rev].confidence > e.confidence:
                continue  # the reverse edge wins; skip this one
            if merged[rev].confidence == e.confidence and k > rev:
                continue  # deterministic tie-break
            dropped_conflicts += 1
        resolved[k] = e

    fused = PrereqGraph(video_id=video_id or symbolic.video_id, method="hybrid")
    fused.nodes = set(symbolic.nodes) | set(neural.nodes)
    fused.meta = {**neural.meta, **symbolic.meta}  # symbolic metadata wins
    for e in resolved.values():
        fused.add_edge(e)

    removed = _break_cycles_lowest_conf(fused)
    fused.meta.setdefault("_fusion", {})
    fused.meta["_fusion"] = {
        "edges_symbolic_only": sum(1 for e in fused.edges if e.provenance == "symbolic"),
        "edges_neural_only": sum(1 for e in fused.edges if e.provenance == "neural"),
        "edges_agreed": sum(1 for e in fused.edges if e.provenance == "both"),
        "direction_conflicts_resolved": dropped_conflicts,
        "cycle_edges_removed": removed,
    }
    return fused


def _break_cycles_lowest_conf(g: PrereqGraph) -> int:
    """Remove the lowest-confidence edge on each cycle until the graph is a DAG."""
    import networkx as nx

    removed = 0
    while True:
        nxg = g.to_networkx()
        try:
            cycle = nx.find_cycle(nxg)
        except nx.NetworkXNoCycle:
            return removed
        # pick the weakest edge along the detected cycle
        weakest = min(
            cycle,
            key=lambda c: nxg.edges[c[0], c[1]]["confidence"],
        )
        s, t = weakest[0], weakest[1]
        g.edges = [e for e in g.edges if e.key() != (s, t)]
        removed += 1


def fuse_video(video_id: str, data_root: str = "data") -> PrereqGraph:
    """Fuse the cached symbolic+neural graphs for one video and write hybrid json."""
    base = Path(data_root) / video_id
    sym = load_graph(base / "graph.symbolic.json", video_id=video_id, method="symbolic")
    neu = load_graph(base / "graph.neural.json", video_id=video_id, method="neural")
    fused = fuse(sym, neu, video_id=video_id)

    out = base / "graph.hybrid.json"
    import json
    out.write_text(json.dumps(fused.to_json(), indent=2))
    return fused


def main() -> None:
    p = argparse.ArgumentParser(description="Fuse symbolic + neural prerequisite graphs")
    p.add_argument("video_id", nargs="?", help="video id (omit to fuse all eligible)")
    p.add_argument("--data-root", default="data")
    args = p.parse_args()

    if args.video_id:
        videos = [args.video_id]
    else:
        root = Path(args.data_root)
        videos = sorted(
            d.name for d in root.iterdir()
            if (d / "graph.symbolic.json").exists() and (d / "graph.neural.json").exists()
        )

    for v in videos:
        g = fuse_video(v, args.data_root)
        f = g.meta["_fusion"]
        print(f"[fuse] {v}: {len(g.nodes)} nodes, {len(g.edges)} edges "
              f"(agreed={f['edges_agreed']}, sym_only={f['edges_symbolic_only']}, "
              f"neu_only={f['edges_neural_only']}, conflicts={f['direction_conflicts_resolved']}, "
              f"cycle_removed={f['cycle_edges_removed']})")


if __name__ == "__main__":
    main()
