# Hardcoded Elements Inventory

This document lists all hardcoded / domain-specific elements in the regex pipeline,
organized by module and mentioned with which video prompted each addition.

---

## Module 3: m3_normalize.py

### `_SEED_VOCAB` - Universal CS seed vocabulary (67 terms)
These are **domain-generic** CS terms always included in the fuzzy-matching vocabulary,
regardless of what the ASR transcript contains. They are NOT video-specific.

**Examples**
```
tree, node, root, leaf, left, right, child, children, parent, binary,
graph, vertex, edge, traversal, order, preorder, inorder, postorder,
pre-order, in-order, post-order, algorithm, recursive, stack, queue,
array, list, element, pointer, data, structure, technique, dummy,
depth, height, subtree, branch, level, search, sort, insert, delete
```
(42 terms)

```
breadth, first, visited, adjacency, matrix, connected, component,
shortest, path, directed, undirected, weighted, unweighted, cycle,
acyclic, neighbor, degree, source, destination, explore, frontier,
enqueue, dequeue, push, pop
```
(25 terms), etc.

### `_OVERRIDE_CORRECTIONS` - Extreme OCR garbling overrides
These handle cases where the edit distance is too large for fuzzy matching to bridge.
These are few examples from Video 1 (`XRcC7bAtL3c`)'s handwritten board:

| OCR garble     | Correction |
|----------------|------------|
| `phqohjhl`     | `preorder` |
| `npqohjjul`    | `preorder` |
| `pnqohjul`     | `preorder` |

---

## Module 4: m4_concepts.py

### `_CONCEPT_PATTERNS` - Concept regex lexicon (26 concepts)

**Examples of CONCEPTS added**
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

### `_OCR_KEYWORD_CONCEPTS` - OCR keyword to concept mapping 

**Examples**
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

---

## Module 5: m5_prereqs.py

### `_DOMAIN_RULES` - Prerequisite rules

**Examples**
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

### `_CONCEPT_FRAGMENTS` - Text fragment to concept mapping

Used inside causal anchor text to find mentioned concepts.

**Examples**
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

### `_CAUSAL_PATTERNS` - Regex patterns for causal language
These are **NOT video-specific**. They detect general causal/sequential language:
1. `before we do X, you need to know Y` -> prerequisite_explicit
2. `first we do X, then Y` -> temporal_sequence
3. `remember/recall X from before` -> back_reference
4. `X means Y` → definition


---
