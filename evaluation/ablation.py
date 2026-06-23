"""
Ablation: does OCR (the handwritten board) actually help the symbolic
pipeline, or could it run on speech alone?

For each video, the cached `normalized_segments.json` is stripped of its OCR
signal and concept + prerequisite extraction is re-run from scratch (in a
throwaway directory, the committed cache under data/ is never touched) to
produce an ASR-only graph. That graph is scored against the same gold
annotation as the full ASR+OCR symbolic graph already in evaluation/results.

usage:
  python -m evaluation.ablation
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from statistics import mean

from lecture2graph.symbolic import concepts as m4_concepts
from lecture2graph.symbolic import prereqs as m5_prereqs
from lecture2graph.graphs import load_graph
from evaluation.metrics import evaluate, load_gold

_HEADLINE = ["edge_precision", "edge_recall", "edge_f1",
             "node_f1", "prereq_order_accuracy", "graph_edit_distance"]


def _strip_ocr(segments: list[dict]) -> list[dict]:
    """Drop OCR signal from normalized segments, keep ASR (speech) only."""
    out = []
    for seg in segments:
        if "spoken_text" in seg:
            # old format: one fused segment per timestep, has both signals
            s = dict(seg)
            s["ocr_keywords"] = []
            out.append(s)
        else:
            # new format: each segment is purely asr or purely ocr
            if seg.get("source") != "ocr":
                out.append(seg)
    return out


def asr_only_graph(video_id: str, data_root: Path):
    """Rebuild concepts + prereq graph for one video using ASR signal only."""
    segments = json.loads((data_root / video_id / "normalized_segments.json").read_text())
    filtered = _strip_ocr(segments)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp) / video_id
        tmp_dir.mkdir(parents=True)
        (tmp_dir / "normalized_segments.json").write_text(json.dumps(filtered))

        m4_concepts.run(video_id, data_root=tmp)
        m5_prereqs.run(video_id, data_root=tmp)

        return load_graph(tmp_dir / "graph.json", video_id=video_id, method="symbolic_asr_only")


def run(data_root: str = "data", gold_dir: str = "evaluation/gold") -> dict:
    data_root = Path(data_root)
    gold_paths = sorted(Path(gold_dir).glob("*.json"))

    per_video: dict[str, dict] = {}
    rows = {"asr_only": [], "asr_ocr": []}

    for gp in gold_paths:
        video = gp.stem
        gold = load_gold(gp)

        full_path = data_root / video / "graph.symbolic.json"
        if not full_path.exists():
            continue
        full_graph = load_graph(full_path, video_id=video, method="symbolic")
        asr_graph = asr_only_graph(video, data_root)

        full_scores = evaluate(full_graph, gold)
        asr_scores = evaluate(asr_graph, gold)
        per_video[video] = {"asr_ocr": full_scores, "asr_only": asr_scores}
        rows["asr_ocr"].append(full_scores)
        rows["asr_only"].append(asr_scores)

    summary = {
        variant: {k: round(mean(r[k] for r in scores), 3) for k in _HEADLINE}
        for variant, scores in rows.items() if scores
    }
    for variant in summary:
        summary[variant]["videos"] = len(rows[variant])

    return {"per_video": per_video, "summary": summary}


def _to_markdown(result: dict) -> str:
    lines = ["# Ablation: does OCR (the board) help the symbolic pipeline?", ""]
    lines.append("Same 5 lectures, same gold graphs, same symbolic pipeline, the only "
                  "difference is whether handwritten-board OCR is fed in alongside speech.")
    lines.append("")
    lines.append("| input | videos | edge_P | edge_R | edge_F1 | node_F1 | order_acc | GED |")
    lines.append("|---|---|---|---|---|---|---|---|")
    labels = {"asr_only": "speech only (no OCR)", "asr_ocr": "speech + OCR (default)"}
    for variant in ["asr_only", "asr_ocr"]:
        s = result["summary"][variant]
        lines.append(f"| {labels[variant]} | {s['videos']} | {s['edge_precision']} | "
                      f"{s['edge_recall']} | {s['edge_f1']} | {s['node_f1']} | "
                      f"{s['prereq_order_accuracy']} | {s['graph_edit_distance']} |")
    lines.append("")
    lines.append("Per-video edge_F1:")
    lines.append("")
    lines.append("| video | speech only | speech + OCR |")
    lines.append("|---|---|---|")
    for video, scores in result["per_video"].items():
        lines.append(f"| {video} | {scores['asr_only']['edge_f1']:.3f} | "
                      f"{scores['asr_ocr']['edge_f1']:.3f} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", default="data")
    p.add_argument("--gold-dir", default="evaluation/gold")
    args = p.parse_args()

    result = run(args.data_root, args.gold_dir)

    print("\nOCR ablation, speech-only vs speech+OCR (symbolic pipeline):\n")
    for variant, s in result["summary"].items():
        print(f"  {variant:10s}  edge_F1={s['edge_f1']:.3f}  node_F1={s['node_f1']:.3f}  "
              f"order_acc={s['prereq_order_accuracy']:.3f}")

    out_dir = Path("evaluation/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation_ocr.json").write_text(json.dumps(result, indent=2))
    (out_dir / "ablation_ocr.md").write_text(_to_markdown(result))
    print(f"\n[ablation] wrote {out_dir / 'ablation_ocr.json'} and ablation_ocr.md")


if __name__ == "__main__":
    main()
