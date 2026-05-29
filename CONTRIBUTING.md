# Contributing to Lecture2Graph

Lecture2Graph is organized around one clean product path:

- Streamlit app for the web experience
- reusable Python core for the pipeline and CLI

## Local setup

1. Clone the repo.
2. Create a Python 3.10+ environment.
3. Install the package:

```bash
pip install -e .
```

4. Optional provider support:

```bash
pip install -e ".[llm]"
```

5. Install system dependencies:

- `ffmpeg`
- `tesseract-ocr`

6. Run the app:

```bash
streamlit run streamlit_app.py
```

## Project structure

- `streamlit_app.py`: main web app
- `core/lecture2graph/`: pipeline, CLI, models, plugin system
- `data/`: bundled sample results and generated outputs
- `docs/`: project docs and issue ideas
- `utils/`: small helper scripts

## How to add a new CS domain

1. Create a module in [`core/lecture2graph/plugins/builtin_domains/`](core/lecture2graph/plugins/builtin_domains).
2. Export a `DomainPlugin` with:
   - `concept_patterns`
   - `ocr_keywords`
   - `prerequisite_rules`
   - `fragment_aliases`
   - `descriptions`
3. Register it in [`core/lecture2graph/plugins/registry.py`](core/lecture2graph/plugins/registry.py).

## How to add new regex patterns

Keep patterns narrow and concept-specific.

Good:

```python
"merge sort": [r"merge\\s+sort"]
```

Risky:

```python
"tree": [r"\\broot\\b"]
```

Prefer domain-owned patterns over giant global pattern files.

## How to extend LLM prompts

Provider engines live in:

- [`core/lecture2graph/pipeline/groq_engine.py`](core/lecture2graph/pipeline/groq_engine.py)
- [`core/lecture2graph/pipeline/gemini_engine.py`](core/lecture2graph/pipeline/gemini_engine.py)
- [`core/lecture2graph/pipeline/openai_engine.py`](core/lecture2graph/pipeline/openai_engine.py)

If you change the output contract in one provider, keep the others aligned too.

## Plugin system

External plugins can be loaded through `LECTURE2GRAPH_PLUGIN_PATHS`.

Minimal example:

```python
from lecture2graph.plugins.base import DomainPlugin

def register(registry):
    registry.register_domain(DomainPlugin(name="my_domain"))
```

## Good first issues

See [docs/good-first-issues.md](docs/good-first-issues.md).

## Before opening a PR

Run:

```bash
python -m compileall core/lecture2graph streamlit_app.py
lecture2graph show XRcC7bAtL3c
streamlit run streamlit_app.py
```

