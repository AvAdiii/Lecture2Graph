"""Fast, offline sanity tests (stdlib unittest — no pytest required).

Run:  python -m unittest discover -s tests
These exercise the parts that must stay correct as the graphs change:
canonicalization/entity-resolution, the fusion DAG guarantee, and the metrics.
"""

import unittest
from pathlib import Path

import networkx as nx

from lecture2graph.graphs import canonical, load_graph
from lecture2graph.hybrid.fuse import fuse_video
from evaluation.metrics import evaluate, load_gold

DATA = "data"
GOLD = Path("evaluation/gold")
COMMON = ["XRcC7bAtL3c", "N2P7w22tN9c", "azXr6nTaD9M"]  # have all methods


class TestCanonical(unittest.TestCase):
    def test_naming_split_resolves(self):
        # symbolic space-form and neural snake/acronym map to one id
        self.assertEqual(canonical("binary tree"), canonical("binary_tree"))
        self.assertEqual(canonical("BFS"), "breadth_first_search")
        self.assertEqual(canonical("pre-order traversal"), "pre_order_traversal")
        self.assertEqual(canonical("pre_order"), "pre_order_traversal")

    def test_idempotent(self):
        for s in ["Tree Traversal", "graph_traversal", "DFS"]:
            self.assertEqual(canonical(s), canonical(canonical(s)))


class TestFusionIsDAG(unittest.TestCase):
    def test_hybrid_graphs_are_acyclic(self):
        for v in COMMON:
            fused = fuse_video(v, DATA)
            g = fused.to_prereq_dag()
            self.assertTrue(nx.is_directed_acyclic_graph(g),
                            f"hybrid graph for {v} must be a DAG")

    def test_fusion_recovers_both_sources(self):
        fused = fuse_video("XRcC7bAtL3c", DATA)
        provs = {e.provenance for e in fused.edges}
        self.assertIn("both", provs)
        self.assertTrue({"symbolic", "neural"} & provs)


class TestMetrics(unittest.TestCase):
    def test_perfect_graph_scores_one(self):
        gold = load_gold(GOLD / "XRcC7bAtL3c.json")
        scores = evaluate(gold, gold)  # gold vs itself
        self.assertAlmostEqual(scores["edge_f1"], 1.0)
        self.assertAlmostEqual(scores["node_f1"], 1.0)
        self.assertEqual(scores["graph_edit_distance"], 0)

    def test_scores_in_range(self):
        gold = load_gold(GOLD / "N2P7w22tN9c.json")
        pred = load_graph(f"{DATA}/N2P7w22tN9c/graph.symbolic.json",
                          method="symbolic")
        s = evaluate(pred, gold)
        for k in ["edge_precision", "edge_recall", "edge_f1", "node_f1"]:
            self.assertGreaterEqual(s[k], 0.0)
            self.assertLessEqual(s[k], 1.0)


if __name__ == "__main__":
    unittest.main()
