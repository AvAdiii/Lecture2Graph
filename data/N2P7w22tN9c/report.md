# Concept DAG Report — N2P7w22tN9c

**Source language:** English
**Concepts:** 12 | **Edges:** 41 | **Topo order:** 12/12

## Topological Order

1. Edge
2. Vertex
3. Graph
4. Graph Traversal
5. Tree
6. Tree Traversal
7. Visited
8. Stack
9. Depth First Search
10. Traversal Technique
11. Pre-Order Traversal
12. Breadth First Search

## Concepts

### Graph
- Mentions: 12
- First seen: 00:02
- Sources: asr, asr+ocr, ocr

### Graph Traversal
- Mentions: 3
- First seen: 00:36
- Sources: asr

### Tree
- Mentions: 4
- First seen: 00:47
- Sources: asr

### Tree Traversal
- Mentions: 1
- First seen: 00:47
- Sources: asr

### Vertex
- Mentions: 5
- First seen: 01:06
- Sources: asr

### Edge
- Mentions: 3
- First seen: 01:14
- Sources: asr

### Depth First Search
- Mentions: 3
- First seen: 02:54
- Sources: asr

### Visited
- Mentions: 1
- First seen: 05:03
- Sources: asr

### Stack
- Mentions: 3
- First seen: 07:04
- Sources: asr

### Pre-Order Traversal
- Mentions: 1
- First seen: 08:29
- Sources: ocr

### Traversal Technique
- Mentions: 1
- First seen: 10:38
- Sources: asr

### Breadth First Search
- Mentions: 1
- First seen: 11:07
- Sources: asr

## Prerequisite Edges

| From | To | Type | Rule |
|------|-----|------|------|
| tree | tree traversal | is_prerequisite_for |  |
| tree traversal | pre-order traversal | refines |  |
| traversal technique | pre-order traversal | is_prerequisite_for |  |
| graph | graph traversal | is_prerequisite_for |  |
| vertex | graph | is_prerequisite_for |  |
| edge | graph | is_prerequisite_for |  |
| graph traversal | breadth first search | refines |  |
| graph traversal | depth first search | refines |  |
| graph | breadth first search | is_prerequisite_for |  |
| graph | depth first search | is_prerequisite_for |  |
| stack | depth first search | is_prerequisite_for |  |
| visited | breadth first search | is_prerequisite_for |  |
| visited | depth first search | is_prerequisite_for |  |
| graph | tree | temporal_precedence |  |
| graph | tree traversal | temporal_precedence |  |
| graph | visited | temporal_precedence |  |
| graph traversal | visited | temporal_precedence |  |
| graph traversal | stack | temporal_precedence |  |
| graph traversal | pre-order traversal | temporal_precedence |  |
| tree | depth first search | temporal_precedence |  |
| tree | visited | temporal_precedence |  |
| tree | stack | temporal_precedence |  |
| tree traversal | depth first search | temporal_precedence |  |
| tree traversal | visited | temporal_precedence |  |
| tree traversal | stack | temporal_precedence |  |
| vertex | visited | temporal_precedence |  |
| vertex | stack | temporal_precedence |  |
| vertex | pre-order traversal | temporal_precedence |  |
| edge | visited | temporal_precedence |  |
| edge | stack | temporal_precedence |  |
| edge | pre-order traversal | temporal_precedence |  |
| depth first search | pre-order traversal | temporal_precedence |  |
| depth first search | traversal technique | temporal_precedence |  |
| depth first search | breadth first search | temporal_precedence |  |
| visited | stack | temporal_precedence |  |
| visited | pre-order traversal | temporal_precedence |  |
| visited | traversal technique | temporal_precedence |  |
| stack | pre-order traversal | temporal_precedence |  |
| stack | traversal technique | temporal_precedence |  |
| stack | breadth first search | temporal_precedence |  |
| pre-order traversal | breadth first search | temporal_precedence |  |
