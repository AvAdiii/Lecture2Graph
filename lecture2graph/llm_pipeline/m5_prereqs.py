"""
module 5 — prerequisite graph via Groq LLM  (LLM pipeline)

WHY LLM:
  the regex pipeline used three heuristic strategies to build prerequisite edges:
    1. Hardcoded domain rules (~80 rules like "array → sorting")
    2. Causal language detection (regex for "before we learn X, need Y")
    3. Temporal ordering (first-mentioned → prerequisite of later-mentioned)

  Problems:
    - Domain rules were incomplete and domain-specific
    - Causal regex missed paraphrased / code-mixed causal language
    - Temporal ordering produced many false positives

  this pipeline sends concepts + transcript context to Groq (Llama 3.3 70B)
  and asks it to *reason* about genuine prerequisites. The LLM can:
    - Understand "you need to know X before Y" in any paraphrase
    - Apply CS domain knowledge from its training data
    - Distinguish genuine prerequisites from mere co-occurrence
    - Explain *why* each edge exists

REQUEST MINIMIZATION:
  Single API call per video — sends concept list + relevant transcript
  excerpts in one request. → exactly 1 request per video.

OUTPUT:
  Same format as the regex pipeline for compatibility with M6 (visualize):
  {"edges": [...], "topological_order": [...]}
"""

import json
import re
import time
import argparse
from pathlib import Path
from collections import defaultdict, deque

from groq import Groq


# ───────────────── config ─────────────────

_MODEL = "llama-3.3-70b-versatile"
_MAX_RETRIES = 4
_RETRY_DELAY = 10

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ───────────────── prompt ─────────────────

_SYSTEM_PROMPT = """\
You are an expert computer science educator building a prerequisite knowledge graph.
Given a list of CS concepts from a lecture, determine which concepts are
PREREQUISITES of which other concepts.

A prerequisite means: "a student MUST understand concept A before they can
properly understand concept B."

RULES:
1. Only add an edge A→B if A is a genuine prerequisite of B.
   - "array" → "sorting" (YES: you need arrays to learn sorting)
   - "recursion" → "merge_sort" (YES: merge sort uses recursion)
   - "binary_tree" → "array" (NO: trees don't require arrays)
2. Be conservative. Fewer correct edges > many questionable ones.
3. Classify each edge:
   - "domain_rule": based on CS domain knowledge (A is foundationally needed for B)
   - "causal": the lecturer explicitly said A is needed before B
   - "temporal": A was taught first and B builds on it in the lecture
4. Provide a brief "rule" explanation for each edge.
5. The graph MUST be a DAG (no cycles). If A→B, then B must NOT→A.
6. Produce a valid topological ordering of ALL concepts (even isolated ones).

RESPOND WITH ONLY valid JSON — no markdown fences:
{
  "edges": [
    {"from": "array", "to": "sorting", "type": "domain_rule",
     "rule": "sorting algorithms operate on arrays"}
  ],
  "topological_order": ["array", "recursion", "sorting", "merge_sort"]
}"""


# ───────────────── helpers ─────────────────

def _call_groq(client: Groq, system: str, user: str) -> str:
    """Call Groq with retry + exponential backoff."""
    delay = _RETRY_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=8000,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() or "429" in err:
                print(f"[m5] rate limited (attempt {attempt+1}/{_MAX_RETRIES}), "
                      f"waiting {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError(f"[m5] Groq failed after {_MAX_RETRIES} retries")


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    return json.loads(text)


def _format_concepts(concepts: list[dict]) -> str:
    """Format concept list for the prompt."""
    lines = []
    for c in concepts:
        name = c.get("name", "")
        mentions = c.get("mentions", 0)
        first = c.get("first_seen", 0)
        sources = ", ".join(c.get("sources", []))
        lines.append(f"  - {name} (mentioned {mentions}x, "
                     f"first at t={first:.1f}s, sources: {sources})")
    return "\n".join(lines)


def _build_transcript_summary(segments: list[dict],
                               concepts: list[dict]) -> str:
    """Pick segments that mention concepts — compact summary for context."""
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

    # cycles detected — remove back-edges
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

def build_prerequisites(concepts: list[dict], segments: list[dict],
                        api_key: str) -> dict:
    """
    Send concepts + transcript context to Groq, build prerequisite DAG.
    Single API call. Returns: {"edges": [...], "topological_order": [...]}
    """
    if not concepts:
        print("[m5] no concepts — returning empty graph")
        return {"edges": [], "topological_order": []}

    client = Groq(api_key=api_key)

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
        f"- Be conservative — fewer correct edges > many wrong ones.\n\n"
        f"Return ONLY valid JSON."
    )

    print(f"[m5] sending {len(concepts)} concepts to Groq ({_MODEL}) "
          f"for prerequisite analysis...")

    raw = _call_groq(client, _SYSTEM_PROMPT, user_prompt)

    try:
        result = _parse_json(raw)
    except json.JSONDecodeError as e:
        print(f"[m5] WARNING: invalid JSON from Groq: {e}")
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

def run(video_id: str, data_root: str, api_key: str = None) -> dict:
    """
    Build prerequisite graph for a video using Groq LLM.

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
        raise FileNotFoundError(f"[m5] {concepts_path} not found — run M4 first")

    with open(concepts_path) as f:
        concepts_data = json.load(f)
    concepts = concepts_data.get("concepts", [])

    segments = []
    if norm_path.exists():
        with open(norm_path) as f:
            segments = json.load(f)

    if not api_key:
        api_key = _load_api_key(data_dir)

    result = build_prerequisites(concepts, segments, api_key)

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    n_edges = len(result.get("edges", []))
    n_topo = len(result.get("topological_order", []))
    print(f"[m5] saved graph → {graph_path}")
    return {"total_edges": n_edges, "topo_size": n_topo,
            "graph_path": str(graph_path)}


def _load_api_key(data_dir: Path) -> str:
    """Try loading API key from env var or .env file."""
    import os
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    for p in [PROJECT_ROOT / ".env", data_dir.parent / ".env", data_dir.parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("GROQ_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("[m5] No API key — set GROQ_API_KEY env var or pass api_key=")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="outputs/llm")
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()
    print(run(args.video_id, args.data_root, args.api_key))
