# ITSSI 2026 — Figures Source Tree

> Editor's request (2026-05-12): submit all schematic figures **in Visio source form** in addition to the PNG renders.

## Journal rule (verbatim)

`journal_rules/article_requirements_EN.md:35` / `author_guidelines.md:36`:

> Figures should be created in **Visio** **and/or** submitted in `.jpg, .jpeg, .png` (no less than 300 dpi).

So PNG ≥300 dpi alone formally satisfies the requirement; the editor's ask for Visio is a separate preference toward editable vector source files for typesetting.

## What we deliver

We have no Microsoft Visio on macOS (Microsoft has not shipped a Mac build since 2010). draw.io is the standard substitute, but with one important caveat: **draw.io is a one-way bridge** to Visio — it can import `.vsdx` files but **cannot export to `.vsdx` in any version (desktop or web)**. Therefore the deliverable for the editor is the **vector SVG** instead, which Visio 2016+ imports natively (Insert → Pictures → choose `.svg` → right-click → "Convert to Microsoft Office drawing"). If the editor specifically demands `.vsdx`, the SVG can be converted via a one-off online tool — see "Optional: SVG → VSDX conversion" below.

| Figure | Type | Vector source | Vector deliverable for editor | Final PNG | Why this choice |
|---|---|---|---|---|---|
| **Fig 1 — Pipeline** | block-flow schematic | `fig_1_pipeline.drawio` | `fig_1_pipeline.svg` | `fig_1_pipeline.png` (2700×… ≥300 dpi) | Pure schematic — vector is the natural medium. |
| **Fig 2 — Digit 7 + graph** | hybrid (raster + graph) | `fig_2_digit7_graph.drawio` (graph half only) + `digit7_sample.png` (raster half) | `fig_2_digit7_graph.svg` (graph half) + `digit7_sample.png` (raster) | `fig_2_digit7_graph.png` (composed via PIL/matplotlib) | The MNIST raster is irreducibly bitmap; the vector graph half is the editable portion. |
| **Fig 3 — Concept 7_1** | graph schematic | `fig_3_concept_7_1.drawio` | `fig_3_concept_7_1.svg` | `fig_3_concept_7_1.png` | Pure graph diagram, plotted from `experiments/run_20260427_144233/concept_graphs.json` node coordinates. |
| **Fig 4 — Confusion matrix** | data heatmap (10 classes + DLQ) | **none — keep PNG** | **none — keep PNG** | `fig_4_confusion_matrix.png` (~2435×2070, ~515 dpi at 4-inch height) | Heatmap is rendered from per-image classification results. A vector schematic is the wrong abstraction, just as Excel charts are never asked to be redrawn as schematics. Journal rule explicitly permits PNG ≥300 dpi. |

## How to regenerate the vector SVG sources

draw.io CLI exports SVG natively with embedded fonts and (where applicable) embedded raster sub-images so the file is self-contained:

```bash
cd papers/itssi_paper_2026/figures

/Applications/draw.io.app/Contents/MacOS/draw.io -x -f svg -e \
  --embed-svg-images --embed-svg-fonts true -b 10 \
  -o fig_1_pipeline.svg fig_1_pipeline.drawio

/Applications/draw.io.app/Contents/MacOS/draw.io -x -f svg -e \
  --embed-svg-images --embed-svg-fonts true -b 20 \
  -o fig_3_concept_7_1.svg fig_3_concept_7_1.drawio

/Applications/draw.io.app/Contents/MacOS/draw.io -x -f svg -e \
  --embed-svg-images --embed-svg-fonts true -b 20 \
  -o fig_2_digit7_graph.svg fig_2_digit7_graph.drawio
```

Flags:
- `-e` embeds the original `.drawio` XML inside the SVG so editors who open the SVG in draw.io recover the editable diagram.
- `--embed-svg-fonts true` inlines fonts so the SVG renders identically on machines without Times New Roman / Courier New.
- `--embed-svg-images` inlines any raster sub-images (not needed for fig 1 and 3, included for safety).

## Optional: SVG → VSDX conversion (if the editor specifically rejects SVG)

draw.io itself cannot produce `.vsdx`. Four ways to get there, in order of practicality:

1. **`Convert-SvgToVsdx.ps1` on any Windows + Visio machine** — checked into this folder. Run from this directory:
   ```powershell
   # default: converts the three figure SVGs in current folder
   .\Convert-SvgToVsdx.ps1

   # explicit list:
   .\Convert-SvgToVsdx.ps1 -Files fig_1_pipeline.svg, fig_3_concept_7_1.svg

   # every *.svg in current folder:
   .\Convert-SvgToVsdx.ps1 -All
   ```
   Same approach as `deonvz/ConvertSVGtoVisio` (drive Visio's own SVG importer over COM) but without the C# project or `.msi` installer. Requires Microsoft Visio (any edition since 2016) on a Windows machine. Run it on Windows, copy the resulting `.vsdx` files back into this folder. Cannot run on macOS — `Visio.Application` COM server is Windows-only. Full header docs inside the script (`Get-Help .\Convert-SvgToVsdx.ps1 -Full`).
2. **Microsoft Visio for the web** (Office 365 with Visio Plan 1, ≈ 5 USD / month) — open each `.svg` directly, *Save As* `.vsdx`. Same conversion engine, just clicked through the browser.
3. **CloudConvert / Aspose Diagrams web app** — upload `.svg`, download `.vsdx`. Free for small one-off conversions. *Warning:* these tools upload the file to a remote server. Our paper figures are not confidential, but verify for future use.
4. **`deonvz/ConvertSVGtoVisio` itself** — same Windows + Visio prerequisite as option 1, plus needs the C# build / installer. Use it only if you specifically want the GUI for batch jobs across many folders.

In practice, the `.svg` itself is usually accepted by editorial offices — it is a more universal vector format than `.vsdx` and is recognised by Adobe Illustrator, Inkscape, LibreOffice Draw, Affinity Designer, and Visio (via Insert → Pictures since Visio 2016). The journal's article-requirements text says "created in Visio" but never specifies `.vsdx`. So start with `.svg`; only fall back to `.vsdx` if the editor explicitly complains.

## How to regenerate the PNGs

The PNG renders are built deterministically from the `.drawio` sources via the desktop CLI:

```bash
cd papers/itssi_paper_2026/figures

# Fig 1
/Applications/draw.io.app/Contents/MacOS/draw.io \
  -x -f png -e -b 10 --width 2700 -o fig_1_pipeline.png fig_1_pipeline.drawio

# Fig 3
/Applications/draw.io.app/Contents/MacOS/draw.io \
  -x -f png -e -b 20 --width 2400 -o fig_3_concept_7_1.png fig_3_concept_7_1.drawio

# Fig 2 (hybrid — needs two steps)
/Applications/draw.io.app/Contents/MacOS/draw.io \
  -x -f png -b 20 --width 1700 -o /tmp/fig_2_graph_half_clean.png fig_2_digit7_graph.drawio
../../../natural-agi/bin/python compose_fig_2.py     # combines digit7_sample.png + /tmp graph half
```

The `-e` flag embeds the diagram XML inside the PNG (so the PNG itself is round-trippable back to `.drawio`). For the assembly stage in Fig 2 we omit `-e` because PIL/matplotlib cannot parse the embedded-XML PNG chunks.

Fig 4 is regenerated from the run artefacts:

```bash
# from the project root
natural-agi/bin/python src/training/evaluation/build_confusion_matrix.py \
  --run experiments/run_20260427_144233 \
  --out papers/itssi_paper_2026/figures/fig_4_confusion_matrix.png
```

## Coordinate system used in Fig 2 and Fig 3

Node positions come from `experiments/run_20260427_144233/concept_graphs.json["7_1"]`. The stored `normalized_x` / `normalized_y` are centred image coordinates in `[−1, +1]` where positive Y means "down on the page" (image convention, not Cartesian). The drawio canvas is laid out in raw pixel coordinates with the same Y-down orientation, so no inversion is needed — points with larger `normalized_y` sit lower in the diagram.

## Reference: concept 7_1 (5 nodes, 4 edges)

| Idx | Label | Type | `(x, y)` | Diagnostic |
|---|---|---|---|---|
| 0 | StartPoint | Point | `(−0.40, −0.50)` | `is_endpoint = 1` |
| 1 | CornerPoint | Point | `(+0.57, −0.63)` | `is_corner = 1` (range center 0.67) |
| 2 | EndPoint | Point | `(−0.03, +0.80)` | `is_endpoint = 1` |
| 3 | HorizontalVector | Vector | `(+0.07, −0.77)` | `angle_with_ox` center = +0.06 |
| 4 | Vector | Vector | `(+0.33, −0.03)` | `angle_with_ox` center = +0.59 |

Edges (bipartite, Point↔Vector only): `0—3, 1—3, 1—4, 2—4`.

Topology resembles the silhouette of digit "7": horizontal bar Start–HVec–Corner across the top, diagonal stroke Corner–Vec–End down to the lower-left tip.
