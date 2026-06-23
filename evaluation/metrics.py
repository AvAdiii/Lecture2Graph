"""
Evaluation metrics for extracted prerequisite graphs.

All metrics compare a predicted `PrereqGraph` against a domain-authored gold
graph, after both have been canonicalized by `lecture2graph.graphs`. We report:

    * node precision / recall / F1: did we recover the right concepts?
    * edge precision / recall / F1: did we recover the right directed
      prerequisite dependencies?
    * prerequisite-order accuracy: of the gold "A before B" pairs whose
      endpoints we predicted, how many does our topological order get right?
    * graph edit distance (symmetric): |node symdiff| + |edge symdiff|, an
      interpretable structural distance.

Edges are matched as exact directed canonical pairs (src, target). Weak
temporal-precedence edges are excluded (see PrereqGraph.prereq_edge_keys).
"""

from __future__ import annotations

import json
from pathlib import Path

from lecture2graph.graphs import Edge, PrereqGraph, canonical, topological_order


def load_gold(path: str | Path) -> PrereqGraph:
    raw = json.loads(Path(path).read_text())
    g = PrereqGraph(video_id=raw.get("video_id", ""), method="gold")
    for c in raw.get("concepts", []):
        g.nodes.add(canonical(c))
    for e in raw.get("edges", []):
        g.add_edge(Edge(canonical(e["source"]), canonical(e["target"])))
    return g


def _prf(pred: set, gold: set) -> dict:
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "pred": len(pred), "gold": len(gold)}


def prereq_order_accuracy(pred: PrereqGraph, gold: PrereqGraph) -> dict:
    """Fraction of gold 'A before B' pairs ordered correctly by pred's topo sort.

    Only counts gold edges whose endpoints both appear in the prediction, you
    cannot order a concept you never extracted (that miss is already penalized
    by recall).
    """
    order = topological_order(pred)
    rank = {n: i for i, n in enumerate(order)}
    considered = correct = 0
    for s, t in gold.prereq_edge_keys():
        if s in rank and t in rank:
            considered += 1
            if rank[s] < rank[t]:
                correct += 1
    return {"accuracy": (correct / considered) if considered else 0.0,
            "correct": correct, "considered": considered}


def graph_edit_distance(pred: PrereqGraph, gold: PrereqGraph) -> int:
    """Interpretable symmetric structural distance: node + edge disagreements."""
    node_sd = pred.nodes ^ gold.nodes
    edge_sd = pred.prereq_edge_keys() ^ gold.prereq_edge_keys()
    return len(node_sd) + len(edge_sd)


def evaluate(pred: PrereqGraph, gold: PrereqGraph) -> dict:
    nodes = _prf(pred.nodes, gold.nodes)
    edges = _prf(pred.prereq_edge_keys(), gold.prereq_edge_keys())
    order = prereq_order_accuracy(pred, gold)
    return {
        "node_precision": nodes["precision"],
        "node_recall": nodes["recall"],
        "node_f1": nodes["f1"],
        "edge_precision": edges["precision"],
        "edge_recall": edges["recall"],
        "edge_f1": edges["f1"],
        "edge_tp": edges["tp"],
        "edge_pred": edges["pred"],
        "edge_gold": edges["gold"],
        "prereq_order_accuracy": order["accuracy"],
        "order_considered": order["considered"],
        "graph_edit_distance": graph_edit_distance(pred, gold),
    }
