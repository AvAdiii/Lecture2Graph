"""
module 5 - prerequisite mapping (v2)

takes concepts.json and normalized_segments.json, produces graph.json.

v2 changes:
  - temporal edges: only for pairs NOT connected by domain rules
  - temporal edges: max 3 out-edges per source concept, gap > 60s
  - causal anchor -> edge conversion for "definition" and "temporal_sequence" types
  - confidence boosting when causal anchors validate domain rules
  - fixed topo order (was stuck at 3/14 due to temporal edge density)
"""

import json
import re
from pathlib import Path
from collections import defaultdict


# ------------------------------------------------------------------
# domain knowledge
# ------------------------------------------------------------------

_DOMAIN_RULES = [
    # --- tree traversal domain ---
    ("tree", "binary tree", "is_prerequisite_for", 0.9),
    ("tree", "tree traversal", "is_prerequisite_for", 0.9),
    ("binary tree", "tree traversal", "is_prerequisite_for", 0.9),
    ("node", "root node", "is_prerequisite_for", 0.8),
    ("node", "leaf node", "is_prerequisite_for", 0.8),
    ("root node", "tree traversal", "is_prerequisite_for", 0.8),
    ("children", "left subtree", "is_prerequisite_for", 0.7),
    ("children", "right subtree", "is_prerequisite_for", 0.7),
    ("tree traversal", "pre-order traversal", "refines", 0.9),
    ("tree traversal", "in-order traversal", "refines", 0.9),
    ("tree traversal", "post-order traversal", "refines", 0.9),
    ("traversal technique", "pre-order traversal", "is_prerequisite_for", 0.7),
    ("traversal technique", "in-order traversal", "is_prerequisite_for", 0.7),
    ("traversal technique", "post-order traversal", "is_prerequisite_for", 0.7),
    ("left subtree", "pre-order traversal", "is_prerequisite_for", 0.7),
    ("right subtree", "pre-order traversal", "is_prerequisite_for", 0.7),
    ("left subtree", "in-order traversal", "is_prerequisite_for", 0.7),
    ("right subtree", "in-order traversal", "is_prerequisite_for", 0.7),
    ("left subtree", "post-order traversal", "is_prerequisite_for", 0.7),
    ("right subtree", "post-order traversal", "is_prerequisite_for", 0.7),
    ("dummy node", "traversal technique", "is_part_of", 0.6),
    # --- BFS / DFS / graph domain ---
    ("graph", "graph traversal", "is_prerequisite_for", 0.9),
    ("vertex", "graph", "is_prerequisite_for", 0.7),
    ("edge", "graph", "is_prerequisite_for", 0.7),
    ("graph traversal", "breadth first search", "refines", 0.9),
    ("graph traversal", "depth first search", "refines", 0.9),
    ("graph", "breadth first search", "is_prerequisite_for", 0.8),
    ("graph", "depth first search", "is_prerequisite_for", 0.8),
    ("queue", "breadth first search", "is_prerequisite_for", 0.8),
    ("stack", "depth first search", "is_prerequisite_for", 0.8),
    ("visited", "breadth first search", "is_prerequisite_for", 0.7),
    ("visited", "depth first search", "is_prerequisite_for", 0.7),
    ("adjacency list", "breadth first search", "is_prerequisite_for", 0.6),
    ("adjacency list", "depth first search", "is_prerequisite_for", 0.6),
    ("node", "vertex", "is_prerequisite_for", 0.5),
    ("breadth first search", "shortest path", "is_prerequisite_for", 0.7),
    ("connected component", "graph traversal", "is_prerequisite_for", 0.6),
    # --- DBMS / keys domain ---
    ("database", "relation", "is_prerequisite_for", 0.9),
    ("relation", "attribute", "is_prerequisite_for", 0.8),
    ("relation", "tuple", "is_prerequisite_for", 0.8),
    ("attribute", "candidate key", "is_prerequisite_for", 0.8),
    ("attribute", "super key", "is_prerequisite_for", 0.8),
    ("unique constraint", "candidate key", "is_prerequisite_for", 0.8),
    ("not null", "primary key", "is_prerequisite_for", 0.8),
    ("null", "not null", "is_prerequisite_for", 0.7),
    ("candidate key", "primary key", "is_prerequisite_for", 0.9),
    ("candidate key", "alternate key", "is_prerequisite_for", 0.8),
    ("super key", "candidate key", "refines", 0.85),
    ("primary key", "foreign key", "is_prerequisite_for", 0.85),
    ("primary key", "composite key", "is_prerequisite_for", 0.7),
    ("unique constraint", "primary key", "is_prerequisite_for", 0.8),
    ("constraint", "unique constraint", "refines", 0.7),
    ("constraint", "not null", "refines", 0.7),
    ("relation", "normalization", "is_prerequisite_for", 0.8),
    ("functional dependency", "normalization", "is_prerequisite_for", 0.8),
    ("primary key", "normalization", "is_prerequisite_for", 0.7),
    ("attribute", "functional dependency", "is_prerequisite_for", 0.7),
    ("database", "sql", "is_prerequisite_for", 0.8),
    ("relation", "sql", "is_prerequisite_for", 0.7),
    ("database", "schema", "is_prerequisite_for", 0.8),
    ("entity", "relation", "is_prerequisite_for", 0.7),
    # --- sorting / searching ---
    ("algorithm", "sorting", "is_prerequisite_for", 0.7),
    ("algorithm", "searching", "is_prerequisite_for", 0.7),
    ("sorting", "bubble sort", "refines", 0.9),
    ("sorting", "merge sort", "refines", 0.9),
    ("sorting", "quick sort", "refines", 0.9),
    ("sorting", "insertion sort", "refines", 0.9),
    ("sorting", "selection sort", "refines", 0.9),
    ("searching", "binary search", "refines", 0.9),
    ("searching", "linear search", "refines", 0.9),
    ("array", "sorting", "is_prerequisite_for", 0.7),
    ("array", "searching", "is_prerequisite_for", 0.7),
    ("recursion", "merge sort", "is_prerequisite_for", 0.7),
    ("recursion", "quick sort", "is_prerequisite_for", 0.7),
    ("algorithm", "time complexity", "is_prerequisite_for", 0.7),
    ("algorithm", "space complexity", "is_prerequisite_for", 0.7),
    # --- general CS ---
    ("data structure", "array", "refines", 0.8),
    ("data structure", "linked list", "refines", 0.8),
    ("data structure", "stack", "refines", 0.8),
    ("data structure", "queue", "refines", 0.8),
    ("data structure", "hash table", "refines", 0.8),
    ("data structure", "tree", "refines", 0.8),
    ("data structure", "graph", "refines", 0.8),
    ("pointer", "linked list", "is_prerequisite_for", 0.7),
    ("array", "hash table", "is_prerequisite_for", 0.6),
]


# ------------------------------------------------------------------
# causal anchor detection
# ------------------------------------------------------------------

_CAUSAL_PATTERNS = [
    (r"before\s+(?:we\s+)?(?:do|discuss|learn|see|talk)\s+(.+?),\s*(?:you\s+)?(?:need|must|should)\s+(?:to\s+)?(?:know|understand|learn)\s+(.+)",
     "prerequisite_explicit"),
    (r"first\s+(?:we\s+)?(?:write|do|see|learn)\s+(.+?),\s*then\s+(.+)",
     "temporal_sequence"),
    (r"(?:remember|recall|as\s+we\s+(?:saw|discussed|did))\s+(.+?)(?:\s+from\s+before|\s+earlier|\?)",
     "back_reference"),
    (r"(\w[\w\s-]+)\s+means\s+(\w[\w\s-]+)",
     "definition"),
]

# concept name fragments for matching inside causal anchor text
_CONCEPT_FRAGMENTS = {
    # tree domain
    "pre-order": "pre-order traversal",
    "preorder": "pre-order traversal",
    "pre order": "pre-order traversal",
    "in-order": "in-order traversal",
    "inorder": "in-order traversal",
    "in order": "in-order traversal",
    "post-order": "post-order traversal",
    "postorder": "post-order traversal",
    "post order": "post-order traversal",
    "root node": "root node",
    "root": "root node",
    "left": "left subtree",
    "right": "right subtree",
    "tree": "tree",
    "node": "node",
    "vertex": "vertex",
    "leaf": "leaf node",
    "binary tree": "binary tree",
    "children": "children",
    "child": "children",
    # BFS/DFS domain
    "breadth first search": "breadth first search",
    "breadth first": "breadth first search",
    "bfs": "breadth first search",
    "depth first search": "depth first search",
    "depth first": "depth first search",
    "dfs": "depth first search",
    "graph traversal": "graph traversal",
    "graph": "graph",
    "queue": "queue",
    "stack": "stack",
    "visited": "visited",
    "adjacency": "adjacency list",
    "edge": "edge",
    "shortest path": "shortest path",
    # DBMS domain
    "primary key": "primary key",
    "candidate key": "candidate key",
    "super key": "super key",
    "foreign key": "foreign key",
    "composite key": "composite key",
    "alternate key": "alternate key",
    "unique": "unique constraint",
    "not null": "not null",
    "null": "null",
    "attribute": "attribute",
    "column": "attribute",
    "tuple": "tuple",
    "row": "tuple",
    "relation": "relation",
    "table": "relation",
    "database": "database",
    "dbms": "database",
    "normalization": "normalization",
    "functional dependency": "functional dependency",
    "schema": "schema",
    "entity": "entity",
    "sql": "sql",
    "sequel": "sql",
    "constraint": "constraint",
    "index": "index",
}


def detect_causal_anchors(segments: list) -> list:
    anchors = []
    for seg in segments:
        # handle both old format ("spoken_text") and new format ("text")
        text = seg.get("spoken_text", seg.get("text", "")).lower()
        for pattern, anchor_type in _CAUSAL_PATTERNS:
            for match in re.finditer(pattern, text):
                anchors.append({
                    "type": anchor_type,
                    "match": match.group(0)[:100],
                    "groups": [g for g in match.groups() if g],
                    "timestamp": seg["start"],
                })
    return anchors


def _find_concepts_in_text(text: str, concept_names: set) -> set:
    """find concept names mentioned in a causal anchor text fragment."""
    found = set()
    text_lower = text.lower().strip()
    # check longest fragments first to prefer specific matches
    for frag, concept in sorted(_CONCEPT_FRAGMENTS.items(), key=lambda x: -len(x[0])):
        if concept in concept_names and frag in text_lower:
            found.add(concept)
    return found


def convert_causal_to_edges(anchors: list, concept_names: set, domain_pairs: set) -> list:
    """convert causal anchors to prerequisite edges.
    skip edges that contradict existing domain rules (reverse direction)."""
    edges = []
    seen = set()
    for anchor in anchors:
        groups = anchor.get("groups", [])
        if len(groups) < 2:
            continue

        if anchor["type"] == "definition":
            defined = _find_concepts_in_text(groups[0], concept_names)
            definition_deps = _find_concepts_in_text(groups[1], concept_names)
            for dep in definition_deps:
                for tgt in defined:
                    if dep != tgt and (dep, tgt) not in seen:
                        # skip if domain already has reverse direction
                        if (tgt, dep) in domain_pairs:
                            continue
                        seen.add((dep, tgt))
                        edges.append({
                            "source": dep,
                            "target": tgt,
                            "type": "is_prerequisite_for",
                            "confidence": 0.75,
                        })

        elif anchor["type"] == "temporal_sequence":
            first_concepts = _find_concepts_in_text(groups[0], concept_names)
            then_concepts = _find_concepts_in_text(groups[1], concept_names)
            for fc in first_concepts:
                for tc in then_concepts:
                    if fc != tc and (fc, tc) not in seen:
                        if (tc, fc) in domain_pairs:
                            continue
                        seen.add((fc, tc))
                        edges.append({
                            "source": fc,
                            "target": tc,
                            "type": "is_prerequisite_for",
                            "confidence": 0.7,
                        })

    return edges


# ------------------------------------------------------------------
# temporal ordering (conservative)
# ------------------------------------------------------------------

_MAX_TEMPORAL_OUT = 3
_TEMPORAL_GAP_MIN = 30  # lowered from 60 to work with shorter videos (~10min)


def _compute_reachable(adj: dict, start: str) -> set:
    """BFS to find all nodes reachable from start in the directed graph."""
    visited = set()
    queue = [start]
    while queue:
        nd = queue.pop(0)
        if nd in visited:
            continue
        visited.add(nd)
        for nb in adj.get(nd, []):
            queue.append(nb)
    visited.discard(start)
    return visited


def build_temporal_edges(concepts: list, strong_edges: list) -> list:
    """
    temporal edges only between concepts with NO path in either direction
    via domain/causal edges (transitive closure check).
    This prevents cycles from temporal contradicting domain ordering.
    """
    # build adjacency from domain+causal edges
    adj = defaultdict(list)
    for e in strong_edges:
        adj[e["source"]].append(e["target"])

    # pre-compute transitive reachability for each concept
    concept_names = [c["name"] for c in concepts]
    reachable = {}
    for cn in concept_names:
        reachable[cn] = _compute_reachable(adj, cn)

    edges = []
    out_count = defaultdict(int)

    for i, c1 in enumerate(concepts):
        for c2 in concepts[i+1:]:
            # skip if any transitive path exists between them in either direction
            if c2["name"] in reachable.get(c1["name"], set()):
                continue
            if c1["name"] in reachable.get(c2["name"], set()):
                continue
            gap = c2["first_mention"] - c1["first_mention"]
            if gap <= _TEMPORAL_GAP_MIN:
                continue
            if out_count[c1["name"]] >= _MAX_TEMPORAL_OUT:
                break
            weight = max(0.3, min(0.5, 1.0 - gap / 400))
            edges.append({
                "source": c1["name"],
                "target": c2["name"],
                "type": "temporal_precedence",
                "confidence": round(weight, 2),
            })
            out_count[c1["name"]] += 1
    return edges


# ------------------------------------------------------------------
# dag verification
# ------------------------------------------------------------------

def verify_dag(nodes: list, edges: list) -> list:
    node_set = set(nodes)
    max_iterations = 10
    for _ in range(max_iterations):
        adj = defaultdict(list)
        in_degree = {n: 0 for n in nodes}
        for e in edges:
            if e["source"] in node_set and e["target"] in node_set:
                adj[e["source"]].append(e["target"])
                in_degree[e["target"]] += 1

        queue = [n for n in nodes if in_degree[n] == 0]
        visited = set()
        while queue:
            nd = queue.pop(0)
            visited.add(nd)
            for nb in adj.get(nd, []):
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    queue.append(nb)

        if len(visited) == len(node_set):
            return edges  # no cycles

        # cycle: remove lowest-confidence edge
        sorted_edges = sorted(edges, key=lambda e: e["confidence"])
        for e in sorted_edges:
            test_edges = [x for x in edges if x is not e]
            adj2 = defaultdict(list)
            in2 = {n: 0 for n in nodes}
            for ex in test_edges:
                if ex["source"] in node_set and ex["target"] in node_set:
                    adj2[ex["source"]].append(ex["target"])
                    in2[ex["target"]] += 1
            q2 = [n for n in nodes if in2[n] == 0]
            v2 = set()
            while q2:
                nd = q2.pop(0)
                v2.add(nd)
                for nb in adj2.get(nd, []):
                    in2[nb] -= 1
                    if in2[nb] == 0:
                        q2.append(nb)
            if len(v2) == len(node_set):
                print(f"  [m5] removed cycle edge: {e['source']} -> {e['target']} (conf={e['confidence']})")
                edges = test_edges
                break
        else:
            break  # couldn't fix
    return edges


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------

def run(video_id: str, data_root: str = "data") -> dict:
    out_dir = Path(data_root) / video_id
    concepts_path = out_dir / "concepts.json"
    normalized_path = out_dir / "normalized_segments.json"
    graph_path = out_dir / "graph.json"

    if graph_path.exists():
        print(f"[m5] graph already exists, loading: {graph_path}")
        with open(graph_path) as f:
            return json.load(f)

    with open(concepts_path) as f:
        concepts_data = json.load(f)
    with open(normalized_path) as f:
        normalized = json.load(f)

    concepts = concepts_data["concepts"]
    concept_names = [c["name"] for c in concepts]
    concept_set = set(concept_names)

    print(f"[m5] building prerequisite graph for {len(concepts)} concepts")

    # 1. domain edges
    domain_edges = []
    domain_pairs = set()
    for prereq, dep, edge_type, conf in _DOMAIN_RULES:
        if prereq in concept_set and dep in concept_set:
            domain_edges.append({
                "source": prereq, "target": dep,
                "type": edge_type, "confidence": conf,
            })
            domain_pairs.add((prereq, dep))

    # 2. causal anchor edges
    causal_anchors = detect_causal_anchors(normalized)
    causal_edges = convert_causal_to_edges(causal_anchors, concept_set, domain_pairs)

    # boost domain edges that are also supported by causal evidence
    causal_pairs = {(e["source"], e["target"]) for e in causal_edges}
    for de in domain_edges:
        if (de["source"], de["target"]) in causal_pairs:
            de["confidence"] = min(1.0, de["confidence"] + 0.1)

    # 3. temporal edges (conservative — uses transitive closure of domain+causal)
    strong_edges = domain_edges + causal_edges
    temporal_edges = build_temporal_edges(concepts, strong_edges)

    # merge: domain > causal > temporal
    all_edges = []
    seen_pairs = set()

    for e in domain_edges:
        pair = (e["source"], e["target"])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            all_edges.append(e)

    for e in causal_edges:
        pair = (e["source"], e["target"])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            all_edges.append(e)

    for e in temporal_edges:
        pair = (e["source"], e["target"])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            all_edges.append(e)

    # 4. verify DAG
    all_edges = verify_dag(concept_names, all_edges)

    # build nodes
    nodes = []
    for c in concepts:
        nodes.append({
            "id": c["name"],
            "mention_count": c["mention_count"],
            "first_mention": c["first_mention"],
            "last_mention": c["last_mention"],
            "sources": c["sources"],
        })

    # topological sort
    adj = defaultdict(list)
    in_deg = {n["id"]: 0 for n in nodes}
    for e in all_edges:
        adj[e["source"]].append(e["target"])
        in_deg[e["target"]] += 1

    topo_order = []
    queue = sorted([n["id"] for n in nodes if in_deg[n["id"]] == 0])
    while queue:
        nd = queue.pop(0)
        topo_order.append(nd)
        for nb in sorted(adj.get(nd, [])):
            in_deg[nb] -= 1
            if in_deg[nb] == 0:
                queue.append(nb)

    graph = {
        "video_id": video_id,
        "total_nodes": len(nodes),
        "total_edges": len(all_edges),
        "topological_order": topo_order,
        "nodes": nodes,
        "edges": all_edges,
        "causal_anchors_detected": len(causal_anchors),
        "causal_edges_created": len(causal_edges),
        "example_tree": concepts_data.get("example_tree", {}),
    }

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"[m5] graph: {len(nodes)} nodes, {len(all_edges)} edges")
    print(f"[m5] causal anchors detected: {len(causal_anchors)}, edges created: {len(causal_edges)}")
    print(f"[m5] topological order ({len(topo_order)} nodes):")
    print(f"      {' -> '.join(topo_order)}")

    edge_types = defaultdict(int)
    for e in all_edges:
        edge_types[e["type"]] += 1
    for t, count in sorted(edge_types.items()):
        print(f"  {t}: {count} edges")

    print(f"[m5] -> {graph_path}")
    return graph


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    run(args.video_id, args.data_root)
