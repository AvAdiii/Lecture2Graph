# Lecture2Graph
Generate pedagogical concept prerequisite DAGs
from code-mixed (Hindi/Telugu + English) lecture videos using multimodal NLP.

## Quick Start

```bash
# activate the virtual environment
source venv/bin/activate  # or activate.fish for fish shell

# ─── Regex pipeline (pattern-based) ───

# interactive demo (recommended)
python scripts/demo.py

# or run directly on a video
python -m lecture2graph.regex_pipeline.pipeline "https://www.youtube.com/watch?v=VIDEO_ID"

# force re-run from a specific stage (e.g., to re-translate)
python -m lecture2graph.regex_pipeline.pipeline "https://www.youtube.com/watch?v=VIDEO_ID" --force-from m2

# ─── LLM pipeline (Groq) ───

# run on a single video (requires Groq API key)
python -m lecture2graph.llm_pipeline.pipeline "https://www.youtube.com/watch?v=VIDEO_ID" \
  --api-key YOUR_GROQ_API_KEY

# or set env var and omit --api-key
export GROQ_API_KEY=YOUR_GROQ_API_KEY
python -m lecture2graph.llm_pipeline.pipeline "https://www.youtube.com/watch?v=VIDEO_ID"

# batch run all test videos
python scripts/run_llm_batch.py
```

## Architecture

### Two Pipelines

This project implements **two independent pipelines** for concept extraction:

| | Regex pipeline | LLM pipeline |
|---|---|---|
| **M3** | Heavy normalization + fuzzy OCR correction | Simplified cleanup (LLM handles noise) |
| **M4** | ~100 regex patterns + OCR keyword map | Groq LLM (llama-3.3-70b) semantic extraction |
| **M5** | ~80 domain rules + causal regex + temporal | Groq LLM prerequisite reasoning |
| **Strengths** | High recall, structural detail | High precision, discovers novel concepts |
| **Weaknesses** | Temporal edge padding, domain-locked | Rate limits, fewer structural details |

Both pipelines share **M1** (ingest), **M2** (ASR+OCR), and **M6** (visualize).

### Pipeline Overview (Regex Pipeline)

```
YouTube URL
    │
    ▼
┌─────────────────┐
│  M1: Ingestion  │  download video, extract audio (16kHz WAV), keyframes (1fps)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  M2: Extraction │  whisper ASR (translate mode) + tesseract OCR
└────────┬────────┘  <- KEY FIX: task="translate" for non-english
         │
         ▼
┌─────────────────┐
│  M3: Normalize  │  hallucination filter + fuzzy OCR correction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  M4: Concepts   │  regex pattern matching for CS concept extraction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  M5: Prereqs    │  domain rules + causal patterns + temporal edges → DAG
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  M6: Visualize  │  interactive HTML graph (vis.js) + markdown report
└─────────────────┘
```

### Pipeline Overview (LLM Pipeline)

```
YouTube URL
    │
    ▼
┌──────────────────────────┐
│  M1: Ingestion           │  <- reused from regex pipeline
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  M2: ASR + OCR           │  <- reused from regex pipeline
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  M3: Light Normalize     │  basic cleanup only (LLM handles noise)
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  M4: Groq LLM Concepts   │   semantic concept extraction
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  M5: Groq LLM Prereqs   │  LLM reasons about prerequisite relationships
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  M6: Visualize           │  <- reused from regex pipeline
└──────────────────────────┘
```

### Key Design Decision: Whisper Translate Mode

**Problem**: Hindi code-mixed lectures contain CS terms spoken in Hindi but
transcribed by Whisper in Devanagari script (e.g., "recursion" → "रिकर्जन",
"primary key" → "प्रामरी की"). English-only regex patterns in M4 could never
match these Devanagari representations, resulting in 0 concepts extracted.

**Solution**: Use Whisper's `task="translate"` instead of `task="transcribe"`.
This tells Whisper to translate all speech into English, which:
1. Converts Devanagari CS terms back to English ("रिकर्जन" → "recursion")
2. Handles Telugu and other Indic languages the same way
3. Has zero impact on English-only lectures (translate ≈ transcribe for English)
4. Requires no external translation APIs - Whisper handles it natively

**Dual output**: M2 saves both `transcript_original.json` (native script, for
reference) and `transcript.json` (English, used by M3-M6). The source language
is also saved in `detected_language.json`.

### Hallucination Filtering

Whisper hallucinates on certain audio types, especially Telugu/low-quality audio.
Common hallucinations include body part words, pop culture references, and
repetitive phrases. M3's enhanced filter catches these using:
- Known hallucination word list (body parts, gaming, politics)
- Pattern matching (repeated phrases, filler words, punctuation-only)
- Non-ASCII ratio check (should be mostly ASCII after translation)

### OCR Correction

M3 uses ASR-seeded vocabulary + RapidFuzz fuzzy matching to correct OCR errors.
Since M2 now produces English ASR output for all languages, the vocabulary is
rich in English CS terms regardless of source language.

## File Structure

```
Lecture2Graph/
├── lecture2graph/
│   ├── regex_pipeline/          # regex-based pipeline (M1-M6)
│   └── llm_pipeline/            # LLM-based pipeline (M3-M5 + reuse M1/M2/M6)
├── scripts/
│   ├── demo.py                  # interactive terminal demo (rich UI)
│   └── run_llm_batch.py         # batch runner for LLM pipeline
├── docs/
│   └── hardcoded-elements.md    # inventory of hardcoded rules (regex pipeline)
├── outputs/                     # generated artifacts (gitignored)
│   ├── regex/
│   └── llm/
├── requirements.txt
├── README.md
├── CHANGELOG.md
└── .gitignore
```

### Output Directory (per video)

```
outputs/regex/<video_id>/
├── video.mp4                 # downloaded video
├── audio.wav                 # extracted audio (16kHz mono)
├── frames/                   # keyframes at 1fps
├── detected_language.json    # whisper language detection result
├── transcript.json           # english transcript (translated if needed)
├── transcript_original.json  # original language transcript
├── ocr_raw.json              # raw OCR results
├── aligned_segments.json     # merged ASR + OCR segments
├── asr_vocabulary.json       # extracted vocabulary for fuzzy correction
├── normalized_segments.json  # cleaned & filtered segments
├── concepts.json             # extracted concepts with mention details
├── prerequisites.json        # prerequisite edges + topological order
├── graph.html                # interactive visualization
├── report.md                 # markdown summary report
└── pipeline_summary.json     # timing & result metrics
```

LLM pipeline outputs use the same layout under `outputs/llm/<video_id>/`.

## Module Details

### M1: Ingestion (`m1_ingest.py`)
- Downloads YouTube videos via `yt-dlp`
- Extracts audio at 16kHz mono WAV (for Whisper)
- Extracts keyframes at 1fps via `ffmpeg`
- Caches all outputs (skip if already downloaded)

### M2: Extraction (`m2_extract.py`)
- **Language detection**: Uses Whisper's `detect_language()` on first 30s
- **ASR**: Whisper `small` model with `task="translate"` for non-English
- **OCR**: Tesseract with `eng+hin` language data, 3-iteration best-confidence
- **Alignment**: Merges ASR + OCR segments sorted by timestamp
- **Dual output**: Saves both original and translated transcripts

### M3: Normalization (`m3_normalize.py`)
- **Hallucination filter**: Removes Whisper hallucinations (body parts, gaming, repetitive)
- **Vocabulary building**: Extracts English terms from ASR for fuzzy correction
- **OCR correction**: RapidFuzz fuzzy matching against ASR vocabulary (threshold: 75%)
- **Language tagging**: Tags segments with detected source language

### M4: Concept Extraction (`m4_concepts.py`)
- 26 regex patterns covering tree structures, graph algorithms, BFS/DFS, DBMS
- OCR keyword mapping for whiteboard/slide terms
- 10-second temporal deduplication window
- Tracks mention details (time, source, text snippet)

### M5: Prerequisite Mining (`m5_prereqs.py`)
- 38 domain knowledge rules (e.g., "binary_tree → binary_search_tree")
- Causal language patterns ("before X, need Y", "X requires Y")
- Temporal ordering with transitive reachability pruning
- Cycle prevention via topological sort validation

### M6: Visualization (`m6_visualize.py`)
- Custom HTML using vis-network.js (not pyvis)
- Dark theme with GitHub-style color palette
- Interactive: click nodes for detail panel
- Edge type legend (domain, causal, temporal, co-occurrence)
- Timeline heatmap showing mention distribution
- Topological order sidebar (clickable)
- Statistics dashboard

## Demo Interface

The `scripts/demo.py` script provides an interactive terminal UI:
- Accepts YouTube URL or video ID
- Shows real-time progress for all 6 pipeline stages
- Displays live log output capture
- Presents results in formatted tables with timings
- Lists all output files with sizes
- Falls back to basic output if `rich` is not installed

```bash
python scripts/demo.py
```

## Suggested Screenshots

If you want visuals in the README, these are the most compelling:
- `graph.html` interactive DAG view (dark theme + concept details sidebar)
- Terminal demo UI showing live pipeline progress
- Report excerpt (`report.md`) showing topological order and edge table
- Timeline heatmap panel from the HTML visualization

## Dependencies

- **whisper** (openai-whisper): ASR with translate mode
- **pytesseract**: OCR on keyframes
- **yt-dlp**: YouTube video download
- **rapidfuzz**: Fuzzy string matching for OCR correction (regex pipeline)
- **groq**: Groq API SDK for LLM inference (LLM pipeline)
- **rich**: Terminal UI for demo
- **Pillow**: Image processing for OCR
- **scenedetect**: (optional) scene detection

System requirements: `ffmpeg`, `tesseract-ocr` (with eng+hin language data)

## Tested Videos

### Regex Pipeline - All 5 Videos

| Video ID | Topic | Language | Concepts | Edges | Topo |
|----------|-------|----------|----------|-------|------|
| XRcC7bAtL3c | Tree Traversal | Hindi | 14 | 51 | 14/14 |
| N2P7w22tN9c | BFS/DFS Graph | Hindi | 12 | 41 | 12/12 |
| Tp37HXfekNo | DBMS Primary Keys | Hindi | 10 | 19 | 10/10 |
| azXr6nTaD9M | Recursion & Stack | Hindi | 7 | 16 | 7/7 |
| eXWl-Uor75o | Sorting & Merge Sort | Telugu | 8 | 21 | 8/8 |

### LLM Pipeline - implemented on 3 of 5 Videos (rate limited)

| Video ID | Topic | Language | Concepts | Edges | Topo |
|----------|-------|----------|----------|-------|------|
| XRcC7bAtL3c | Tree Traversal | Hindi | 7 | 6 | 7/7 |
| N2P7w22tN9c | BFS/DFS Graph | Hindi | 10 | 9 | 10/10 |
| azXr6nTaD9M | Recursion & Stack | Hindi | 9 | 8 | 9/9 |
| Tp37HXfekNo | DBMS Primary Keys | Hindi | - | - | ❌ rate limited |
| eXWl-Uor75o | Sorting & Merge Sort | Telugu | - | - | ❌ rate limited |

### Comparison of the two pipelines

| Metric | Regex pipeline | LLM pipeline |
|--------|-------------------|------------------|
| Total concepts | 33 | 26 |
| Total edges | 108 | 23 |
| Temporal/low-conf edges | 62 (57%) | 0 (0%) |
| Domain/causal edges | 37 + 0 | 18 + 5 |
| Unique concepts found | 14 | 7 |

See [CHANGELOG.md](CHANGELOG.md) for detailed per-video comparison.

## Limitations

1. **Whisper small on Telugu**: May produce lower quality translations. Can consider using `--model medium` for Telugu videos.
2. **Domain coverage (regex pipeline)**: M4 regex patterns cover trees, graphs, BFS/DFS, DBMS, sorting. New CS domains require extending the pattern list manually.
3. **Rate limits (LLM pipeline)**: Groq free tier has request/token limits. Only 3 of 5 videos completed. Production deployment needs a paid API plan or locally hosted LLM.
4. **LLM granularity (LLM pipeline)**: LLMs abstract away structural sub-concepts (left_subtree, node, children) in favor of higher-level terms.
5. **OCR quality**: Heavily depends on video resolution and text clarity.
6. **Processing time**: Whisper ASR is CPU-intensive. Two passes (transcribe + translate) for non-English videos doubles the ASR time.

See [docs/hardcoded-elements.md](docs/hardcoded-elements.md) for the full regex inventory.
