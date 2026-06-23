"""
Graph-RAG tutor over the concept DAG.

The prerequisite graph is not just a picture — it is a study planner. Given a
concept the learner wants to reach, the tutor *retrieves* the relevant subgraph
(its transitive prerequisites) from the DAG and answers:

    * what must I learn before X?      -> ancestors(X), topologically ordered
    * what does X unlock?              -> descendants(X)
    * where is X explained?            -> first-mention timestamp -> YouTube link
    * give me a full study path        -> topological order of the whole graph

This is retrieval over a *structured* graph rather than a vector store: the
edges encode genuine dependencies, so the "context" handed to any downstream
LLM is precise. The structured answers are fully offline; if a local LLM server
is running (see lecture2graph.neural.llm), `--explain` additionally narrates the
retrieved subgraph in prose (graceful no-op when no server is reachable).

usage:
  python -m lecture2graph.tutor.tutor <video_id> --before pre_order_traversal
  python -m lecture2graph.tutor.tutor <video_id> --path
  python -m lecture2graph.tutor.tutor <video_id> --before recursion --explain
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lecture2graph.graphs import canonical, load_graph, topological_order


class Tutor:
    def __init__(self, video_id: str, data_root: str = "data",
                 method: str = "auto"):
        self.video_id = video_id
        self.base = Path(data_root) / video_id
        self.graph = self._load_graph(method)
        self.nxg = self.graph.to_prereq_dag()
        self.timestamps = self._load_timestamps()

    def _load_graph(self, method: str):
        order = (["hybrid", "symbolic", "neural"] if method == "auto"
                 else [method])
        for m in order:
            p = self.base / f"graph.{m}.json"
            if p.exists():
                return load_graph(p, video_id=self.video_id, method=m)
        raise FileNotFoundError(f"no graph found for {self.video_id} in {self.base}")

    def _load_timestamps(self) -> dict[str, float]:
        """Canonical concept -> earliest mention time (seconds)."""
        ts: dict[str, float] = {}
        # node metadata carried through fusion (symbolic first_mention)
        for node, meta in self.graph.meta.items():
            if isinstance(meta, dict) and "first_mention" in meta:
                ts[node] = float(meta["first_mention"])
        # concepts.json is the richer source
        cpath = self.base / "concepts.json"
        if cpath.exists():
            for c in json.loads(cpath.read_text()).get("concepts", []):
                cid = canonical(c["name"])
                fm = c.get("first_mention", c.get("first_seen"))
                if fm is not None:
                    ts.setdefault(cid, float(fm))
                    ts[cid] = min(ts[cid], float(fm))
        return ts

    # ── retrieval primitives ─────────────────────────────────────────────
    def resolve(self, concept: str) -> str:
        """Map free-text input to a graph node id, fuzzily if needed."""
        cid = canonical(concept)
        if cid in self.graph.nodes:
            return cid
        from rapidfuzz import process, fuzz
        match = process.extractOne(cid, list(self.graph.nodes),
                                   scorer=fuzz.WRatio)
        if match and match[1] >= 70:
            return match[0]
        raise KeyError(
            f"'{concept}' not found. Known concepts: "
            + ", ".join(sorted(self.graph.nodes)))

    def prerequisites(self, concept: str) -> list[str]:
        import networkx as nx
        cid = self.resolve(concept)
        anc = nx.ancestors(self.nxg, cid)
        sub = self.nxg.subgraph(anc | {cid})
        return [n for n in nx.lexicographical_topological_sort(sub) if n != cid]

    def unlocks(self, concept: str) -> list[str]:
        import networkx as nx
        cid = self.resolve(concept)
        return sorted(nx.descendants(self.nxg, cid))

    def learning_path(self, concept: str) -> list[str]:
        import networkx as nx
        cid = self.resolve(concept)
        sub = self.nxg.subgraph(nx.ancestors(self.nxg, cid) | {cid})
        return list(nx.lexicographical_topological_sort(sub))

    def full_path(self) -> list[str]:
        return topological_order(self.graph)

    def youtube_link(self, concept: str) -> str | None:
        cid = self.resolve(concept)
        if cid not in self.timestamps:
            return None
        t = int(self.timestamps[cid])
        return f"https://www.youtube.com/watch?v={self.video_id}&t={t}s"

    # ── optional LLM narration over the retrieved subgraph ───────────────
    def explain(self, concept: str) -> str | None:
        """Narrate the retrieved prerequisite subgraph with the local LLM.

        Returns None (rather than raising) if no local model server is
        reachable — narration is a nicety, the structured answer is the product.
        """
        from lecture2graph.neural import llm

        prereqs = self.prerequisites(concept)
        context = "\n".join(
            f"- {s} -> {t}" for s, t in self.graph.prereq_edge_keys()
            if t == self.resolve(concept) or s in prereqs
        )
        prompt = (
            f"A student wants to learn '{concept}'. Based ONLY on this "
            f"prerequisite graph (edges 'A -> B' mean learn A before B):\n"
            f"{context}\n\nIn 3-4 sentences, explain the order they should study "
            f"these concepts and why, grounded strictly in the graph.")
        try:
            return llm.chat(
                "You are a concise study advisor.", prompt,
                temperature=0.2, json_mode=False, max_tokens=400).strip()
        except (ConnectionError, RuntimeError):
            return None


def _print_list(title: str, items: list[str], tutor: "Tutor" = None) -> None:
    print(f"\n{title}")
    if not items:
        print("  (none)")
        return
    for i, c in enumerate(items, 1):
        link = ""
        if tutor and c in tutor.timestamps:
            link = f"   [{int(tutor.timestamps[c])}s]"
        print(f"  {i}. {c}{link}")


def main() -> None:
    p = argparse.ArgumentParser(description="Graph-RAG tutor over the concept DAG")
    p.add_argument("video_id")
    p.add_argument("--data-root", default="data")
    p.add_argument("--method", default="auto",
                   choices=["auto", "symbolic", "neural", "hybrid"])
    p.add_argument("--before", metavar="CONCEPT",
                   help="show prerequisites + study path for CONCEPT")
    p.add_argument("--unlocks", metavar="CONCEPT",
                   help="show what CONCEPT unlocks")
    p.add_argument("--where", metavar="CONCEPT",
                   help="show the YouTube timestamp where CONCEPT is introduced")
    p.add_argument("--path", action="store_true",
                   help="print the full topological study path")
    p.add_argument("--explain", action="store_true",
                   help="also narrate with the local LLM (needs a running server)")
    args = p.parse_args()

    t = Tutor(args.video_id, args.data_root, args.method)
    print(f"[tutor] {args.video_id} — using '{t.graph.method}' graph "
          f"({len(t.graph.nodes)} concepts, {len(t.graph.edges)} edges)")

    if args.before:
        _print_list(f"To learn '{args.before}', study these first:",
                    t.prerequisites(args.before), t)
        _print_list("Full study path (prereqs -> target):",
                    t.learning_path(args.before), t)
        if args.explain:
            narration = t.explain(args.before)
            print("\nLLM narration:\n  " + (narration or
                  "(start a local LLM server to enable narration)"))
    if args.unlocks:
        _print_list(f"'{args.unlocks}' unlocks:", t.unlocks(args.unlocks), t)
    if args.where:
        link = t.youtube_link(args.where)
        print(f"\n'{args.where}' is introduced at: {link or '(no timestamp available)'}")
    if args.path:
        _print_list("Full topological study path:", t.full_path(), t)
    if not any([args.before, args.unlocks, args.where, args.path]):
        _print_list("Full topological study path:", t.full_path(), t)


if __name__ == "__main__":
    main()
