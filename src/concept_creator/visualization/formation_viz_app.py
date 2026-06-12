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

sys.path.insert(0, str(Path(__file__).parent))  # AppTest runs from elsewhere

import data
import plotting

st.set_page_config(page_title="Concept Formation Visualizer", layout="wide")
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
    threshold = st.number_input("Mismatch threshold", min_value=0.05,
                                max_value=1.0, value=0.35, step=0.05)

    if st.button("Run formation", disabled=choice is None, type="primary"):
        session_id = options[choice]
        out_path = data.OUTPUT_DIR / f"{session_id}_{int(time.time())}.pkl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with st.status(f"Running formation for {session_id}...",
                       expanded=True) as status:
            proc = data.launch_runner(session_id, steps_limit or None,
                                      threshold, out_path)
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("PROGRESS"):
                    status.update(label=f"{session_id}: {line.split('=')[-1]} steps")
                elif line.startswith("DONE"):
                    status.update(label=line, state="complete")
            rc = proc.wait()
        if rc != 0:
            st.error("Runner failed")
            with st.expander("stderr"):
                st.code(data.stderr_log_path(out_path).read_text()[-8000:])
        else:
            st.session_state["payload"] = data.load_payload(out_path)
            st.session_state["payload_path"] = str(out_path)

    payload = st.session_state.get("payload")
    if payload:
        meta = payload["meta"]
        st.divider()
        verdict_color = "green" if meta["verdict"] == "CLEAN" else "red"
        st.markdown(f"**Verdict:** :{verdict_color}[{meta['verdict']}]")
        st.markdown(f"mean_xy_width: `{meta['mean_xy_width']}`")
        st.markdown(f"duration: `{meta['duration_s']}s`  "
                    f"steps: `{len(payload['steps'])}`")
        if meta.get("skipped_images"):
            st.warning(f"Skipped: {', '.join(meta['skipped_images'])}")

# -------------------------------------------------------------------- main --
if not payload:
    st.info("Pick a session and click **Run formation**.")
    st.stop()

steps = payload["steps"]
events = payload["events"]

tab_steps, tab_ranges, tab_events, tab_inspect = st.tabs(
    ["Step viewer", "Range evolution", "Events", "Node inspector"]
)

with tab_steps:
    step_num = st.slider("Step", min_value=steps[0]["step"],
                         max_value=steps[-1]["step"],
                         value=steps[0]["step"]) if len(steps) > 1 else steps[0]["step"]
    step = next(s for s in steps if s["step"] == step_num)
    st.caption(step["description"])
    animate = st.toggle("Animate matching", value=False)
    step_merges = [e for e in events
                   if e.get("type") == "merge" and e.get("step") == step_num]
    st.plotly_chart(plotting.step_figure(step, step_merges, animate=animate),
                    use_container_width=True)

with tab_ranges:
    st.plotly_chart(plotting.range_evolution_figure(steps), use_container_width=True)

with tab_events:
    only_mismatch = st.checkbox("Mismatches only", value=False)
    scope_all = st.checkbox("All steps (uncheck = selected step)", value=False)

    def _filtered(event_type: str) -> pd.DataFrame:
        rows = [e for e in events if e.get("type") == event_type]
        if not scope_all:
            rows = [e for e in rows if e.get("step") == step_num]
        if only_mismatch:
            rows = [e for e in rows if e.get("mismatch")]
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
    final = steps[-1]["concept_after"]
    node_ids = [n["id"] for n in final["nodes"]]
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
