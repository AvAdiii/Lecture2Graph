#!/usr/bin/env python3
"""
demo.py — interactive terminal demo for the concept extraction pipeline

a rich terminal ui that:
  - accepts a youtube url (or video id)
  - shows real-time progress through all 6 pipeline stages
  - displays live log capture
  - presents results in formatted tables
  - opens the output html visualization

requires: rich (pip install rich)
"""

import sys
import re
import time
import threading
from pathlib import Path

# add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# try importing rich
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich.markdown import Markdown
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from lecture2graph.regex_pipeline import pipeline as pipe1

OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "regex"


# ───────────────── ansi fallback (no rich) ─────────────────

def _fallback_demo():
    """simple fallback when rich is not installed."""
    print("\n" + "=" * 60)
    print("  Lecture2Graph")
    print("  Lecture-to-concept DAG extraction")
    print("=" * 60)
    print()

    url = input("  Enter YouTube URL or video ID: ").strip()
    if not url:
        print("  no url provided, exiting.")
        return

    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        url = "https://www.youtube.com/watch?v=" + url

    model = input("  Whisper model [small]: ").strip() or "small"
    force = input("  Force from stage (m1-m6, or enter to skip): ").strip() or None

    print()
    print("  starting pipeline...")
    print("-" * 60)

    summary = pipe1.run_pipeline(url, model=model, data_root=str(OUTPUT_ROOT),
                                 force_from=force)

    print("-" * 60)
    print(f"\n  results:")
    print(f"    video:    {summary['video_id']}")
    print(f"    language: {summary['detected_language']}")
    print(f"    concepts: {summary['n_concepts']}")
    print(f"    edges:    {summary['n_edges']}")
    print(f"    topo:     {summary['n_topo']}/{summary['n_concepts']}")
    print(f"    time:     {summary['total_time']}s")
    print(f"    output:   {summary['data_dir']}/graph.html")
    print()


# ───────────────── rich demo ─────────────────

STAGE_INFO = {
    "m1": ("Download & Extract", "downloading video, extracting audio & keyframes"),
    "m2": ("ASR + OCR", "running whisper transcription & tesseract ocr"),
    "m3": ("Normalization", "cleaning text, filtering hallucinations, correcting ocr"),
    "m4": ("Concept Extraction", "identifying CS concepts via pattern matching"),
    "m5": ("Prerequisite Mining", "building prerequisite DAG with domain rules"),
    "m6": ("Visualization", "generating interactive html graph & report"),
}


class LogCapture:
    """capture stdout to a log buffer while still printing."""
    def __init__(self, max_lines=50):
        self.lines = []
        self.max_lines = max_lines
        self._old_stdout = None
        self._old_stderr = None

    def start(self):
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def stop(self):
        if self._old_stdout:
            sys.stdout = self._old_stdout
        if self._old_stderr:
            sys.stderr = self._old_stderr

    def write(self, text):
        if text.strip():
            self.lines.append(text.rstrip())
            if len(self.lines) > self.max_lines:
                self.lines = self.lines[-self.max_lines:]
        if self._old_stdout:
            self._old_stdout.write(text)

    def flush(self):
        if self._old_stdout:
            self._old_stdout.flush()

    def get_recent(self, n=15):
        return self.lines[-n:]


def _rich_demo():
    """full rich terminal demo."""
    console = Console()

    # header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Lecture2Graph[/]\n"
        "[dim]Lecture-to-concept DAG extraction[/]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()

    # input
    url = console.input("[bold green]►[/] YouTube URL or video ID: ").strip()
    if not url:
        console.print("[red]no url provided, exiting.[/]")
        return

    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        url = "https://www.youtube.com/watch?v=" + url

    model = console.input("[bold green]►[/] Whisper model [dim]\\[small][/]: ").strip() or "small"
    force = console.input("[bold green]►[/] Force from stage [dim](m1-m6 or enter)[/]: ").strip() or None
    if force and force not in pipe1.STAGES:
        console.print(f"[red]invalid stage: {force}[/]")
        return

    console.print()

    # state tracking
    stage_status = {s: "waiting" for s in pipe1.STAGES}
    stage_results = {}
    current_stage = [None]
    log_capture = LogCapture(max_lines=100)

    def progress_callback(stage, status, info):
        if stage == "done":
            return
        if status == "start":
            stage_status[stage] = "running"
            current_stage[0] = stage
        elif status == "done":
            stage_status[stage] = "done"
            stage_results[stage] = info
        elif status == "error":
            stage_status[stage] = "error"
            stage_results[stage] = info

    # build the display
    def make_display():
        # progress table
        tbl = Table(
            show_header=True, header_style="bold",
            box=box.SIMPLE_HEAVY, expand=True,
            title="Pipeline Progress",
            title_style="bold cyan",
        )
        tbl.add_column("#", width=3, justify="center")
        tbl.add_column("Module", width=22)
        tbl.add_column("Status", width=10, justify="center")
        tbl.add_column("Detail", ratio=1)

        for i, s in enumerate(pipe1.STAGES, 1):
            name, desc = STAGE_INFO.get(s, (s, ""))
            st = stage_status[s]
            if st == "waiting":
                icon = "[dim]○[/]"
                detail = f"[dim]{desc}[/]"
            elif st == "running":
                icon = "[yellow]◉[/]"
                detail = f"[yellow]{desc}...[/]"
            elif st == "done":
                icon = "[green]✓[/]"
                info = stage_results.get(s, {})
                detail = _format_result(s, info)
            elif st == "error":
                icon = "[red]✗[/]"
                info = stage_results.get(s, {})
                detail = f"[red]{info.get('error', 'failed')}[/]"
            else:
                icon = "?"
                detail = ""

            tbl.add_row(str(i), name, icon, detail)

        # log panel
        recent_logs = log_capture.get_recent(12)
        log_text = "\n".join(recent_logs) if recent_logs else "[dim]waiting...[/]"

        log_panel = Panel(
            log_text,
            title="[bold]Live Log[/]",
            border_style="dim",
            height=14,
            expand=True,
        )

        return tbl, log_panel

    def _format_result(stage, info):
        if stage == "m1":
            return f"[green]{info.get('n_frames', '?')} frames extracted[/]"
        elif stage == "m2":
            lang = info.get("detected_language", "?")
            n_asr = info.get("n_asr_segments", "?")
            n_ocr = info.get("n_ocr_segments", "?")
            return f"[green]lang={lang} asr={n_asr} ocr={n_ocr}[/]"
        elif stage == "m3":
            n_out = info.get("n_output", "?")
            n_hall = info.get("n_hallucinations", 0)
            vocab = info.get("vocab_size", "?")
            return f"[green]{n_out} segments, {n_hall} hallucinations filtered, vocab={vocab}[/]"
        elif stage == "m4":
            n = info.get("n_concepts", "?")
            return f"[green]{n} concepts extracted[/]"
        elif stage == "m5":
            n_e = info.get("n_edges", "?")
            n_t = info.get("n_topo", "?")
            return f"[green]{n_e} edges, topo={n_t}[/]"
        elif stage == "m6":
            return f"[green]graph.html + report.md generated[/]"
        return "[green]done[/]"

    # run pipeline in a thread, display progress with Live
    result = [None]
    error = [None]

    def run_thread():
        try:
            log_capture.start()
            result[0] = pipe1.run_pipeline(
                url, model=model, data_root=str(OUTPUT_ROOT),
                force_from=force, callback=progress_callback,
            )
        except Exception as e:
            error[0] = e
        finally:
            log_capture.stop()

    thread = threading.Thread(target=run_thread, daemon=True)

    with Live(console=console, refresh_per_second=4) as live:
        thread.start()
        while thread.is_alive():
            tbl, log_panel = make_display()
            from rich.console import Group
            live.update(Group(tbl, log_panel))
            time.sleep(0.25)
        # final update
        tbl, log_panel = make_display()
        from rich.console import Group
        live.update(Group(tbl, log_panel))

    console.print()

    if error[0]:
        console.print(f"[bold red]Pipeline failed:[/] {error[0]}")
        return

    summary = result[0]
    if not summary:
        console.print("[red]no results[/]")
        return

    # results panel
    results_tbl = Table(
        show_header=False, box=box.ROUNDED,
        title="Results", title_style="bold green",
        expand=False, padding=(0, 2),
    )
    results_tbl.add_column("Key", style="bold")
    results_tbl.add_column("Value", style="cyan")

    results_tbl.add_row("Video ID", summary["video_id"])
    results_tbl.add_row("Language", summary["detected_language"])
    results_tbl.add_row("Concepts", str(summary["n_concepts"]))
    results_tbl.add_row("Edges", str(summary["n_edges"]))
    results_tbl.add_row("Topo Order", f"{summary['n_topo']}/{summary['n_concepts']}")
    results_tbl.add_row("Total Time", f"{summary['total_time']}s")
    results_tbl.add_row("Output", f"{summary['data_dir']}/graph.html")

    # timings
    if summary.get("timings"):
        timing_parts = []
        for s, t in summary["timings"].items():
            name = STAGE_INFO.get(s, (s,))[0]
            timing_parts.append(f"{name}: {t}s")
        results_tbl.add_row("Timings", " | ".join(timing_parts))

    console.print(results_tbl)
    console.print()

    # show output files
    data_dir = Path(summary["data_dir"])
    if data_dir.exists():
        files_tbl = Table(
            title="Output Files", title_style="bold",
            box=box.SIMPLE, expand=False,
        )
        files_tbl.add_column("File", style="cyan")
        files_tbl.add_column("Size", justify="right")

        for f in sorted(data_dir.glob("*.json")) + sorted(data_dir.glob("*.html")) + sorted(data_dir.glob("*.md")):
            size = f.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            files_tbl.add_row(f.name, size_str)

        console.print(files_tbl)
        console.print()

    console.print("[dim]open graph.html in a browser to see the interactive visualization[/]")
    console.print()


# ───────────────── main ─────────────────

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("usage: python scripts/demo.py")
        print("  interactive terminal demo for the concept extraction pipeline")
        print("  requires: rich (pip install rich)")
        return

    if HAS_RICH:
        _rich_demo()
    else:
        print("[!] 'rich' not installed — using basic terminal mode")
        print("    install with: pip install rich")
        print()
        _fallback_demo()


if __name__ == "__main__":
    main()
