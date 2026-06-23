# Lecture2Graph

Lecture2Graph watches a lecture video and produces a **prerequisite graph**:
a map of every concept the lecture teaches and which ones depend on which
others. Point it at a recording, and instead of a flat transcript you get a
study order, "to understand X, learn A, then B, then C first."

The lectures this was built and tested on are recorded Hindi/English
code-mixed computer science classes filmed off a whiteboard or notebook, the
kind where the instructor talks through an idea while writing diagrams,
variable names, and worked examples by hand at the same time. That means
there are two separate raw signals to pull concepts out of:

- **Speech** -> transcribed with Whisper (ASR) into a timestamped transcript.
- **Handwriting** -> the video frames are sampled and run through Tesseract
  (OCR) to pull out whatever text is legible on the board (node labels,
  keywords like "BFS" or "O(n)", partial diagrams), then cleaned up with
  fuzzy correction seeded from the speech transcript, since raw handwriting
  OCR is unreliable on its own.

Both signals are timestamped and merged into one stream of "what was said or
shown, and when," which is what every downstream method (symbolic and
neural alike) actually consumes. The [ablation below](#ablation-does-the-board-ocr-actually-matter)
measures how much that handwriting signal is actually worth.

Three independent methods build that graph, and each is scored against a
human-written answer key so the comparison isn't just qualitative:

| method | how it builds the graph | score (edge F1) |
|---|---|---|
| symbolic | hand-written rules: regex pattern matching + a curated set of CS prerequisite rules | 0.540 |
| neural | a local LLM (7B, runs on a laptop, no cloud) reads the transcript and reasons about dependencies | 0.174 |
| **hybrid** | **combines both, weighting agreement higher and resolving disagreements** | **0.551** |

*Edge F1 measures how many of the "A must be learned before B" relationships
the method finds match the ones in a human-written answer key, balancing
false positives against missed dependencies. Higher is better; 1.0 would mean
a perfect match. Full numbers, including concept-recovery and ordering
accuracy, in [`evaluation/results/benchmark.md`](evaluation/results/benchmark.md).*

The rule-based method alone is already decent. The small local LLM alone is
noisy. But combining them produces a better graph than either alone, because
they tend to make *different* mistakes, so merging them with confidence
weighting cancels out a good chunk of the noise instead of compounding it.

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
  ablation.py      isolates how much OCR contributes to the symbolic score
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

## Ablation: does the board (OCR) actually matter?

The symbolic pipeline reads two signals: what the instructor *says* (speech,
via Whisper) and what they *write* (handwriting, via OCR). To check whether
OCR is pulling its weight or just adding noise, it was re-run on the same 5
lectures with OCR disabled, speech only, everything else identical, and
scored against the same gold graphs:

| input | edge F1 | node F1 | order accuracy |
|---|---|---|---|
| speech only (no OCR) | 0.482 | 0.808 | 0.899 |
| speech + OCR (default) | **0.540** | **0.833** | **0.921** |

OCR earns its place: speech alone underperforms across every metric, and on
lectures where the instructor narrates less while writing more, OCR is the
difference between recovering an edge and missing it entirely (e.g. one
lecture's edge F1 goes from 0.286 to 0.444 with OCR included). Full per-video
breakdown in [`evaluation/results/ablation_ocr.md`](evaluation/results/ablation_ocr.md),
reproduce with `python -m evaluation.ablation`.

## License

MIT, see [LICENSE](LICENSE).
