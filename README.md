# Lecture2Graph

Turn a lecture video into a map of what to learn, and in what order.

Lecture2Graph watches a lecture (Hindi/English code-mixed, spoken + written on
a board) and builds a **prerequisite graph**: which concepts the lecture
teaches, and which ones you need to know before which others.

It builds this graph three different ways, and measures which one wins:

| method | how it works | edge F1 | node F1 | order accuracy |
|---|---|---|---|---|
| symbolic | regex + hand-written domain rules | 0.540 | **0.833** | 0.921 |
| neural | a local LLM reads the transcript | 0.174 | 0.479 | 0.527 |
| **hybrid** | **combines both** | **0.551** | 0.804 | **0.932** |

<sub>Averaged over 5 lectures. Reproduce with `python -m evaluation.benchmark`
→ [full results](evaluation/results/benchmark.md). The LLM is a 7B model
running fully locally via Ollama, no API key, no cloud.</sub>

**The takeaway:** the rule-based extractor alone is already strong. The local
LLM alone is weak and inconsistent. But combining them beats both individually
on accuracy, recall, and getting the order right, because each one's mistakes
are different, so a confidence-weighted fusion cancels out most of the noise.

---

## Why this isn't just "feed it to an LLM"

**1. The input is two messy signals that disagree.** The lecturer speaks
(code-mixed Hindi/English, picked up by Whisper) and writes on a board (picked
up by raw OCR, which is unreliable on handwriting). The symbolic pipeline
builds a vocabulary from the clean speech transcript and uses that to
fuzzy-correct OCR errors (`"Koot"` → `"root"`), so it adapts to new handwriting
without per-video tuning.

**2. Teaching order isn't dependency order.** A lecturer might give an example
(say, pre-order traversal) before explaining the general concept it depends on
(tree traversal). Naively ordering concepts by when they're first mentioned
gets this backwards. The graph builder instead combines domain rules, causal
phrases ("X means Y", "pehle X phir Y"), and mention-order, while checking that
no new edge contradicts an already-established dependency path.

**3. The two extractors don't even agree on vocabulary.** The rule-based and
LLM-based pipelines output different schemas and call the same concept
different things (`"bfs"` vs `"breadth first search"`). Before they can be
compared or fused, everything is normalized into one canonical name space
(`lecture2graph/graphs.py`).

---

## How it works

```
YouTube lecture URL
        │
        ▼
  ASR (Whisper) + OCR (Tesseract) + transcript-seeded OCR correction
        │
        ├──────────────────┐
        ▼                  ▼
   SYMBOLIC            NEURAL
   regex + rules       local LLM (Ollama)
        │                  │
        └────────┬─────────┘
                  ▼
            HYBRID  (fuse the two graphs:
                      confidence-weighted, conflict-resolved,
                      guaranteed acyclic)
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   EVALUATION          GRAPH-RAG TUTOR
   score vs gold        "what should I learn
   prerequisite graphs   before X?"
```

## Repo layout

```
lecture2graph/
  graphs.py        shared concept canonicalization + graph data structure
  symbolic/        rule-based pipeline
  neural/          local-LLM pipeline (talks to Ollama)
  hybrid/fuse.py   combines the two into one graph
  tutor/tutor.py   answers "what do I need to learn first?" from the graph
evaluation/
  gold/            hand-written correct prerequisite graphs, for scoring
  metrics.py       precision/recall/F1, ordering accuracy, edit distance
  benchmark.py     runs all three methods and compares them
tests/             sanity checks
data/              cached per-video outputs (transcripts, graphs)
```

---

## Try it

Everything below runs **offline on cached data** already in this repo, no API
key, no GPU needed.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m evaluation.benchmark     # reproduce the table above
python -m lecture2graph.hybrid.fuse   # rebuild the hybrid graphs

# ask: what should I learn before "pre_order_traversal"?
python -m lecture2graph.tutor.tutor XRcC7bAtL3c --before pre_order_traversal
```

```
To learn 'pre_order_traversal', study these first:
  1. tree            [3s]
  2. node            [12s]
  3. binary_tree     [99s]
  ...
  9. tree_traversal  [3s]
```

### Running it on a new video

This needs `ffmpeg`, `tesseract`, and a local LLM server. With
[Ollama](https://ollama.com):

```bash
ollama pull llama3.1:8b && ollama serve

python -m lecture2graph.symbolic.pipeline "https://youtu.be/VIDEO_ID"
python -m lecture2graph.neural.pipeline   "https://youtu.be/VIDEO_ID"
python -m lecture2graph.hybrid.fuse VIDEO_ID
```

---

## How it's scored

- A human wrote a "correct" prerequisite graph for each of the 5 lectures
  (`evaluation/gold/`). Edge `A → B` means "learn A before B."
- Each method's output is compared against that gold graph: precision/recall/F1
  on both concepts and edges, how often the predicted order respects the gold
  order, and a structural edit-distance score.
- All three methods are scored on the exact same 5 lectures, so the
  comparison is apples-to-apples.

## Honest limitations

- 5 lectures is a real but small sample, treat it as a pilot, not a
  statistically powered benchmark.
- The local LLM is a 7B model, chosen to run on a normal laptop. It's weak on
  noisy lectures (on 2 of 5 it finds almost nothing useful). A bigger model
  would likely close the neural/hybrid gap further; the architecture wouldn't
  need to change.
- The gold graphs were written by one annotator, not cross-checked by multiple
  people.
- The rule-based side is CS-specific. Teaching it a new subject means writing
  new domain rules, see [`docs/symbolic-hardcoding.md`](docs/symbolic-hardcoding.md).

## Background

This started as a take-home task for a research lab's recruitment process (a
code-mixed, multimodal concept extractor). It was later rebuilt into this
measured, neuro-symbolic system, the fusion logic, evaluation benchmark, and
tutor are new work built on top of that original pipeline.

## License

MIT, see [LICENSE](LICENSE).
