# Error Anatomy and Stability of Structural Concept Formation (2026)

Solo-author paper (M. Lapin), deadline 2026-08-15. Venue: **AIS (Advanced
Information Systems)**, NTU "KhPI", ISSN 2522-9052.

The submission artifact is `ais/lapin_ais_2026.docx` (with a `.doc` copy, the
format the journal's author page names) — 10 pages, A4, Times New Roman 10 pt,
two 8.0 cm columns. `main.tex` is the archival LaTeX version in IEEEtran
layout, 9 pages; both carry the same text.

## Scope

1. **Anatomy of the dominant 2→7 error**: stage-localized root cause — lower-loop
   hole absent in the binarized mask 110/111 (fixed threshold 110), lost at
   GNG+RDP vectorization 1/111, reduction 0/111; pre-filter ablation (2_2 wins
   0/111, similarity 0.0 via intersection gate); cost implementation verified
   consistent by replay (13/13 self-recognition); the similarity function's
   suitability is stated as the open downstream question.
2. **Five stability studies**: S1 dataset variants, S2 presentation order, S3
   sample count (offline), S5 reduction convergence, S6 compression.
   Augmentation (S4) and per-sample-count downstream accuracy are declared
   future work (require destructive retrains).

## Data provenance

Numbers come from committed run artifacts (`experiments/run_20260630_235356/`),
the supervisor experiments notebook caches
(`src/training/training_results/formation_probes/`), the dataset-variant
run exports (`src/training/training_results/run_20260717_{161201,162928,180330}/`),
and the 2026-08-01 meeting evidence CSVs (PhD vault,
`raw/evidence/2026-08-01_blue_remarks/`). No values re-derived by hand. All 17
reference DOIs were checked against Crossref on 2026-08-14.

## Building the AIS submission

```bash
.venv/bin/python papers/concept_stability_2026/ais/build_docx.py
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless \
    --convert-to pdf --outdir papers/concept_stability_2026/ais \
    papers/concept_stability_2026/ais/lapin_ais_2026.docx
```

Text lives in `ais/content.py`, layout in `ais/build_docx.py`, and the measured
journal specification in `journal_rules/ais_layout.md`. Regenerating the `.doc`
copy uses the same LibreOffice call with `--convert-to "doc:MS Word 97"`.

## Building the LaTeX archive

```bash
make build   # → build/main.pdf
make clean
```

## Figures

All figures are English. Regenerate with:

```bash
.venv/bin/python papers/concept_stability_2026/render_figures.py
```

Triptychs need Neo4j up with the baseline image graphs; the rest renders
offline from probe caches. Host venv needs `scikit-image==0.26.0`
(production image version) for the construction figure. Every figure clears
300 dpi at the width it is placed.

## Author decisions still open

- **UDC `004.93'1:004.932:004.032.26`** covers pattern recognition, image
  analysis, and neural networks. UDC assignment normally comes from the KhPI
  library — confirm before submitting.
- **Received / accepted dates** are placeholders (`__.__.2026`); the editor
  fills them, and the DOI line is omitted for the same reason.
- **Reference recency**: 7 of 17 sources are within 10 years, against the
  author page's "past 10 years" wording. The journal applies it loosely — its
  own 2025 article cites Landauer 1961 — and the older entries here are the
  foundational GED, thinning, and RDP papers. A reviewer may still ask.
- **Abstract length** is 2,441 characters. AIS states no limit; its printed
  abstracts run shorter, around 1,900.
