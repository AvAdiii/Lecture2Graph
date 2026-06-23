# Concept DAG Report — eXWl-Uor75o

**Source language:** Telugu
**Concepts:** 8 | **Edges:** 21 | **Topo order:** 8/8

## Topological Order

1. Left Subtree
2. Right Subtree
3. Sorting
4. Merge Sort
5. Traversal Technique
6. In-Order Traversal
7. Index
8. Bubble Sort

## Concepts

### Merge Sort
- Mentions: 24
- First seen: 00:08
- Sources: asr

### Sorting
- Mentions: 146
- First seen: 00:08
- Sources: asr

### Right Subtree
- Mentions: 18
- First seen: 00:21
- Sources: asr, ocr

### Left Subtree
- Mentions: 5
- First seen: 00:31
- Sources: ocr

### In-Order Traversal
- Mentions: 8
- First seen: 00:38
- Sources: asr

### Traversal Technique
- Mentions: 4
- First seen: 02:03
- Sources: asr

### Index
- Mentions: 4
- First seen: 03:51
- Sources: asr

### Bubble Sort
- Mentions: 1
- First seen: 10:16
- Sources: asr

## Prerequisite Edges

| From | To | Type | Rule |
|------|-----|------|------|
| traversal technique | in-order traversal | is_prerequisite_for |  |
| left subtree | in-order traversal | is_prerequisite_for |  |
| right subtree | in-order traversal | is_prerequisite_for |  |
| sorting | bubble sort | refines |  |
| sorting | merge sort | refines |  |
| merge sort | traversal technique | temporal_precedence |  |
| merge sort | index | temporal_precedence |  |
| merge sort | bubble sort | temporal_precedence |  |
| sorting | traversal technique | temporal_precedence |  |
| sorting | index | temporal_precedence |  |
| right subtree | traversal technique | temporal_precedence |  |
| right subtree | index | temporal_precedence |  |
| right subtree | bubble sort | temporal_precedence |  |
| left subtree | traversal technique | temporal_precedence |  |
| left subtree | index | temporal_precedence |  |
| left subtree | bubble sort | temporal_precedence |  |
| in-order traversal | index | temporal_precedence |  |
| in-order traversal | bubble sort | temporal_precedence |  |
| traversal technique | index | temporal_precedence |  |
| traversal technique | bubble sort | temporal_precedence |  |
| index | bubble sort | temporal_precedence |  |
