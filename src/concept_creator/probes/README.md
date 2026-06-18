# Concept-Formation Probes

Instrumentation suite for `src/critical_point_concept_service.py`.  All probe
code lives under `probes/`.  Production source files are never modified.

Run everything from `src/concept_creator/` with the project venv:

```bash
cd /Users/mlapin/Development/personal/NaturalAGI/src/concept_creator
export PYTHONPATH=.:/Users/mlapin/Development/personal/NaturalAGI/common
VENV=/Users/mlapin/Development/personal/NaturalAGI/natural-agi/bin/python
```

---

## Scripts

### probe_concept_formation.py

Main probe CLI.  Two modes:

**Neo4j mode** (reads live data):
```bash
$VENV probes/probe_concept_formation.py \
    --session <session_id> \
    [--concept-id probe] \
    [--steps 5] \
    [--out probes/output/my_run] \
    [--viz] \
    [--mismatch-threshold 0.35]
```

Set env vars for Neo4j credentials (defaults shown):
```
NEO4J_DSN=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=111122223333
```

**Offline mode** (no Neo4j; reads node-link JSON graphs):
```bash
$VENV probes/probe_concept_formation.py \
    --samples-dir probes/repro/sample_data/seven_clean \
    --concept-id seven_clean \
    --viz
```

**Output** (written to `--out` directory, default `probes/output/<concept-id>/`):
- `events.jsonl` — all instrumentation events (one JSON object per line)
- `range_evolution.csv` — per-step per-node range widths
- `summary.json` — aggregate metrics
- `report.md` — human-readable report with verdict `CLEAN` or `SUSPECT`
- `step_NNN.png` — one 3-panel figure per step (only with `--viz`)

**Verdict** is `CLEAN` when:
- zero mismatch events AND
- `mean_xy_width` of the final concept < 0.6

---

### verify_concept_ranges.py

Prints a per-node width table and exits 1 when `mean_xy_width > --max-width`.

```bash
# From Neo4j:
$VENV probes/verify_concept_ranges.py --concept-id 7_1

# From a probe run summary:
$VENV probes/verify_concept_ranges.py \
    --summary probes/output/seven_flipped/summary.json \
    --max-width 0.6
```

Useful as an integration-test assertion in CI:
```bash
$VENV probes/verify_concept_ranges.py --summary ... || exit 1
```

---

### test_probe_selfcheck.py

Self-test (no pytest required).  Builds synthetic 7-like graphs under
`probes/repro/sample_data/` and verifies:
- Clean set → zero mismatches, `mean_xy_width < 0.6`
- Flipped set → at least one mismatch, `mean_xy_width(flipped) > mean_xy_width(clean)`

```bash
$VENV probes/test_probe_selfcheck.py
```

---

## JSONL Event Schema

Each line in `events.jsonl` is a JSON object with a `"type"` field.

### `merge`
Fired on every `PropertyProcessor.process_properties` call.

| field | type | description |
|---|---|---|
| `type` | `"merge"` | |
| `step` | int | Formation step index (1 = initial concept) |
| `g_labels` | list[str] | Labels of the concept/template node |
| `h_labels` | list[str] | Labels of the sample/other node |
| `g_x`, `g_y` | float | Normalised coords of the concept node |
| `h_x`, `h_y` | float | Normalised coords of the sample node |
| `distance` | float | Euclidean distance between the two positions |
| `merged_width_normalized_x` | float | Range width of merged `normalized_x` |
| `merged_width_normalized_y` | float | Range width of merged `normalized_y` |
| `mismatch` | bool | `True` when `distance > mismatch_threshold` |

### `sync_pair`
Fired for every `(node_c, node_i)` pair in the sync list returned by
`SyncedTraversalGenerator.generate_synced_traversal`.

| field | type | description |
|---|---|---|
| `type` | `"sync_pair"` | |
| `step` | int | |
| `node_c`, `node_i` | any | Node IDs in concept/image graphs |
| `c_x`, `c_y` | float | Concept node coordinates |
| `i_x`, `i_y` | float | Image node coordinates |
| `c_labels`, `i_labels` | list[str] | Labels |
| `distance` | float | Spatial distance |
| `mismatch` | bool | `True` when distance > threshold |

### `sync_summary`
One per `generate_synced_traversal` call.

| field | type | description |
|---|---|---|
| `type` | `"sync_summary"` | |
| `step` | int | |
| `num_paths` | int | Paths in sync list |
| `num_pairs` | int | Total (node_c, node_i) pairs |
| `num_mismatches` | int | Pairs with mismatch flag |

### `segment_match`
Fired once per aligned pair returned by `align_monotone_one_to_one` (monotone 1:1).

| field | type | description |
|---|---|---|
| `type` | `"segment_match"` | |
| `step` | int | |
| `row_idx` | int | Concept-side (A) node index |
| `best_idx` | int | Matched image-side (B) node index |
| `best_score` | float | |
| `row_scores` | list[float] | All column scores for this row |
| `crossing` | bool | Always `False` (alignment is monotone by construction) |
| `many_to_one` | bool | Always `False` (alignment is 1:1 by construction) |

### `start_point`
Fired in `StartPointModifier.change_start_point` BEFORE labels are cleared.

| field | type | description |
|---|---|---|
| `type` | `"start_point"` | |
| `step` | int | |
| `graph_id` | str | From `graph.graph["graph_id"]` |
| `node_id` | any | Node being relabeled |
| `normalized_x`, `normalized_y` | float | Coordinates |
| `original_labels` | list[str] | Labels BEFORE the clear+relabel |
| `degree` | int | Node degree in the graph |

### `id_collision`
Fired when the logger for `SyncedGraphMinorFinder` emits the "already exists
in result graph" warning.

| field | type | description |
|---|---|---|
| `type` | `"id_collision"` | |
| `step` | int | |
| `message` | str | Full log message |

---

## summary.json Fields

| field | description |
|---|---|
| `total_merges` | Total `process_properties` calls |
| `mismatch_merges` | Calls where `distance > threshold` |
| `mismatch_rate` | `mismatch_merges / total_merges` |
| `distance_histogram` | Counts in buckets `0.0-0.1`, `0.1-0.2`, …, `>1.0` |
| `crossing_count` | Total crossing flags across all segment_match events |
| `many_to_one_count` | Total many-to-one flags |
| `id_collisions` | Count of id_collision events |
| `sync_mismatches` | sync_pair events with mismatch=True |
| `per_step_merges` | `{step: count}` |
| `per_step_mismatches` | `{step: count}` |
| `start_point_table` | All start_point events |
| `per_property_max_width` | `{property: max_width_seen}` across all merge events |
| `sync_summaries` | All sync_summary events |
| `mean_xy_width` | Mean of `(width_x + width_y) / 2` over final concept nodes |
| `step_node_edge_counts` | `[{step, nodes, edges}]` |

---

## Flags

| flag | default | description |
|---|---|---|
| `--mismatch-threshold` | `0.35` | Distance above which a pairing is flagged |
| `--max-width` (verify) | `0.6` | mean_xy_width threshold for exit code |
| `--viz` | off | Render per-step 3-panel PNG figures |
| `--steps N` | all | Stop after N formation steps |
