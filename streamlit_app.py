"""Streamlit app for Lecture2Graph."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


REPO_ROOT = Path(__file__).resolve().parent
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from lecture2graph.config import resolve_data_root
from lecture2graph.models import LectureGraphResult, PipelineRequest
from lecture2graph.pipeline.orchestrator import load_result, run_pipeline
from lecture2graph.plugins import get_registry
from lecture2graph.utils.youtube import watch_url


SAMPLE_CATALOG = [
    ("XRcC7bAtL3c", "Tree Traversal Walkthrough", "Binary tree traversal orders", "English"),
    ("N2P7w22tN9c", "BFS vs DFS", "Graph traversal intuition", "English"),
    ("Tp37HXfekNo", "DBMS Keys Explained", "Primary, candidate, and foreign keys", "Hindi"),
    ("azXr6nTaD9M", "Recursion and Stack Frames", "Recursive reasoning and call stack", "Hindi"),
    ("eXWl-Uor75o", "Sorting and Merge Sort", "Sorting intuition and merge sort", "Telugu"),
]


st.set_page_config(
    page_title="Lecture2Graph",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_sample(video_id: str) -> LectureGraphResult:
    return load_result(video_id, data_root=resolve_data_root())


def load_graph_html(result: LectureGraphResult) -> str:
    return Path(result.artifacts.graph_html).read_text(encoding="utf-8")


def result_files(result: LectureGraphResult) -> dict[str, bytes]:
    return {
        "graph.html": Path(result.artifacts.graph_html).read_bytes(),
        "notes.md": Path(result.artifacts.notes_md).read_bytes(),
        "lecture2graph.json": Path(result.artifacts.bundle_json).read_bytes(),
    }


def pick_default_concept(result: LectureGraphResult) -> str | None:
    if result.graph.topological_order:
        return result.graph.topological_order[0]
    if result.concepts:
        return result.concepts[0].id
    return None


def set_active_result(result: LectureGraphResult) -> None:
    st.session_state["result"] = result
    st.session_state["selected_concept_id"] = pick_default_concept(result)


def concept_options(result: LectureGraphResult) -> dict[str, str]:
    return {concept.name: concept.id for concept in result.concepts}


def selected_concept(result: LectureGraphResult):
    selected_id = st.session_state.get("selected_concept_id")
    for concept in result.concepts:
        if concept.id == selected_id:
            return concept
    if result.concepts:
        st.session_state["selected_concept_id"] = result.concepts[0].id
        return result.concepts[0]
    return None


def render_sidebar() -> None:
    st.sidebar.title("Lecture2Graph")
    st.sidebar.caption("Understand any lecture instantly.")

    engines = get_registry().engines()
    engine_names = [engine.name for engine in engines]
    engine_labels = {engine.name: engine.label for engine in engines}
    engine_requirements = {engine.name: engine.requires_api_key for engine in engines}

    with st.sidebar.form("process_form"):
        url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        engine = st.selectbox(
            "Engine",
            options=engine_names,
            format_func=lambda value: engine_labels[value],
            index=engine_names.index("rules") if "rules" in engine_names else 0,
        )
        api_key = st.text_input(
            "Provider API key",
            placeholder="Needed only for Groq, Gemini, and OpenAI",
            type="password",
        )
        submitted = st.form_submit_button("Generate graph", use_container_width=True)

    if submitted:
        if not url.strip():
            st.sidebar.error("Paste a YouTube URL first.")
        else:
            try:
                with st.spinner("Processing lecture. This can take a while for fresh videos."):
                    result = run_pipeline(
                        PipelineRequest(
                            url=url.strip(),
                            engine=engine,
                            api_key=api_key.strip() or None,
                        )
                    )
                set_active_result(result)
                st.sidebar.success("Graph generated.")
            except Exception as exc:
                if engine_requirements.get(engine) and not api_key.strip():
                    st.sidebar.error(f"{engine_labels[engine]} needs an API key. Add it in the field above or in .env.")
                else:
                    st.sidebar.error(str(exc))

    st.sidebar.markdown("---")
    st.sidebar.subheader("Instant demos")
    for video_id, title, topic, language in SAMPLE_CATALOG:
        if st.sidebar.button(f"{title}", use_container_width=True, key=f"sample-{video_id}"):
            set_active_result(load_sample(video_id))
        st.sidebar.caption(f"{topic} · {language}")

    st.sidebar.markdown("---")
    st.sidebar.caption("CLI is still available:")
    st.sidebar.code('lecture2graph "https://www.youtube.com/watch?v=VIDEO_ID"', language="bash")


def render_header(result: LectureGraphResult) -> None:
    stats = result.stats
    st.title("Understand any lecture instantly.")
    st.write(
        "Paste a YouTube lecture, extract the concepts, follow the prerequisite path, and jump back to the exact moments where each idea shows up."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Concepts", stats.concept_count)
    c2.metric("Dependencies", stats.edge_count)
    c3.metric("Learning steps", stats.learning_path_length)
    c4.metric("Language", result.video.source_language_label)

    st.caption(f"Video: {result.video.watch_url} · Engine: {result.video.engine.upper()}")


def render_graph_panel(result: LectureGraphResult) -> None:
    st.subheader("Interactive graph")
    html = load_graph_html(result)
    components.html(html, height=920, scrolling=True)


def render_concept_panel(result: LectureGraphResult) -> None:
    st.subheader("Concept explorer")
    options = concept_options(result)
    labels = list(options.keys())
    current_id = st.session_state.get("selected_concept_id")
    current_label = next((label for label, concept_id in options.items() if concept_id == current_id), labels[0] if labels else None)

    chosen_label = st.selectbox("Selected concept", options=labels, index=labels.index(current_label) if current_label in labels else 0)
    st.session_state["selected_concept_id"] = options[chosen_label]
    concept = selected_concept(result)
    if concept is None:
        st.info("No concepts found yet.")
        return

    st.markdown(f"### {concept.name}")
    st.write(concept.description)

    b1, b2, b3 = st.columns(3)
    b1.metric("Mentions", concept.mention_count)
    b2.metric("Prerequisites", len(concept.prerequisites))
    b3.metric("Unlocks", len(concept.dependents))

    with st.expander("Prerequisites", expanded=True):
        if concept.prerequisites:
            for item in concept.prerequisites:
                st.write(f"- {item.name}")
        else:
            st.caption("None")

    with st.expander("Unlocks", expanded=True):
        if concept.dependents:
            for item in concept.dependents:
                st.write(f"- {item.name}")
        else:
            st.caption("None")

    with st.expander("Timestamps", expanded=True):
        if concept.timestamps:
            for item in concept.timestamps:
                st.markdown(f"- [{item.label}]({item.url}) · `{item.source}`")
        else:
            st.caption("No timestamps captured.")


def render_learning_path(result: LectureGraphResult) -> None:
    st.subheader("Learning path")
    for step in result.learning_path:
        with st.container(border=True):
            st.caption(f"Step {step.step}")
            st.markdown(f"**{step.title}**")
            st.write(step.description)
            if step.timestamp_url:
                st.link_button("Jump to lecture moment", step.timestamp_url)


def render_transcripts(result: LectureGraphResult) -> None:
    st.subheader("Transcript")
    tab_original, tab_translated = st.tabs(["Original", "Translated"])

    with tab_original:
        transcript = result.transcripts.original or result.transcripts.translated
        for segment in transcript[:50]:
            st.markdown(f"**{segment.start:0.0f}s · {segment.source}**  \n{segment.text}")

    with tab_translated:
        for segment in result.transcripts.translated[:50]:
            st.markdown(f"**{segment.start:0.0f}s · {segment.source}**  \n{segment.text}")


def render_exports(result: LectureGraphResult) -> None:
    st.subheader("Exports")
    files = result_files(result)
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download graph.html", files["graph.html"], file_name="graph.html", mime="text/html", use_container_width=True)
    c2.download_button("Download notes.md", files["notes.md"], file_name="notes.md", mime="text/markdown", use_container_width=True)
    c3.download_button(
        "Download lecture2graph.json",
        files["lecture2graph.json"],
        file_name="lecture2graph.json",
        mime="application/json",
        use_container_width=True,
    )


def ensure_default_state() -> None:
    if "result" not in st.session_state:
        set_active_result(load_sample("XRcC7bAtL3c"))


def main() -> None:
    render_sidebar()
    ensure_default_state()
    result: LectureGraphResult = st.session_state["result"]

    render_header(result)

    left, right = st.columns([1.65, 1.0], gap="large")
    with left:
        render_graph_panel(result)
    with right:
        render_concept_panel(result)

    lower_left, lower_right = st.columns([1.1, 0.9], gap="large")
    with lower_left:
        render_learning_path(result)
    with lower_right:
        render_exports(result)

    render_transcripts(result)


if __name__ == "__main__":
    main()

