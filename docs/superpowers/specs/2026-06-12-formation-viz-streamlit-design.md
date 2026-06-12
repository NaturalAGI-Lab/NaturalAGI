# Design: Streamlit Concept-Formation Visualizer

**Date:** 2026-06-12
**Status:** Approved (design review 2026-06-12)
**Related:** `researches/concept_creator_bug_analysis.md` §3–§4 (probe suite, VisualGED decision), `src/concept_creator/probes/`

## Purpose

Interactive debugging tool for concept formation. The user uploads training
samples to Neo4j via `train_mnist(class_number, subclass, is_prepared_samples=True,
with_concept_creation=False)` — samples land under `session_id = "{class}_{subclass}"`
with no `concept_id`, untouched by the pipeline's concept creation. The app runs
formation on demand against that data and visualizes every merge step.

**Hard requirement — no code duplication:** the app imports the production
`concept_creator` code (`CriticalPointConceptService`) and the existing probe
instrumentation. Debugging edits happen in one place (the production source) and
are picked up by the app automatically.

## Architecture: fresh subprocess per run

Streamlit reruns its script on changes but never reloads imported modules
(`sys.modules` cache), so a naive in-process import would silently serve stale
formation code — the worst failure mode for a debug tool. Decision (user-approved):

```
Streamlit app (UI only, long-lived)
   │  click "Run formation"
   ▼
subprocess: formation_runner.py  ◀─ fresh import of concept_creator code EVERY run
   │  CriticalPointConceptService.create_concept_incrementally(debug_mode=True)
   │  + probes.instrumentation.attach_instrumentation (event stream)
   ▼
result pickle: plain dicts + nx node-link data ONLY (no concept_creator classes)
   │
   ▼
Streamlit renders Plotly views; result cached in st.session_state
```

- Subprocess = the venv interpreter (`natural-agi/bin/python`) with
  `PYTHONPATH=.:<repo>/common`, cwd `src/concept_creator` (same pattern as probes).
- Runner converts every `ConceptFormationStep` to
  `{step, description, image_id, concept_before, sample, concept_after}` where the
  graphs are `nx.node_link_data` dicts. The Streamlit process never imports or
  unpickles `concept_creator` classes — editing the service (even its dataclasses)
  cannot crash or stale-poison the UI.
- Runner streams `step i/N` progress to stdout; the app shows it via `st.status`.
- Interpreter startup (~1–2 s) is paid once per run; all UI interaction afterwards
  reads the cached payload.

## Files

New package `src/concept_creator/visualization/`:

| File | Responsibility |
|---|---|
| `formation_runner.py` | CLI: `--session <id>` (Neo4j) or `--samples-dir <dir>` (offline, reuses the probe's loader), `--steps`, `--mismatch-threshold`, `--out <pkl>`. Attaches instrumentation, runs formation `debug_mode=True`, writes the payload pickle. |
| `formation_viz_app.py` | Streamlit UI. Imports only `plotting.py` + `data.py` + stdlib/streamlit. |
| `plotting.py` | Plotly figure builders: 3-panel step figure (+ animation frames), range-evolution charts. |
| `data.py` | Neo4j session listing: distinct `session_id` with `concept_id IS NULL`, image counts. Subprocess launch + payload load helpers. |

- Makefile target `formation_viz`: `streamlit run` on **port 8502** (existing
  `dashboard` keeps 8501).
- Run payloads cached under `src/concept_creator/visualization/output/` (gitignored).

## Payload schema (runner → app)

```python
{
  "meta": {"session_id": str, "params": {...}, "duration_s": float,
            "created_at": str, "verdict": "CLEAN"|"SUSPECT",
            "mean_xy_width": float, "skipped_images": [str]},
  "steps": [
    {"step": int, "description": str, "image_id": str,
     "concept_before": node_link_dict, "sample": node_link_dict,
     "concept_after": node_link_dict}
  ],
  "events": [ ... ]   # FormationRecorder events verbatim (sync_pair,
                      # segment_match, start_point, id_collision, merge, ...)
}
```

`verdict` uses the probe rule: CLEAN iff no mismatch merges and
`mean_xy_width < 0.6`.

## UI

**Sidebar:** session picker (Neo4j query + refresh, shows image counts), optional
steps limit, mismatch threshold (default 0.35), **Run formation** button, last-run
metadata (duration, params, verdict).

**Main area — four tabs:**

1. **Step viewer** — step slider + the step's description
   (`Processing image 5/33: <id>` / `SKIPPED ...`). One Plotly figure, three
   panels: concept-before / sample / merged-after. Correspondence lines between
   concept and sample panels from the step's `sync_pair` events: gray = matched,
   **red = mismatch** (`distance > threshold`). Node hover: id, labels, all
   properties with ranges rendered `[min, max]`. Node positions = midpoint of the
   `normalized_x/y` range. Colors follow the probe palette (EndPoint red,
   StartPoint orange, Intersection/Corner green, interior gray).
   **Minimal matching animation:** a toggle that adds Plotly frames revealing
   correspondence lines one pair at a time in event order (the order pairs were
   recorded within the step), with Plotly's built-in play/pause buttons — pure
   client-side, no Streamlit reruns.
2. **Range evolution** — `mean_xy_width` per step (line chart with the 0.6
   SUSPECT threshold marked) + per-node width traces for the **top 5 widest
   final nodes**. Pinpoints which step exploded which node.
3. **Events** — tables scoped to the selected step (or all steps): sync pairs
   (node_c, node_i, distance, mismatch), segment matches (row_idx, best_idx,
   score, crossing, many_to_one), start-point picks. "Mismatches only" filter.
4. **Node inspector** — select a concept node → property ranges table +
   **widening history**: per property, the step/sample where the range widened,
   computed by diffing consecutive `concept_after` snapshots.

## Production change (single line)

`src/concept_creator/src/critical_point_concept_service.py:129` currently calls
`self.repository.remove_image_data(image_id)` when a sample's merge raises —
**even in debug mode** (CC-16 in the bug analysis). Repeated debug runs would
silently delete uploaded samples. Fix: gate it with `if not debug_mode:`.
Production pipeline behavior is unchanged (deletion still happens in normal mode);
debug runs become strictly read-only against Neo4j.

## Error handling

- No debug sessions found → message with the exact `train_mnist(...)` invocation
  to upload data.
- Runner subprocess non-zero exit → stderr shown in an expander; app keeps the
  previous run.
- Per-sample merge exception → step rendered with its SKIPPED description;
  skipped list in run metadata (sample data preserved thanks to the CC-16 fix).
- Neo4j unreachable → connection error with the DSN shown.

## Testing

Runner's `--samples-dir` offline mode enables Neo4j-free tests against the
existing fixtures (`probes/repro/sample_data/`):

- **Runner test:** offline run on `seven_flipped/` → payload has expected step
  count, 2 mismatch `sync_pair` events, verdict SUSPECT, and contains only plain
  dict/list/str/float types (no custom classes).
- **Plotting test:** 3-panel figure from that payload → expected trace counts,
  2 red correspondence lines, animation frame count == pair count.
- **Manual smoke:** live Neo4j session → full app walkthrough
  (`make formation_viz`).

## Out of scope

- GED/classification visualization (VisualGED's territory — see
  `researches/concept_creator_bug_analysis.md` §4).
- Editing samples or concepts from the app (strictly read-only).
- Comparing two formation runs side-by-side (possible later on top of cached
  payload pickles).
