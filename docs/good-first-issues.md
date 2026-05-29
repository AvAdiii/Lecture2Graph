# Good First Issues

These are intentionally scoped so new contributors can ship something valuable without touching every layer of the repo.

## 1. Add an Operating Systems domain pack

Goal: teach Lecture2Graph to recognize concepts like process, thread, scheduling, deadlock, semaphore, and context switch.

Suggested files:

- `core/lecture2graph/plugins/builtin_domains/os.py`
- `core/lecture2graph/plugins/registry.py`

Acceptance:

- Adds concept patterns, OCR keywords, prerequisite rules, and descriptions.
- Works on a checked-in or new OS lecture sample.

## 2. Add a Computer Networks domain pack

Goal: support topics like TCP/IP, routing, subnetting, packet switching, congestion control, and DNS.

Suggested files:

- `core/lecture2graph/plugins/builtin_domains/networks.py`
- `core/lecture2graph/plugins/registry.py`

Acceptance:

- Produces a sensible learning path for a networking lecture.

## 3. Add a Machine Learning domain pack

Goal: support terms like dataset, feature, label, loss function, gradient descent, and overfitting.

Suggested files:

- `core/lecture2graph/plugins/builtin_domains/ml.py`
- `core/lecture2graph/plugins/registry.py`

Acceptance:

- Keeps patterns focused enough to avoid false positives in non-ML lectures.

## 4. Improve OCR accuracy

Goal: reduce noisy OCR segments from whiteboards and handwritten notes.

Suggested files:

- `core/lecture2graph/pipeline/extract.py`
- `core/lecture2graph/pipeline/normalize.py`

Ideas:

- Better image preprocessing before Tesseract.
- Smarter OCR deduplication across adjacent frames.
- Domain-aware correction for common handwritten confusions.

## 5. Improve graph readability

Goal: make dense concept graphs easier to scan.

Suggested files:

- `streamlit_app.py`
- `core/lecture2graph/pipeline/visualize.py`

Ideas:

- Better edge legends.
- Node clustering for related concepts.
- Tighter layout for long learning paths.

## 6. Add another language

Goal: improve transcript and UI support for one more lecture language such as Tamil or Kannada.

Suggested files:

- `core/lecture2graph/pipeline/extract.py`
- `core/lecture2graph/pipeline/artifacts.py`
- `streamlit_app.py`

Acceptance:

- Detected language is surfaced correctly in the bundle and UI.
- Original and translated transcript views remain usable.
