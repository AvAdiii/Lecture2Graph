# neural, LLM-in-the-loop concept extraction & prerequisite mapping
#
# Key difference from the symbolic pipeline:
#   symbolic uses handcrafted regex patterns + hardcoded domain rules
#   neural sends the transcript to an LLM for semantic extraction
#
# LLM backend: a local OpenAI-compatible server (Ollama by default; configure
#   the model/endpoint via lecture2graph.neural.llm). Running locally removes
#   the cloud rate limits that originally capped this pipeline at 3/5 videos -
#   it can now re-process the whole corpus for free, offline.
#
# Shared modules (reused from the symbolic pipeline):
#   M1 (ingest)   , video download, audio extraction, keyframe extraction
#   M2 (extract)  , whisper ASR + tesseract OCR
#   M6 (visualize), hierarchical DAG HTML + markdown report
#
# New / replaced modules:
#   M3 (normalize), simplified: basic cleanup only (LLM handles noisy text)
#   M4 (concepts) , LLM extracts CS concepts semantically (not regex)
#   M5 (prereqs)  , LLM reasons about prerequisite relationships (not rules)
#
# Key findings (see evaluation/ for the measured comparison):
#   - LLM produces fewer but more precise edges (no temporal padding)
#   - LLM discovers application-level concepts regex misses (web_crawler,
#     activation_record, factorial, minimum_cost_spanning_tree)
#   - Regex captures more structural sub-concepts (left_subtree, right_subtree)
