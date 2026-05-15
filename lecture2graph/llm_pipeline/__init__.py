# LLM pipeline — concept extraction & prerequisite mapping
#
# Key difference from the regex pipeline:
#   regex uses handcrafted patterns + domain rules
#   this pipeline sends the transcript to an LLM for semantic extraction
#
# LLM backend: Groq API (llama-3.3-70b-versatile)
#   Initially attempted Gemini 2.0 Flash but hit free-tier rate limits
#   (quota: 0 requests/min after initial burst). Switched to Groq which
#   provides fast inference on open-weight models with generous free tier.
#
# Shared modules (reused from the regex pipeline):
#   M1 (ingest)    — video download, audio extraction, keyframe extraction
#   M2 (extract)   — whisper ASR (translate mode) + tesseract OCR
#   M6 (visualize) — vis.js hierarchical DAG HTML + markdown report
#
# New / replaced modules:
#   M3 (normalize) — simplified: basic cleanup only (LLM handles noisy text)
#   M4 (concepts)  — LLM extracts CS concepts semantically (not regex)
#   M5 (prereqs)   — LLM reasons about prerequisite relationships (not rules)
#
# Results (3/5 videos completed before rate limits):
#   XRcC7bAtL3c — 7 concepts, 6 edges   (regex: 14 concepts, 51 edges)
#   N2P7w22tN9c — 10 concepts, 9 edges  (regex: 12 concepts, 41 edges)
#   azXr6nTaD9M — 9 concepts, 8 edges   (regex: 7 concepts, 16 edges)
#   Tp37HXfekNo — NOT PROCESSED (rate limit)
#   eXWl-Uor75o — NOT PROCESSED (rate limit)
#
# Key findings:
#   - LLM produces fewer but more precise edges (no temporal padding)
#   - LLM discovers application-level concepts regex misses (web_crawler,
#     activation_record, factorial, minimum_cost_spanning_tree)
#   - Regex captures more structural sub-concepts (left_subtree, right_subtree)
#   - See CHANGELOG.md for full comparison table
