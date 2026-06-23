# Concept DAG Report — Tp37HXfekNo

**Source language:** Hindi
**Concepts:** 10 | **Edges:** 19 | **Topo order:** 10/10

## Topological Order

1. Database
2. Null
3. Unique Constraint
4. Not Null
5. Relation
6. Sql
7. Attribute
8. Candidate Key
9. Primary Key
10. Normalization

## Concepts

### Primary Key
- Mentions: 191
- First seen: 00:00
- Sources: asr, asr+ocr, ocr

### Database
- Mentions: 13
- First seen: 00:06
- Sources: asr

### Not Null
- Mentions: 123
- First seen: 00:06
- Sources: asr

### Null
- Mentions: 127
- First seen: 00:06
- Sources: asr, asr+ocr

### Unique Constraint
- Mentions: 108
- First seen: 00:06
- Sources: asr, asr+ocr

### Candidate Key
- Mentions: 6
- First seen: 00:23
- Sources: asr

### Normalization
- Mentions: 1
- First seen: 00:27
- Sources: asr

### Sql
- Mentions: 2
- First seen: 00:27
- Sources: asr

### Attribute
- Mentions: 10
- First seen: 01:13
- Sources: asr

### Relation
- Mentions: 2
- First seen: 01:13
- Sources: asr

## Prerequisite Edges

| From | To | Type | Rule |
|------|-----|------|------|
| database | relation | is_prerequisite_for |  |
| relation | attribute | is_prerequisite_for |  |
| attribute | candidate key | is_prerequisite_for |  |
| unique constraint | candidate key | is_prerequisite_for |  |
| not null | primary key | is_prerequisite_for |  |
| null | not null | is_prerequisite_for |  |
| candidate key | primary key | is_prerequisite_for |  |
| unique constraint | primary key | is_prerequisite_for |  |
| relation | normalization | is_prerequisite_for |  |
| primary key | normalization | is_prerequisite_for |  |
| database | sql | is_prerequisite_for |  |
| relation | sql | is_prerequisite_for |  |
| not null | attribute | temporal_precedence |  |
| not null | relation | temporal_precedence |  |
| null | attribute | temporal_precedence |  |
| null | relation | temporal_precedence |  |
| unique constraint | attribute | temporal_precedence |  |
| unique constraint | relation | temporal_precedence |  |
| sql | attribute | temporal_precedence |  |
