# Concept DAG Report — XRcC7bAtL3c

**Source language:** English
**Concepts:** 14 | **Edges:** 51 | **Topo order:** 14/14

## Topological Order

1. Tree
2. Node
3. Root Node
4. Children
5. Left Subtree
6. Right Subtree
7. Binary Tree
8. Dummy Node
9. Tree Traversal
10. Traversal Technique
11. In-Order Traversal
12. Post-Order Traversal
13. Pre-Order Traversal
14. Leaf Node

## Concepts

### Pre-Order Traversal
- Mentions: 13
- First seen: 00:00
- Sources: asr, asr+ocr, ocr

### Root Node
- Mentions: 34
- First seen: 00:00
- Sources: asr+ocr, ocr

### Tree
- Mentions: 12
- First seen: 00:03
- Sources: asr

### Tree Traversal
- Mentions: 2
- First seen: 00:03
- Sources: asr

### In-Order Traversal
- Mentions: 10
- First seen: 00:06
- Sources: asr

### Post-Order Traversal
- Mentions: 17
- First seen: 00:06
- Sources: asr, asr+ocr, ocr

### Left Subtree
- Mentions: 29
- First seen: 00:12
- Sources: asr, asr+ocr, ocr

### Node
- Mentions: 11
- First seen: 00:12
- Sources: asr, ocr

### Right Subtree
- Mentions: 13
- First seen: 00:22
- Sources: asr, asr+ocr, ocr

### Traversal Technique
- Mentions: 4
- First seen: 01:18
- Sources: asr

### Binary Tree
- Mentions: 2
- First seen: 01:39
- Sources: asr

### Children
- Mentions: 7
- First seen: 01:45
- Sources: asr

### Leaf Node
- Mentions: 2
- First seen: 01:54
- Sources: asr

### Dummy Node
- Mentions: 2
- First seen: 02:00
- Sources: asr

## Prerequisite Edges

| From | To | Type | Rule |
|------|-----|------|------|
| tree | binary tree | is_prerequisite_for |  |
| tree | tree traversal | is_prerequisite_for |  |
| binary tree | tree traversal | is_prerequisite_for |  |
| node | root node | is_prerequisite_for |  |
| node | leaf node | is_prerequisite_for |  |
| root node | tree traversal | is_prerequisite_for |  |
| children | left subtree | is_prerequisite_for |  |
| children | right subtree | is_prerequisite_for |  |
| tree traversal | pre-order traversal | refines |  |
| tree traversal | in-order traversal | refines |  |
| tree traversal | post-order traversal | refines |  |
| traversal technique | pre-order traversal | is_prerequisite_for |  |
| traversal technique | in-order traversal | is_prerequisite_for |  |
| traversal technique | post-order traversal | is_prerequisite_for |  |
| left subtree | pre-order traversal | is_prerequisite_for |  |
| right subtree | pre-order traversal | is_prerequisite_for |  |
| left subtree | in-order traversal | is_prerequisite_for |  |
| right subtree | in-order traversal | is_prerequisite_for |  |
| left subtree | post-order traversal | is_prerequisite_for |  |
| right subtree | post-order traversal | is_prerequisite_for |  |
| dummy node | traversal technique | is_part_of |  |
| root node | right subtree | is_prerequisite_for |  |
| root node | left subtree | is_prerequisite_for |  |
| node | right subtree | is_prerequisite_for |  |
| node | left subtree | is_prerequisite_for |  |
| root node | pre-order traversal | is_prerequisite_for |  |
| node | pre-order traversal | is_prerequisite_for |  |
| root node | in-order traversal | is_prerequisite_for |  |
| root node | post-order traversal | is_prerequisite_for |  |
| node | post-order traversal | is_prerequisite_for |  |
| tree | node | is_prerequisite_for |  |
| pre-order traversal | leaf node | temporal_precedence |  |
| root node | traversal technique | temporal_precedence |  |
| root node | binary tree | temporal_precedence |  |
| root node | children | temporal_precedence |  |
| tree | traversal technique | temporal_precedence |  |
| tree | children | temporal_precedence |  |
| tree | dummy node | temporal_precedence |  |
| tree traversal | traversal technique | temporal_precedence |  |
| tree traversal | leaf node | temporal_precedence |  |
| in-order traversal | leaf node | temporal_precedence |  |
| post-order traversal | leaf node | temporal_precedence |  |
| left subtree | traversal technique | temporal_precedence |  |
| left subtree | binary tree | temporal_precedence |  |
| left subtree | leaf node | temporal_precedence |  |
| node | traversal technique | temporal_precedence |  |
| node | binary tree | temporal_precedence |  |
| node | children | temporal_precedence |  |
| right subtree | binary tree | temporal_precedence |  |
| right subtree | leaf node | temporal_precedence |  |
| right subtree | dummy node | temporal_precedence |  |
