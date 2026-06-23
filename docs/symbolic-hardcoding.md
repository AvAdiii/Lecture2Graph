# Hardcoded Elements Inventory

This document lists all hardcoded / domain-specific elements in Approach 1 which is the rule-based pipeline,
organized by module and mentioned which video the different elements correspond to.

These hardcoded elements are the main limitation of the rule-based approach.
Each new video domain may require extending these lists. A future approach using LLMs or
unsupervised NLP (e.g., YAKE keyword extraction) would eliminate most of these.

---

## Module 3: `m3_normalize.py`

### `_SEED_VOCAB` — Universal CS seed vocabulary (67 terms)
These are **domain-generic** CS terms always included in the fuzzy-matching vocabulary,
regardless of what the ASR transcript contains. They are NOT video-specific.

**Added for Video 1** (`XRcC7bAtL3c` — Tree Traversals):
```
tree, node, root, leaf, left, right, child, children, parent, binary,
graph, vertex, edge, traversal, order, preorder, inorder, postorder,
pre-order, in-order, post-order, algorithm, recursive, stack, queue,
array, list, element, pointer, data, structure, technique, dummy,
depth, height, subtree, branch, level, search, sort, insert, delete
```
(42 terms)

**Added for Video 2** (`N2P7w22tN9c` — BFS/DFS):
```
breadth, first, visited, adjacency, matrix, connected, component,
shortest, path, directed, undirected, weighted, unweighted, cycle,
acyclic, neighbor, degree, source, destination, explore, frontier,
enqueue, dequeue, push, pop
```
(25 terms)

### `_OVERRIDE_CORRECTIONS` — Extreme OCR garbling overrides (3 entries)
These handle cases where the edit distance is too large for fuzzy matching to bridge.
All from Video 1's handwritten board:

| OCR garble     | Correction | Video |
|----------------|------------|-------|
| `phqohjhl`     | `preorder` | Video 1 (`XRcC7bAtL3c`) |
| `npqohjjul`    | `preorder` | Video 1 (`XRcC7bAtL3c`) |
| `pnqohjul`     | `preorder` | Video 1 (`XRcC7bAtL3c`) |

### Constants
| Name | Value | Purpose |
|------|-------|---------|
| `_MIN_FUZZY_SCORE` | 65 | Minimum rapidfuzz score to accept a correction |
| `_MIN_TOKEN_LEN` | 3 | Skip very short tokens for fuzzy matching |

---

## Module 4: Concept Extraction (`m4_concepts.py`)

### `_CONCEPT_PATTERNS` — Concept regex lexicon (26 concepts)

**Added for Video 1** (`XRcC7bAtL3c` — Tree Traversals, 14 concepts):
| Concept | Regex patterns |
|---------|---------------|
| tree traversal | `tree\s+traversal`, `traversal\s+technique` |
| pre-order traversal | `pre[\-\s]?order`, `preorder` |
| in-order traversal | `in[\-\s]?order`, `inorder` |
| post-order traversal | `post[\-\s]?order`, `postorder` |
| binary tree | `binary\s+tree` |
| root node | `root\s+node`, `root\s+element`, `\broot\b` |
| leaf node | `leaf\s+node`, `leaf\b` |
| left subtree | `left\s+(?:subtree\|child\|node\|element\|side)` |
| right subtree | `right\s+(?:subtree\|child\|node\|element\|side)` |
| node | `\bnode\b`, `\bnodes\b` |
| tree | `\btree\b` |
| children | `\bchildren\b`, `\bchild\b` |
| dummy node | `dummy\b` |
| traversal technique | `technique\b`, `traversing\b` |

**Added for Video 2** (`N2P7w22tN9c` — BFS/DFS, 12 concepts):
| Concept | Regex patterns |
|---------|---------------|
| breadth first search | `\bbfs\b`, `breadth\s+first\s+search`, `breadth\s+first` |
| depth first search | `\bdfs\b`, `depth\s+first\s+search`, `depth\s+first` |
| graph traversal | `graph\s+travers`, `travers(?:e\|ing\|al)\s+(?:a\s+)?graph` |
| graph | `\bgraph\b`, `\bgraphs\b` |
| vertex | `\bvertex\b`, `\bvertices\b`, `\bvertice\b` |
| edge | `\bedge\b`, `\bedges\b` |
| queue | `\bqueue\b`, `\bFIFO\b` |
| stack | `\bstack\b`, `\bLIFO\b` |
| visited | `\bvisited\b`, `visit(?:ed)?\s+(?:array\|list\|set\|node)` |
| adjacency list | `adjacen(?:cy\|t)\s+(?:list\|matrix)`, `adjacen(?:cy\|t)\b` |
| connected component | `connected\s+component` |
| shortest path | `shortest\s+path`, `shortest\s+distance` |
| level order | `level\s+(?:order\|by\s+level\|wise)` |

### `_OCR_KEYWORD_CONCEPTS` — OCR keyword → concept mapping (18 entries)

**Added for Video 1** (8 entries):
| OCR keyword | Maps to concept |
|-------------|----------------|
| `root` | root node |
| `left` | left subtree |
| `right` | right subtree |
| `preorder` | pre-order traversal |
| `inorder` | in-order traversal |
| `post` | post-order traversal |
| `postorder` | post-order traversal |
| `node` | node |

**Added for Video 2** (10 entries):
| OCR keyword | Maps to concept |
|-------------|----------------|
| `bfs` | breadth first search |
| `dfs` | depth first search |
| `queue` | queue |
| `stack` | stack |
| `visited` | visited |
| `graph` | graph |
| `vertex` | vertex |
| `edge` | edge |
| `adjacency` | adjacency list |

### Constants
| Name | Value | Purpose |
|------|-------|---------|
| `_OCR_DEDUP_WINDOW` | 10.0s | Temporal dedup window for OCR-only mentions |

---

## Module 5: Prerequisite Mapping (`m5_prereqs.py`)

### `_DOMAIN_RULES` — Prerequisite rules (38 rules)

**Added for Video 1** (`XRcC7bAtL3c` — Tree Traversals, 21 rules):
| Source | Target | Type | Confidence |
|--------|--------|------|------------|
| tree | binary tree | is_prerequisite_for | 0.9 |
| tree | tree traversal | is_prerequisite_for | 0.9 |
| binary tree | tree traversal | is_prerequisite_for | 0.9 |
| node | root node | is_prerequisite_for | 0.8 |
| node | leaf node | is_prerequisite_for | 0.8 |
| root node | tree traversal | is_prerequisite_for | 0.8 |
| children | left subtree | is_prerequisite_for | 0.7 |
| children | right subtree | is_prerequisite_for | 0.7 |
| tree traversal | pre-order traversal | refines | 0.9 |
| tree traversal | in-order traversal | refines | 0.9 |
| tree traversal | post-order traversal | refines | 0.9 |
| traversal technique | pre-order traversal | is_prerequisite_for | 0.7 |
| traversal technique | in-order traversal | is_prerequisite_for | 0.7 |
| traversal technique | post-order traversal | is_prerequisite_for | 0.7 |
| left subtree | pre-order traversal | is_prerequisite_for | 0.7 |
| right subtree | pre-order traversal | is_prerequisite_for | 0.7 |
| left subtree | in-order traversal | is_prerequisite_for | 0.7 |
| right subtree | in-order traversal | is_prerequisite_for | 0.7 |
| left subtree | post-order traversal | is_prerequisite_for | 0.7 |
| right subtree | post-order traversal | is_prerequisite_for | 0.7 |
| dummy node | traversal technique | is_part_of | 0.6 |

**Added for Video 2** (`N2P7w22tN9c` — BFS/DFS, 17 rules):
| Source | Target | Type | Confidence |
|--------|--------|------|------------|
| graph | graph traversal | is_prerequisite_for | 0.9 |
| vertex | graph | is_prerequisite_for | 0.7 |
| edge | graph | is_prerequisite_for | 0.7 |
| graph traversal | breadth first search | refines | 0.9 |
| graph traversal | depth first search | refines | 0.9 |
| graph | breadth first search | is_prerequisite_for | 0.8 |
| graph | depth first search | is_prerequisite_for | 0.8 |
| queue | breadth first search | is_prerequisite_for | 0.8 |
| stack | depth first search | is_prerequisite_for | 0.8 |
| visited | breadth first search | is_prerequisite_for | 0.7 |
| visited | depth first search | is_prerequisite_for | 0.7 |
| adjacency list | breadth first search | is_prerequisite_for | 0.6 |
| adjacency list | depth first search | is_prerequisite_for | 0.6 |
| node | vertex | is_prerequisite_for | 0.5 |
| breadth first search | shortest path | is_prerequisite_for | 0.7 |
| connected component | graph traversal | is_prerequisite_for | 0.6 |

### `_CONCEPT_FRAGMENTS` — Text fragment → concept mapping (30 entries)

Used inside causal anchor text to find mentioned concepts.

**Added for Video 1** (18 entries):
| Fragment | Maps to concept |
|----------|----------------|
| `pre-order` | pre-order traversal |
| `preorder` | pre-order traversal |
| `pre order` | pre-order traversal |
| `in-order` | in-order traversal |
| `inorder` | in-order traversal |
| `in order` | in-order traversal |
| `post-order` | post-order traversal |
| `postorder` | post-order traversal |
| `post order` | post-order traversal |
| `root node` | root node |
| `root` | root node |
| `left` | left subtree |
| `right` | right subtree |
| `tree` | tree |
| `node` | node |
| `vertex` | vertex |
| `leaf` | leaf node |
| `binary tree` | binary tree |
| `children` / `child` | children |

**Added for Video 2** (12 entries):
| Fragment | Maps to concept |
|----------|----------------|
| `breadth first search` | breadth first search |
| `breadth first` | breadth first search |
| `bfs` | breadth first search |
| `depth first search` | depth first search |
| `depth first` | depth first search |
| `dfs` | depth first search |
| `graph traversal` | graph traversal |
| `graph` | graph |
| `queue` | queue |
| `stack` | stack |
| `visited` | visited |
| `adjacency` | adjacency list |
| `edge` | edge |
| `shortest path` | shortest path |

### `_CAUSAL_PATTERNS` — Regex patterns for causal language (4 patterns, generic)
These are **NOT video-specific** — they detect general causal/sequential language:
1. `before we do X, you need to know Y` → prerequisite_explicit
2. `first we do X, then Y` → temporal_sequence
3. `remember/recall X from before` → back_reference
4. `X means Y` → definition

### Constants
| Name | Value | Purpose |
|------|-------|---------|
| `_MAX_TEMPORAL_OUT` | 3 | Max temporal out-edges per concept |
| `_TEMPORAL_GAP_MIN` | 30s | Minimum temporal gap for temporal edge |

---

## Summary: Per-Video Additions

### Video 1: `XRcC7bAtL3c` — Tree Traversal Techniques
| Module | What was added | Count |
|--------|---------------|-------|
| M3 | `_SEED_VOCAB` (tree/data structure terms) | 42 terms |
| M3 | `_OVERRIDE_CORRECTIONS` (extreme OCR garbling) | 3 entries |
| M4 | `_CONCEPT_PATTERNS` (tree traversal concepts) | 14 concepts |
| M4 | `_OCR_KEYWORD_CONCEPTS` (tree OCR keywords) | 8 entries |
| M5 | `_DOMAIN_RULES` (tree traversal prerequisites) | 21 rules |
| M5 | `_CONCEPT_FRAGMENTS` (tree text fragments) | 18 entries |

### Video 2: `N2P7w22tN9c` — BFS/DFS Graph Traversal
| Module | What was added | Count |
|--------|---------------|-------|
| M3 | `_SEED_VOCAB` (graph/BFS/DFS terms) | 25 terms |
| M4 | `_CONCEPT_PATTERNS` (graph/BFS/DFS concepts) | 12 concepts |
| M4 | `_OCR_KEYWORD_CONCEPTS` (graph OCR keywords) | 10 entries |
| M5 | `_DOMAIN_RULES` (graph/BFS/DFS prerequisites) | 17 rules |
| M5 | `_CONCEPT_FRAGMENTS` (graph text fragments) | 12 entries |

### Videos 3-5: `Tp37HXfekNo`, `azXr6nTaD9M`, `eXWl-Uor75o`
**No new hardcoded elements added.** These videos are run with the existing rule set to test generalizability. Results may be suboptimal for topics outside the tree traversal / BFS/DFS domain.

---

## What would eliminate these hardcoded elements?

1. **LLM-in-the-loop (Option A):** Use an LLM to extract concepts and prerequisite relationships directly from transcript text. Eliminates M4 patterns and M5 domain rules entirely.
2. **Unsupervised NLP (Option B):** Use YAKE or similar keyword extraction for M4, and co-occurrence / PMI analysis for M5 edges. No domain lexicon needed.
3. **Hybrid (Option C):** Use unsupervised extraction for initial concept/edge candidates, then LLM for refinement and confidence scoring.
