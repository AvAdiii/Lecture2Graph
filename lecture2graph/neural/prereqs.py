"""
module 5 (neural): prerequisite graph via a local LLM.

WHY LLM:
  The symbolic pipeline used three heuristic strategies to build prerequisite
  edges:
    1. Hardcoded domain rules (~80 rules like "array -> sorting")
    2. Causal language detection (regex for "before we learn X, need Y")
    3. Temporal ordering (first-mentioned -> prerequisite of later-mentioned)

  Problems:
    - Domain rules were incomplete and domain-specific
    - Causal regex missed paraphrased / code-mixed causal language
    - Temporal ordering produced many false positives

  This module sends concepts + transcript context to a local LLM and asks it to
  *reason* about genuine prerequisites. The LLM can:
    - Understand "you need to know X before Y" in any paraphrase
    - Apply CS domain knowledge from its training data
    - Distinguish genuine prerequisites from mere co-occurrence
    - Explain *why* each edge exists

LOCAL, NOT CLOUD:
  Runs against a local OpenAI-compatible server (Ollama by default, see
  lecture2graph.neural.llm). One request per video, no API key.

OUTPUT:
  Same format as the symbolic pipeline for compatibility with M6 (visualize):
  {"edges": [...], "topological_order": [...]}
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict, deque

from lecture2graph.neural import llm


# ───────────────── prompt ─────────────────

_SYSTEM_PROMPT = """\
You are an expert computer science educator building a prerequisite knowledge graph.
Given a list of CS concepts from a lecture, output the directed edges that say
which concept must be learned BEFORE which other concept.

############  EDGE DIRECTION: READ THIS TWICE  ############
Every edge is {"from": A, "to": B} and MUST mean: learn A FIRST, then B.
  * "from" = the PREREQUISITE, the simpler / more general / foundational idea.
  * "to"   = the concept that DEPENDS on it, more advanced or more specific.

Get the arrow the right way round. The most common mistake is reversing it:
  CORRECT: {"from": "tree_traversal", "to": "pre_order_traversal"}
           (pre-order is a SPECIFIC KIND of traversal -> learn the general idea first)
  WRONG:   {"from": "pre_order_traversal", "to": "tree_traversal"}
  CORRECT: {"from": "tree", "to": "binary_tree"}      (binary tree is a kind of tree)
  CORRECT: {"from": "graph", "to": "graph_traversal"} (need a graph before traversing it)
  CORRECT: {"from": "stack", "to": "depth_first_search"} (DFS uses a stack)
  CORRECT: {"from": "recursion", "to": "factorial"}   (factorial shown via recursion)
General-before-specific and foundation-before-application: the general/foundational
concept is ALWAYS the "from".
###########################################################

RULES:
1. Add an edge for every genuine "learn A before B" relationship, include
   general->specific (a concept and its sub-types) and foundation->application.
   Aim for good coverage, but never invent relationships that aren't real.
   - "array" -> "sorting" (need arrays to learn sorting)        ✓
   - "recursion" -> "merge_sort" (merge sort uses recursion)    ✓
   - "binary_tree" -> "array" (trees don't require arrays)      ✗
2. Classify each edge with "type":
   - "domain_rule": CS domain knowledge (A is foundationally needed for B)
   - "causal": the lecturer explicitly said A is needed before B
3. Give a brief "rule" explaining each edge.
4. The graph MUST be a DAG (no cycles): if A->B then never B->A.
5. Produce a topological ordering of ALL concepts (prerequisites first).

RESPOND WITH ONLY valid JSON, no markdown fences:
{
  "edges": [
    {"from": "array", "to": "sorting", "type": "domain_rule",
     "rule": "sorting algorithms operate on arrays"}
  ],
  "topological_order": ["array", "recursion", "sorting", "merge_sort"]
}"""


# ───────────────── helpers ─────────────────

def _format_concepts(concepts: list[dict]) -> str:
    """Format concept list for the prompt."""
    lines = []
    for c in concepts:
        name = c.get("name", "")
        mentions = c.get("mentions", 0) or 0
        first = c.get("first_seen", c.get("first_mention", 0))
        first = float(first) if isinstance(first, (int, float)) else 0.0
        sources = ", ".join(c.get("sources", []) or [])
        lines.append(f"  - {name} (mentioned {mentions}x, "
                     f"first at t={first:.1f}s, sources: {sources})")
    return "\n".join(lines)


def _build_transcript_summary(segments: list[dict],
                               concepts: list[dict]) -> str:
    """Pick segments that mention concepts, compact summary for context."""
    concept_names = set()
    for c in concepts:
        name = c["name"].replace("_", " ").lower()
        concept_names.add(name)
        # also add without spaces for compound terms
        concept_names.add(name.replace(" ", ""))

    relevant = []
    for seg in segments:
        text_lower = seg.get("text", "").lower()
        for cname in concept_names:
            if cname in text_lower:
                t = seg.get("start", 0)
                src = seg.get("source", "?")[0]
                relevant.append(f"  [{t:.0f}s|{src}] {seg['text'][:120]}")
                break

    # cap at 50 to stay within token limits
    if len(relevant) > 50:
        step = len(relevant) / 50
        relevant = [relevant[int(i * step)] for i in range(50)]

    return "\n".join(relevant) if relevant else "  (no matching segments)"


# ───────────────── DAG verification ─────────────────

def verify_dag(concepts: list[str], edges: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Verify graph is a DAG. Remove edges to break cycles if needed.
    Returns: (clean_edges, topological_order)
    """
    graph = defaultdict(set)
    in_degree = defaultdict(int)
    all_nodes = set(concepts)

    for e in edges:
        src, tgt = e["from"], e["to"]
        if src in all_nodes and tgt in all_nodes and src != tgt:
            if tgt not in graph[src]:
                graph[src].add(tgt)
                in_degree[tgt] += 1

    for n in all_nodes:
        if n not in in_degree:
            in_degree[n] = 0

    # Kahn's algorithm
    queue = deque(sorted(n for n in all_nodes if in_degree[n] == 0))
    topo = []
    visited = set()

    while queue:
        node = queue.popleft()
        topo.append(node)
        visited.add(node)
        for neighbor in sorted(graph.get(node, [])):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topo) == len(all_nodes):
        clean_edges = [e for e in edges
                       if e["from"] in all_nodes and e["to"] in all_nodes
                       and e["from"] != e["to"]]
        return clean_edges, topo

    # cycles detected, remove back-edges
    print(f"[m5] WARNING: cycle detected, removing back-edges "
          f"({len(visited)}/{len(all_nodes)} visited)")
    remaining = all_nodes - visited
    clean_edges = [e for e in edges
                   if e["from"] not in remaining and e["to"] not in remaining
                   and e["from"] in all_nodes and e["to"] in all_nodes
                   and e["from"] != e["to"]]
    topo.extend(sorted(remaining))
    return clean_edges, topo


# ───────────────── core ─────────────────

def build_prerequisites(concepts: list[dict], segments: list[dict]) -> dict:
    """
    Send concepts + transcript context to the local LLM, build prerequisite DAG.
    Single call. Returns: {"edges": [...], "topological_order": [...]}
    """
    if not concepts:
        print("[m5] no concepts, returning empty graph")
        return {"edges": [], "topological_order": []}

    concept_text = _format_concepts(concepts)
    transcript_summary = _build_transcript_summary(segments, concepts)

    user_prompt = (
        f"Here are {len(concepts)} CS concepts from a lecture, with context:\n\n"
        f"CONCEPTS:\n{concept_text}\n\n"
        f"RELEVANT TRANSCRIPT EXCERPTS:\n{transcript_summary}\n\n"
        f"Build the prerequisite graph. Remember:\n"
        f"- Only genuine prerequisites (A must be known before B).\n"
        f"- Include ALL concepts in topological_order, even isolated ones.\n"
        f"- Graph must be a DAG (no cycles).\n"
        f"- Be conservative, fewer correct edges > many wrong ones.\n\n"
        f"Return ONLY valid JSON."
    )

    print(f"[m5] sending {len(concepts)} concepts to local LLM ({llm.model()}) "
          f"for prerequisite analysis...")

    raw = llm.chat(_SYSTEM_PROMPT, user_prompt, temperature=0.1)

    try:
        result = llm.extract_json(raw)
    except json.JSONDecodeError as e:
        print(f"[m5] WARNING: invalid JSON from LLM: {e}")
        print(f"[m5] raw (first 300 chars): {raw[:300]}")
        result = {"edges": [], "topological_order": []}

    raw_edges = result.get("edges", [])

    # normalize edge format
    edges = []
    for e in raw_edges:
        edges.append({
            "from": e.get("from", ""),
            "to": e.get("to", ""),
            "type": e.get("type", "domain_rule"),
            "rule": e.get("rule", ""),
        })

    # verify DAG
    concept_names = [c["name"] for c in concepts]
    clean_edges, topo = verify_dag(concept_names, edges)

    print(f"[m5] prerequisite graph: {len(clean_edges)} edges, "
          f"{len(topo)}/{len(concepts)} topo order")

    return {"edges": clean_edges, "topological_order": topo}


# ───────────────── run ─────────────────

def run(video_id: str, data_root: str) -> dict:
    """
    Build prerequisite graph for a video using the local LLM.

    Reads:  concepts.json, normalized_segments.json
    Writes: graph.json
    Returns: {"total_edges": N, "topo_size": M, "graph_path": "..."}
    """
    data_dir = Path(data_root) / video_id
    concepts_path = data_dir / "concepts.json"
    norm_path = data_dir / "normalized_segments.json"
    graph_path = data_dir / "graph.json"

    # cache check
    if graph_path.exists():
        with open(graph_path) as f:
            existing = json.load(f)
        n = len(existing.get("edges", []))
        t = len(existing.get("topological_order", []))
        print(f"[m5] using cached graph: {n} edges, {t} topo")
        return {"total_edges": n, "topo_size": t, "graph_path": str(graph_path)}

    if not concepts_path.exists():
        raise FileNotFoundError(f"[m5] {concepts_path} not found, run M4 first")

    with open(concepts_path) as f:
        concepts_data = json.load(f)
    concepts = concepts_data.get("concepts", [])

    segments = []
    if norm_path.exists():
        with open(norm_path) as f:
            segments = json.load(f)

    result = build_prerequisites(concepts, segments)

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    n_edges = len(result.get("edges", []))
    n_topo = len(result.get("topological_order", []))
    print(f"[m5] saved graph -> {graph_path}")
    return {"total_edges": n_edges, "topo_size": n_topo,
            "graph_path": str(graph_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    print(run(args.video_id, args.data_root))
