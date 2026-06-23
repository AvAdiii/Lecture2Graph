"""
module 4 - concept extraction (v2)

takes normalized_segments.json and produces concepts.json.

v2 changes:
  - temporal deduplication for OCR-only mentions (10s window)
    prevents root_node=72, left_subtree=69 inflation from static board
  - cleaner source tracking
"""

import json
import re
from pathlib import Path
from collections import defaultdict


# ------------------------------------------------------------------
# concept lexicon
# ------------------------------------------------------------------

_CONCEPT_PATTERNS = {
    # --- tree traversal domain ---
    "tree traversal": [
        r"tree\s+traversal", r"traversal\s+technique",
    ],
    "pre-order traversal": [
        r"pre[\-\s]?order", r"preorder",
    ],
    "in-order traversal": [
        r"in[\-\s]?order", r"inorder",
    ],
    "post-order traversal": [
        r"post[\-\s]?order", r"postorder",
    ],
    "binary tree": [
        r"binary\s+tree",
    ],
    "root node": [
        r"root\s+node", r"root\s+element", r"\broot\b",
    ],
    "leaf node": [
        r"leaf\s+node", r"leaf\b",
    ],
    "left subtree": [
        r"left\s+(?:subtree|child|node|element|side)",
    ],
    "right subtree": [
        r"right\s+(?:subtree|child|node|element|side)",
    ],
    "node": [
        r"\bnode\b", r"\bnodes\b",
    ],
    "tree": [
        r"\btree\b",
    ],
    "children": [
        r"\bchildren\b", r"\bchild\b",
    ],
    "dummy node": [
        r"dummy\b",
    ],
    "traversal technique": [
        r"technique\b", r"traversing\b",
    ],
    # --- BFS / DFS / graph domain ---
    "breadth first search": [
        r"\bbfs\b", r"breadth\s+first\s+search", r"breadth\s+first",
    ],
    "depth first search": [
        r"\bdfs\b", r"depth\s+first\s+search", r"depth\s+first",
    ],
    "graph traversal": [
        r"graph\s+travers", r"travers(?:e|ing|al)\s+(?:a\s+)?graph",
    ],
    "graph": [
        r"\bgraph\b", r"\bgraphs\b",
    ],
    "vertex": [
        r"\bvertex\b", r"\bvertices\b", r"\bvertice\b",
    ],
    "edge": [
        r"\bedge\b", r"\bedges\b",
    ],
    "queue": [
        r"\bqueue\b", r"\bFIFO\b",
    ],
    "stack": [
        r"\bstack\b", r"\bLIFO\b",
    ],
    "visited": [
        r"\bvisited\b", r"visit(?:ed)?\s+(?:array|list|set|node)",
    ],
    "adjacency list": [
        r"adjacen(?:cy|t)\s+(?:list|matrix)", r"adjacen(?:cy|t)\b",
    ],
    "connected component": [
        r"connected\s+component",
    ],
    "shortest path": [
        r"shortest\s+path", r"shortest\s+distance",
    ],
    "level order": [
        r"level\s+(?:order|by\s+level|wise)",
    ],
    # --- DBMS / keys domain ---
    "primary key": [
        r"primary\s+key",
    ],
    "candidate key": [
        r"candidate\s+key",
    ],
    "super key": [
        r"super\s+key",
    ],
    "foreign key": [
        r"foreign\s+key",
    ],
    "composite key": [
        r"composite\s+key",
    ],
    "alternate key": [
        r"alternate\s+key", r"alternative\s+key",
    ],
    "unique constraint": [
        r"\bunique\b",
    ],
    "not null": [
        r"not\s+null",
    ],
    "null": [
        r"\bnull\b",
    ],
    "attribute": [
        r"\battribute\b", r"\battributes\b", r"\bcolumn\b", r"\bcolumns\b",
    ],
    "tuple": [
        r"\btuple\b", r"\btuples\b", r"\brow\b(?!\s+level)",
    ],
    "relation": [
        r"\brelation\b", r"\btable\b(?!\s+of\s+contents)",
    ],
    "database": [
        r"\bdatabase\b", r"\bdbms\b", r"\brdbms\b",
    ],
    "normalization": [
        r"\bnormali[sz]ation\b", r"\bnormal\s+form\b",
    ],
    "functional dependency": [
        r"functional\s+depend", r"\bfd\b",
    ],
    "schema": [
        r"\bschema\b",
    ],
    "entity": [
        r"\bentity\b", r"\bentities\b",
    ],
    "index": [
        r"\bindex\b(?!\.)", r"\bindexing\b",
    ],
    "sql": [
        r"\bsql\b", r"\bsequel\b",
    ],
    "constraint": [
        r"\bconstraint\b", r"\bconstraints\b",
    ],
    # --- sorting / searching domain ---
    "sorting": [
        r"\bsort(?:ing)?\b",
    ],
    "searching": [
        r"\bsearch(?:ing)?\b",
    ],
    "binary search": [
        r"binary\s+search",
    ],
    "linear search": [
        r"linear\s+search",
    ],
    "bubble sort": [
        r"bubble\s+sort",
    ],
    "merge sort": [
        r"merge\s+sort",
    ],
    "quick sort": [
        r"quick\s+sort", r"quicksort",
    ],
    "insertion sort": [
        r"insertion\s+sort",
    ],
    "selection sort": [
        r"selection\s+sort",
    ],
    "time complexity": [
        r"time\s+complex", r"\bbig[\s\-]?o\b", r"O\s*\(",
    ],
    "space complexity": [
        r"space\s+complex",
    ],
    # --- general CS ---
    "recursion": [
        r"\brecurs(?:ion|ive)\b",
    ],
    "array": [
        r"\barray\b", r"\barrays\b",
    ],
    "linked list": [
        r"linked\s+list",
    ],
    "pointer": [
        r"\bpointer\b", r"\bpointers\b",
    ],
    "hash table": [
        r"hash\s+(?:table|map|function)", r"\bhashing\b",
    ],
    "algorithm": [
        r"\balgorithm\b", r"\balgorithms\b",
    ],
    "data structure": [
        r"data\s+structure",
    ],
}

# OCR keyword -> concept mapping (for cross-modal enrichment)
_OCR_KEYWORD_CONCEPTS = {
    # tree domain
    "root": "root node",
    "left": "left subtree",
    "right": "right subtree",
    "preorder": "pre-order traversal",
    "inorder": "in-order traversal",
    "post": "post-order traversal",
    "postorder": "post-order traversal",
    "node": "node",
    # BFS/DFS domain
    "bfs": "breadth first search",
    "dfs": "depth first search",
    "queue": "queue",
    "stack": "stack",
    "visited": "visited",
    "graph": "graph",
    "vertex": "vertex",
    "edge": "edge",
    "adjacency": "adjacency list",
    # DBMS domain
    "primary": "primary key",
    "primary key": "primary key",
    "candidate": "candidate key",
    "candidate key": "candidate key",
    "super key": "super key",
    "foreign": "foreign key",
    "foreign key": "foreign key",
    "unique": "unique constraint",
    "null": "null",
    "not null": "not null",
    "attribute": "attribute",
    "tuple": "tuple",
    "table": "relation",
    "relation": "relation",
    "schema": "schema",
    "sql": "sql",
    "normalization": "normalization",
    "index": "index",
    "constraint": "constraint",
}

# node labels found in examples (letters for tree, also support numeric vertex labels)
_EXAMPLE_NODE_LABELS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# temporal dedup window (seconds) — OCR-only mentions within this window are merged
_OCR_DEDUP_WINDOW = 10.0


# ------------------------------------------------------------------
# extraction
# ------------------------------------------------------------------

def extract_concepts_from_text(text: str) -> set:
    """find all matching concepts in a text string."""
    found = set()
    text_lower = text.lower()
    for concept, patterns in _CONCEPT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                found.add(concept)
                break
    return found


def extract_concepts_from_ocr(ocr_keywords: list) -> set:
    """find concepts from corrected OCR keywords."""
    found = set()
    for kw in ocr_keywords:
        key = kw.lower().strip()
        if key in _OCR_KEYWORD_CONCEPTS:
            found.add(_OCR_KEYWORD_CONCEPTS[key])
        # also try multi-word matches for compound OCR text
        for ocr_key, concept in _OCR_KEYWORD_CONCEPTS.items():
            if ' ' in ocr_key and ocr_key in key:
                found.add(concept)
    return found


def extract_node_labels(text: str, ocr_keywords: list) -> set:
    """find tree node labels mentioned by the teacher."""
    labels = set()
    for match in re.finditer(r'\b([A-Z])\b', text):
        if match.group(1) in _EXAMPLE_NODE_LABELS:
            labels.add(match.group(1))
    for kw in ocr_keywords:
        upper = kw.upper()
        if len(upper) >= 2 and all(c in _EXAMPLE_NODE_LABELS for c in upper):
            labels.update(upper)
    return labels


def _get_segment_fields(seg: dict) -> tuple:
    """extract (spoken_text, ocr_keywords) from either old or new segment format.

    old format: {"spoken_text": str, "ocr_keywords": list, ...}
    new format: {"text": str, "source": "asr"|"ocr", ...}
    """
    if "spoken_text" in seg:
        # old format — has both spoken text and OCR in one segment
        return seg["spoken_text"], seg.get("ocr_keywords", [])
    else:
        # new format — each segment is either ASR or OCR
        text = seg.get("text", "")
        source = seg.get("source", "asr")
        if source == "ocr":
            # OCR segment: use text for concept matching, extract words as keywords
            ocr_words = [w.strip() for w in re.split(r'[\s,;|]+', text) if len(w.strip()) >= 2]
            return text, ocr_words
        else:
            # ASR segment: spoken text, no OCR keywords
            return text, []


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------

def run(video_id: str, data_root: str = "data") -> dict:
    out_dir = Path(data_root) / video_id
    normalized_path = out_dir / "normalized_segments.json"
    concepts_path = out_dir / "concepts.json"

    if concepts_path.exists():
        print(f"[m4] concepts already exists, loading: {concepts_path}")
        with open(concepts_path) as f:
            return json.load(f)

    with open(normalized_path) as f:
        normalized = json.load(f)

    print(f"[m4] extracting concepts from {len(normalized)} segments")

    concept_mentions = defaultdict(list)
    node_label_mentions = defaultdict(list)
    last_ocr_only = {}  # concept -> last timestamp of OCR-only mention (for dedup)

    for seg in normalized:
        start, end = seg["start"], seg["end"]
        spoken, ocr_kws = _get_segment_fields(seg)

        # concepts from spoken text (always counted)
        spoken_concepts = extract_concepts_from_text(spoken)
        for c in spoken_concepts:
            concept_mentions[c].append({"start": start, "end": end, "source": "asr"})

        # concepts from OCR with temporal deduplication
        ocr_concepts = extract_concepts_from_ocr(ocr_kws)
        for c in ocr_concepts:
            if c in spoken_concepts:
                # both sources agree — upgrade last ASR mention to multimodal
                concept_mentions[c][-1]["source"] = "asr+ocr"
            else:
                # OCR-only: only count if >_OCR_DEDUP_WINDOW since last OCR-only mention
                last_t = last_ocr_only.get(c, -999)
                if start - last_t > _OCR_DEDUP_WINDOW:
                    concept_mentions[c].append({"start": start, "end": end, "source": "ocr"})
                    last_ocr_only[c] = start

        # node labels
        labels = extract_node_labels(spoken, ocr_kws)
        for label in labels:
            node_label_mentions[label].append({"start": start, "end": end})

    # build output
    concepts = []
    for concept, mentions in sorted(concept_mentions.items()):
        first = min(m["start"] for m in mentions)
        last = max(m["end"] for m in mentions)
        sources = sorted(set(m["source"] for m in mentions))
        concepts.append({
            "name": concept,
            "mention_count": len(mentions),
            "first_mention": round(first, 1),
            "last_mention": round(last, 1),
            "sources": sources,
            "timestamps": [{"start": round(m["start"], 1), "end": round(m["end"], 1)} for m in mentions],
        })

    concepts.sort(key=lambda c: c["first_mention"])

    example_tree = {
        "description": "binary tree example used in the lecture",
        "node_labels": sorted(node_label_mentions.keys()),
        "node_mention_counts": {
            label: len(mentions) for label, mentions in sorted(node_label_mentions.items())
        },
    }

    result = {
        "video_id": video_id,
        "total_concepts": len(concepts),
        "concepts": concepts,
        "example_tree": example_tree,
    }

    with open(concepts_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[m4] extracted {len(concepts)} concepts")
    for c in concepts:
        src = ",".join(c["sources"])
        print(f"  {c['first_mention']:>6.1f}s  {c['name']:<25s} ({c['mention_count']}x, {src})")
    print(f"[m4] example tree nodes: {sorted(node_label_mentions.keys())}")
    print(f"[m4] -> {concepts_path}")

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    run(args.video_id, args.data_root)
