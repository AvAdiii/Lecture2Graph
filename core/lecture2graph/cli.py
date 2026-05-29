"""CLI entrypoint."""

from __future__ import annotations

import argparse
import sys

from lecture2graph.models import PipelineRequest
from lecture2graph.pipeline.orchestrator import hydrate_existing_run, load_result, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lecture2graph",
        description="Turn YouTube lectures into interactive concept graphs and learning paths.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Process a YouTube lecture.")
    run_parser.add_argument("url", help="YouTube URL or video ID")
    run_parser.add_argument("--engine", default="rules", help="rules, groq, gemini, or openai")
    run_parser.add_argument("--api-key", default=None, help="Optional provider API key")
    run_parser.add_argument("--whisper-model", default="small", help="Whisper model size")
    run_parser.add_argument("--data-root", default=None, help="Override the output directory")
    run_parser.add_argument("--force-from", default=None, choices=["extract", "normalize", "concepts", "graph", "artifacts"])

    hydrate_parser = subparsers.add_parser("hydrate", help="Rebuild product artifacts from an existing processed sample.")
    hydrate_parser.add_argument("video_id", help="Existing sample video ID")
    hydrate_parser.add_argument("--engine", default="rules")
    hydrate_parser.add_argument("--api-key", default=None)
    hydrate_parser.add_argument("--data-root", default=None)

    show_parser = subparsers.add_parser("show", help="Print the output paths for an existing result bundle.")
    show_parser.add_argument("video_id")
    show_parser.add_argument("--data-root", default=None)

    parser.add_argument("url", nargs="?", help=argparse.SUPPRESS)
    return parser


def main() -> None:
    parser = build_parser()
    argv = sys.argv[1:]
    if argv and argv[0] not in {"run", "hydrate", "show", "-h", "--help"}:
        argv = ["run", *argv]
    args = parser.parse_args(argv)

    if args.command == "run":
        result = run_pipeline(
            PipelineRequest(
                url=args.url,
                engine=args.engine,
                whisper_model=args.whisper_model,
                data_root=args.data_root,
                force_from=args.force_from,
                api_key=args.api_key,
            )
        )
        print(result.artifacts.graph_html)
        return

    if args.command == "hydrate":
        result = hydrate_existing_run(
            video_id=args.video_id,
            engine=args.engine,
            data_root=args.data_root,
            api_key=args.api_key,
        )
        print(result.artifacts.graph_html)
        return

    if args.command == "show":
        result = load_result(args.video_id, data_root=args.data_root)
        print(result.artifacts.graph_html)
        print(result.artifacts.notes_md)
        print(result.artifacts.bundle_json)
        return

    parser.print_help()
