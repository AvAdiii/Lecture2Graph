# Changelog

All notable changes to Lecture2Graph.

## Unreleased
- Renamed the project to Lecture2Graph and reorganized the repository layout.
- Consolidated docs under `docs/` and moved outputs under `outputs/`.

## Regex pipeline

### Modules
- M1: Video download + audio/frame extraction
- M2: Whisper ASR (`task="transcribe"`) + Tesseract OCR
- M3: ASR-seeded vocabulary + RapidFuzz OCR correction
- M4: 26 concept patterns (trees + BFS/DFS)
- M5: 38 domain rules + causal patterns + temporal edges
- M6: Pyvis graph.html + markdown report

### Issues Discovered
- Whisper transcribe mode renders Hindi CS terms in Devanagari
- English-only regex cannot match Devanagari text
- Whisper small fails catastrophically on Telugu
- No hallucination filtering for single-word nonsense

### Root Cause Analysis: Hindi/Telugu Extraction Failure

Three videos produced near-empty results (0–1 concepts) despite having rich
CS content:

| Video | Language | Old Result | Root Cause |
|-------|----------|------------|------------|
| Tp37HXfekNo | Hindi | 0 concepts | ALL CS terms transcribed in Devanagari |
| azXr6nTaD9M | Hindi | 1 concept | Only "stack" appeared in English (2×) |
| eXWl-Uor75o | Telugu | 1 concept | Whisper `small` catastrophically fails on Telugu |

**Hindi videos**: Whisper with `task="transcribe"` renders Hindi-spoken English
CS terms in Devanagari script. For example:
- "recursion" → "रिकर्जन"
- "primary key" → "प्रामरी की"
- "stack" → "स्ताक"
- "factorial" → "खेक्टोरिल"
- "function" → "फुंच्छन"

The downstream concept extraction (M4) uses English regex patterns like
`\brecursion\b`, which can never match Devanagari text. Result: 0 concepts
for a video about DBMS Primary Keys.

**Telugu video**: Whisper `small` produces garbled output + hallucinations
("LGBT", "Bowser", body part descriptions). Only 39 segments (vs 120+ for
Hindi), mostly nonsensical.

### Changes Made

#### M2: ASR Extraction - Translate Mode (CRITICAL FIX)
- **Before**: `model.transcribe(audio, task="transcribe")` - keeps native script
- **After**: Detects language first, then uses `task="translate"` for non-English
- Saves both `transcript_original.json` (native script) and `transcript.json` (English)
- Saves `detected_language.json` with language code + confidence
- Cache-aware: checks for `detected_language.json` to distinguish v1/v2 transcripts
- English videos unchanged (translate ≈ transcribe for English)

#### M3: Normalization - Enhanced Hallucination Filter
- Added 40+ known hallucination words (body parts, gaming, politics)
- Added pattern-based detection (repeated phrases, filler, punctuation-only)
- Added non-ASCII ratio check (translated text should be mostly ASCII)
- Vocabulary builder now captures English terms from translated ASR output

### Results
- XRcC7bAtL3c (Tree Traversal): 14 concepts, 51 edges ✓
- N2P7w22tN9c (BFS/DFS): 12 concepts, 41 edges ✓
- Tp37HXfekNo (DBMS, Hindi): 10 concepts, 19 edges ✓
- azXr6nTaD9M (Recursion, Hindi): 7 concepts, 16 edges ✓
- eXWl-Uor75o (Telugu): 8 concepts, 21 edges ✓


## LLM pipeline

### Motivation

The regex pipeline relied on ~100 handcrafted regex patterns and ~80 domain rules to
extract concepts and prerequisites. While effective for known CS topics (trees,
graphs, DBMS), this approach:
- Cannot discover novel/unexpected concepts outside the pattern list
- Produces many low-confidence temporal edges (57% of all edges)
- Requires manual rule authoring for each new domain
- Cannot reason about *why* A is a prerequisite of B

The LLM pipeline replaces M3–M5 with LLM calls, sending the transcript to a language
model that can semantically understand CS concepts and reason about prerequisite
relationships.

### LLM Backend Journey

**Attempt 1 - Gemini 2.0 Flash (Google):**
- Used `google-generativeai` SDK with API key
- Hit free-tier rate limits immediately: `RESOURCE_EXHAUSTED` -
  "Quota exceeded for generativelanguage.googleapis.com/generate_content_free_tier_requests,
  limit: 0, model: gemini-2.0-flash"
- The free tier had a per-minute and per-day quota that was exhausted after the
  initial API test calls, leaving 0 remaining requests
- **Abandoned** after failing all 5 retry attempts with exponential backoff

**Attempt 2 - Groq (llama-3.3-70b-versatile):**
- Switched to Groq API which provides fast inference on open-weight LLMs
- Used `groq` Python SDK with `response_format={"type": "json_object"}`
- Successfully processed 3 of 5 videos before hitting rate limits

### Changes Made

#### New: `lecture2graph/llm_pipeline/` directory
- `m3_normalize.py` - Simplified normalization (no fuzzy correction, no heavy
  hallucination filter). LLMs handle noisy/misspelled text well, so only basic
  garbage removal (empty, punctuation-only, repeated phrases) is needed.
  Also handles both old-format (`spoken_text`/`visual_text`) and new-format
  (`text`/`source`) aligned segments.
- `m4_concepts.py` - Sends transcript to Groq in chunks of 80 segments,
  asks the LLM to extract CS concepts with names, mention counts, timestamps,
  and sources. Merges chunk results via a second LLM call. All prompts enforce
  JSON-only output with structured schema.
- `m5_prereqs.py` - Sends concept list + transcript summary to Groq, asks it
  to determine genuine prerequisite relationships. Classifies edges as
  `domain_rule` or `causal`. Includes DAG verification (Kahn's algorithm)
  to detect and break cycles if the LLM produces any.
- `pipeline.py` - Orchestrator that reuses M1/M2 from the regex pipeline, runs new
  M3–M5, and reuses M6 from the regex pipeline.
- `run_llm_batch.py` - Batch runner that symlinks M1/M2 artifacts from
  `outputs/regex/` into `outputs/llm/` to avoid re-downloading videos.

#### Reused from regex pipeline (unchanged)
- `m1_ingest.py` - Video download, audio extraction, keyframe extraction
- `m2_extract.py` - Whisper ASR (translate mode) + Tesseract OCR
- `m6_visualize.py` - vis.js hierarchical DAG HTML + markdown report

### Results: 3 of 5 Videos Completed

| Video | Language | LLM Concepts | LLM Edges | Status |
|-------|----------|-------------|----------|--------|
| XRcC7bAtL3c | English | 7 | 6 | Complete |
| N2P7w22tN9c | English | 10 | 9 | Complete |
| azXr6nTaD9M | Hindi | 9 | 8 | Complete |
| Tp37HXfekNo | Hindi | - | - | Rate limited |
| eXWl-Uor75o | Telugu | - | - | Rate limited |

### Comparison: Regex pipeline vs LLM pipeline

#### Video: XRcC7bAtL3c - Tree Traversal (English)

| Metric | Regex | LLM |
|--------|-----------|-----------|
| Concepts | 14 | 7 |
| Edges | 51 | 6 |
| Edge types | temporal(20), prerequisite(27), refines(3), part_of(1) | domain_rule(6) |

**Regex only** (7): tree, left_subtree, right_subtree, node, traversal_technique, children, dummy_node <br>
**LLM only** (0): all LLM concepts had regex counterparts<br>
**Both** (7): tree_traversal, pre_order, in_order, post_order, binary_tree, leaf_node, root_node<br>

*Analysis*: Regex captured more low-level structural components (subtrees, nodes)
while LLM focused on the core pedagogical concepts. LLM produced far fewer
edges (6 vs 51) but all are `domain_rule` type with explanations - no temporal
padding.

#### Video: N2P7w22tN9c - BFS/DFS Graph Traversal (English)

| Metric | Regex | LLM |
|--------|-----------|-----------|
| Concepts | 12 | 10 |
| Edges | 41 | 9 |
| Edge types | temporal(28), prerequisite(10), refines(3) | domain_rule(6), causal(3) |

**Regex only** (5): graph, tree, visited, pre_order_traversal, traversal_technique
**LLM only** (3): time_complexity, web_crawler, minimum_cost_spanning_tree
**Both** (7): graph_traversal, bfs, dfs, stack, tree_traversal, vertex, edge

*Analysis*: LLM discovered application-level concepts (web_crawler as BFS
application, minimum_cost_spanning_tree as DFS application, time_complexity O(V+E))
that regex completely missed. Regex captured the generic "graph" and "tree"
structural terms. LLM edges include 3 `causal` edges from lecturer's explicit
prerequisite language.

#### Video: azXr6nTaD9M - Recursion & Stack (Hindi)

| Metric | Regex | LLM |
|--------|-----------|-----------|
| Concepts | 7 | 9 |
| Edges | 16 | 8 |
| Edge types | temporal(14), refines(2) | domain_rule(6), causal(2) |

**Regex only** (2): data_structure, pointer
**LLM only** (4): activation_record, call_by_value, instruction_pointer, factorial
**Both** (5): recursion, stack, time_complexity, space_complexity, tree

*Analysis*: **LLM's strongest showing.** Found 4 unique concepts that are
pedagogically critical to understanding recursion (activation_record,
call_by_value, instruction_pointer, factorial) but don't match standard regex
patterns. This is the case where LLM understanding beats pattern matching.

#### Aggregate Comparison

| Metric | Regex pipeline | LLM pipeline |
|--------|-------------------|------------------|
| Total concepts (3 videos) | 33 | 26 |
| Total edges (3 videos) | 108 | 23 |
| Avg concepts/video | 11.0 | 8.7 |
| Avg edges/video | 36.0 | 7.7 |
| Concepts unique to approach | 14 | 7 |
| Concepts shared | 19 | 19 |
| Temporal/low-confidence edges | 62 (57%) | 0 (0%) |
| Domain/causal edges | 0 (0%) | 23 (100%) |

### Key Findings

1. The regex pipeline extracts more concepts (higher
   recall) but includes structural noise (left_subtree, dummy_node). The LLM pipeline
   is more precise, focusing on pedagogically meaningful concepts.

2. The LLM pipeline produces 4.7× fewer edges but every edge has a
   semantic justification. The regex pipeline's edges are 57% temporal ("mentioned first"),
   which are low-confidence heuristics. The LLM pipeline's edges are 100% domain_rule
   or causal.

3. activation_record, web_crawler,
   factorial, minimum_cost_spanning_tree - concepts that require understanding
   the lecture content, not just matching keywords.

4. left_subtree, right_subtree, node,
   children - fine-grained structural concepts that LLMs tend to omit in favor
   of higher-level abstractions.
---
