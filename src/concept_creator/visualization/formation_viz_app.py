"""
formation_viz_app.py — Streamlit UI for concept-formation debugging.

Run via:  make formation_viz   (port 8502)

UI-only: imports plotting/data; concept_creator code runs ONLY inside the
formation_runner subprocess, so source edits there are picked up on every run.
"""
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent))  # AppTest runs from elsewhere

import data
import plotting

STEP_KEY = "formation_viz_step"


def _step_index(step_values: list[int]) -> int:
    current = st.session_state.get(STEP_KEY, step_values[0])
    if current not in step_values:
        st.session_state[STEP_KEY] = step_values[0]
        return 0
    return step_values.index(current)


def _shift_step(delta: int, step_values: list[int]) -> None:
    idx = _step_index(step_values)
    next_idx = max(0, min(len(step_values) - 1, idx + delta))
    st.session_state[STEP_KEY] = step_values[next_idx]


st.set_page_config(page_title="Concept Formation Visualizer", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background: #080c12;
    }
    [data-testid="stHeader"] {
        background: rgba(8, 12, 18, 0.86);
    }
    [data-testid="stSidebar"] {
        background: #232632;
        border-right: 1px solid #343846;
    }
    [data-testid="stSidebar"] hr {
        border-color: #454a58;
    }
    .stPlotlyChart {
        overflow: hidden;
        border: 1px solid #263241;
        border-radius: 8px;
        background: #0b1017;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #2a3442;
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Concept Formation Visualizer")

# ----------------------------------------------------------------- sidebar --
with st.sidebar:
    st.header("Run")
    try:
        sessions = data.list_debug_sessions()
    except Exception as exc:  # Neo4j down / unreachable
        sessions = []
        st.error(f"Neo4j unreachable at {data.NEO4J_DSN}: {exc}")

    if not sessions:
        st.info(
            "No debug sessions found. Upload samples with:\n\n"
            "`train_mnist(class_number=N, subclass=M, is_prepared_samples=True, "
            "with_concept_creation=False)`"
        )

    options = {f"{s['session_id']}  ({s['image_count']} images)": s["session_id"]
               for s in sessions}
    choice = st.selectbox("Session", list(options.keys())) if options else None
    steps_limit = st.number_input("Steps limit (0 = all)", min_value=0, value=0)

    if st.button("Run formation", disabled=choice is None, type="primary"):
        session_id = options[choice]
        out_path = data.OUTPUT_DIR / f"{session_id}_{int(time.time())}.pkl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with st.status(f"Running formation for {session_id}...",
                       expanded=True) as status:
            proc = data.launch_runner(session_id, steps_limit or None, out_path)
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("PROGRESS"):
                    status.update(label=f"{session_id}: {line.split('=')[-1]} steps")
                elif line.startswith("DONE"):
                    status.update(label=line, state="complete")
            rc = proc.wait()
        # The runner always writes a payload — even when formation throws, it
        # captures the steps up to and including the failing pair. Load whenever
        # the file exists; only fall back to "Runner failed" on a hard crash.
        loaded = False
        if out_path.exists():
            try:
                st.session_state["payload"] = data.load_payload(out_path)
                st.session_state["payload_path"] = str(out_path)
                st.session_state.pop(STEP_KEY, None)
                loaded = True
            except Exception as exc:
                st.error(f"Could not read runner output: {exc}")
        if not loaded:
            st.error("Runner failed")
            with st.expander("stderr"):
                st.code(data.stderr_log_path(out_path).read_text()[-8000:])

    payload = st.session_state.get("payload")
    if payload:
        meta = payload["meta"]
        st.divider()
        verdict_color = "green" if meta["verdict"] == "CLEAN" else "red"
        st.markdown(f"**Verdict:** :{verdict_color}[{meta['verdict']}]")
        st.markdown(f"mean_xy_width: `{meta['mean_xy_width']}`")
        st.markdown(f"duration: `{meta['duration_s']}s`  "
                    f"steps: `{len(payload['steps'])}`")

# -------------------------------------------------------------------- main --
if not payload:
    st.info("Pick a session and click **Run formation**.")
    st.stop()

if payload["meta"].get("is_error"):
    st.error(
        f"⚠️ Formation failed: {payload['meta'].get('error_message', 'unknown error')}\n\n"
        f"Showing all {len(payload['steps'])} steps up to and including the failing "
        "pair. On the last step, **Sample** is the image that broke formation and "
        "**Merged result** is empty."
    )

steps = payload["steps"]
if not steps:
    st.warning("No formation steps were produced before the failure.")
    st.stop()
events = payload["events"]
step_values = [s["step"] for s in steps]
step_by_num = {s["step"]: s for s in steps}
if STEP_KEY not in st.session_state or st.session_state[STEP_KEY] not in step_values:
    st.session_state[STEP_KEY] = step_values[0]

tab_steps, tab_ranges, tab_events, tab_inspect = st.tabs(
    ["Step viewer", "Range evolution", "Events", "Node inspector"]
)

with tab_steps:
    current_idx = _step_index(step_values)
    prev_col, next_col, _ = st.columns([0.7, 0.7, 5.6])
    prev_col.button("Prev", disabled=current_idx == 0,
                    on_click=_shift_step, args=(-1, step_values))
    next_col.button("Next", disabled=current_idx == len(step_values) - 1,
                    on_click=_shift_step, args=(1, step_values))

    if len(step_values) > 1:
        step_num = st.select_slider("Step", options=step_values, key=STEP_KEY)
    else:
        step_num = step_values[0]

    step = step_by_num[step_num]
    st.caption(step["description"])
    animate = st.toggle("Animate matching", value=False)
    st.caption("💡 Click any node to copy its id to the clipboard.")
    step_merges = [e for e in events
                   if e.get("type") == "merge" and e.get("step") == step_num]
    fig = plotting.step_figure(step, step_merges, animate=animate)
    # Render through components.html (not st.plotly_chart) so the embedded
    # click-to-copy handler in figure_html runs — it needs a live JS context.
    components.html(
        plotting.figure_html(fig, auto_play=animate),
        height=int(fig.layout.height or 560) + 8,
        scrolling=False,
    )

with tab_ranges:
    st.plotly_chart(plotting.range_evolution_figure(steps), use_container_width=True)

with tab_events:
    scope_all = st.checkbox("All steps (uncheck = selected step)", value=False)

    def _filtered(event_type: str) -> pd.DataFrame:
        rows = [e for e in events if e.get("type") == event_type]
        if not scope_all:
            rows = [e for e in rows if e.get("step") == step_num]
        return pd.DataFrame(rows)

    st.subheader("Merges")
    st.dataframe(_filtered("merge"), use_container_width=True)
    st.subheader("Sync pairs")
    st.dataframe(_filtered("sync_pair"), use_container_width=True)
    st.subheader("Segment matches")
    st.dataframe(_filtered("segment_match"), use_container_width=True)
    st.subheader("Start points")
    st.dataframe(pd.DataFrame([e for e in events
                               if e.get("type") == "start_point"]), use_container_width=True)

with tab_inspect:
    # A failed run's last step has an empty concept_after; inspect the last step
    # that actually produced a concept.
    final = next((s["concept_after"] for s in reversed(steps)
                  if s["concept_after"]["nodes"]), steps[-1]["concept_after"])
    node_ids = [n["id"] for n in final["nodes"]]
    if not node_ids:
        st.caption("No concept nodes to inspect (formation produced no concept).")
    else:
        node_id = st.selectbox("Concept node", node_ids)
        node = next(n for n in final["nodes"] if n["id"] == node_id)

        rows = []
        for prop, value in node.items():
            if prop in ("id", "labels"):
                continue
            if isinstance(value, dict) and "min" in value:
                rows.append({"property": prop, "min": value["min"],
                             "max": value["max"],
                             "width": plotting.range_width(value)})
            else:
                rows.append({"property": prop, "min": value, "max": value, "width": 0.0})
        st.subheader(f"Node {node_id} — {', '.join(node.get('labels', []))}")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.subheader("Widening history")
        hist = plotting.widening_history(steps, node_id)
        if hist:
            st.dataframe(pd.DataFrame(hist), use_container_width=True)
        else:
            st.caption("This node's ranges never widened.")
