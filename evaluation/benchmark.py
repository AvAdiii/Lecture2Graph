"""
Benchmark: symbolic vs. neural vs. hybrid extraction against the gold graphs.

For every video that has a gold annotation, score each available extraction
method and print a per-video table plus a macro-averaged summary (the headline
ablation). Results are also written to evaluation/results/ as JSON + Markdown so
they can be dropped straight into the README.

usage:
  python -m evaluation.benchmark
  python -m evaluation.benchmark --data-root data --gold-dir evaluation/gold
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from lecture2graph.graphs import load_graph
from lecture2graph.hybrid.fuse import fuse_video
from evaluation.metrics import evaluate, load_gold

METHODS = ["symbolic", "neural", "hybrid"]
_HEADLINE = ["edge_precision", "edge_recall", "edge_f1",
             "node_f1", "prereq_order_accuracy", "graph_edit_distance"]


def _method_graph(video: str, method: str, data_root: Path):
    base = data_root / video
    if method == "hybrid":
        # build hybrid on demand if both inputs exist
        if (base / "graph.symbolic.json").exists() and (base / "graph.neural.json").exists():
            return fuse_video(video, str(data_root))
        return None
    path = base / f"graph.{method}.json"
    if not path.exists():
        return None
    return load_graph(path, video_id=video, method=method)


def run(data_root: str = "data", gold_dir: str = "evaluation/gold") -> dict:
    data_root = Path(data_root)
    gold_paths = sorted(Path(gold_dir).glob("*.json"))

    per_video: dict[str, dict] = {}
    by_method: dict[str, list[dict]] = {m: [] for m in METHODS}

    for gp in gold_paths:
        video = gp.stem
        gold = load_gold(gp)
        per_video[video] = {"gold_edges": len(gold.prereq_edge_keys()),
                            "gold_nodes": len(gold.nodes), "methods": {}}
        for m in METHODS:
            g = _method_graph(video, m, data_root)
            if g is None:
                continue
            scores = evaluate(g, gold)
            per_video[video]["methods"][m] = scores
            by_method[m].append(scores)

    def macro(rows: list[dict]) -> dict:
        s = {k: round(mean(r[k] for r in rows), 3) for k in _HEADLINE}
        s["videos"] = len(rows)
        return s

    summary = {m: macro(rows) for m, rows in by_method.items() if rows}

    # Fair head-to-head: macro-average only over videos where EVERY method ran.
    common = [v for v, info in per_video.items()
              if all(m in info["methods"] for m in METHODS)]
    summary_common = {}
    for m in METHODS:
        rows = [per_video[v]["methods"][m] for v in common]
        if rows:
            summary_common[m] = macro(rows)

    return {"per_video": per_video, "summary": summary,
            "summary_common": summary_common, "common_videos": common}


def _fmt_table(summary: dict) -> str:
    cols = ["method", "videos", "edge_P", "edge_R", "edge_F1",
            "node_F1", "order_acc", "GED"]
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    keymap = {"edge_P": "edge_precision", "edge_R": "edge_recall",
              "edge_F1": "edge_f1", "node_F1": "node_f1",
              "order_acc": "prereq_order_accuracy", "GED": "graph_edit_distance"}
    for m in METHODS:
        if m not in summary:
            continue
        s = summary[m]
        row = [m, str(s["videos"])]
        for c in cols[2:]:
            row.append(f"{s[keymap[c]]:.3f}" if c != "GED" else f"{s[keymap[c]]:.1f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Run the extraction benchmark")
    p.add_argument("--data-root", default="data")
    p.add_argument("--gold-dir", default="evaluation/gold")
    p.add_argument("--out-dir", default="evaluation/results")
    args = p.parse_args()

    results = run(args.data_root, args.gold_dir)

    print("\n=== Per-video edge F1 ===")
    header = f"{'video':<14} " + " ".join(f"{m:>9}" for m in METHODS)
    print(header)
    for v, info in results["per_video"].items():
        cells = []
        for m in METHODS:
            sc = info["methods"].get(m)
            cells.append(f"{sc['edge_f1']:.3f}" if sc else "    -   ")
        print(f"{v:<14} " + " ".join(f"{c:>9}" for c in cells))

    table_all = _fmt_table(results["summary"])
    table_common = _fmt_table(results["summary_common"])
    common = ", ".join(results["common_videos"])
    print("\n=== Macro-averaged (all available videos) ===")
    print(table_all)
    print(f"\n=== Fair head-to-head (common subset: {common}) ===")
    print(table_common)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "benchmark.json").write_text(json.dumps(results, indent=2))
    legend = (
        "\n\n- **edge_P/R/F1** — directed prerequisite-edge precision / recall / F1\n"
        "- **node_F1** — concept-recovery F1\n"
        "- **order_acc** — fraction of gold 'A before B' pairs ordered correctly\n"
        "- **GED** — graph edit distance (node + edge symmetric difference; lower is better)\n"
    )
    (out / "benchmark.md").write_text(
        "# Benchmark: symbolic vs. neural vs. hybrid\n\n"
        "## Fair head-to-head\n\n"
        f"Macro-averaged over the {len(results['common_videos'])} videos where all "
        "three methods ran (" + common + ").\n\n" + table_common + "\n\n"
        "## All available videos\n\n"
        "Symbolic also covers videos the neural pipeline had not yet processed, "
        "so this view is not a like-for-like comparison.\n\n"
        + table_all + legend
    )
    print(f"\nWrote {out/'benchmark.json'} and {out/'benchmark.md'}")


if __name__ == "__main__":
    main()
