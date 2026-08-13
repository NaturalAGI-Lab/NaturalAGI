# Error Anatomy and Stability of Structural Concept Formation (2026)

Solo-author paper (M. Lapin), deadline 2026-08-15. Venue: AIS (Advanced
Information Systems) journal, Harvard citations; the IEEEtran layout is
the interim working format (AIS itself takes Word .doc, Times 10 pt,
minimum 4 full pages, no stated maximum). Current build: 9 pages, no open
TODOs in the text.

## Scope

1. **Anatomy of the dominant 2→7 error** (Section IV): stage-localized
   root cause — lower-loop hole absent in the binarized mask 110/111
   (fixed threshold 110), lost at GNG+RDP vectorization 1/111, reduction
   0/111; pre-filter ablation (2_2 wins 0/111, similarity 0.0 via
   intersection gate); cost implementation verified consistent by replay
   (13/13 self-recognition); the similarity function's suitability is
   stated as the open downstream question.
2. **Five stability studies** (Section V): S1 dataset variants, S2
   presentation order, S3 sample count (offline), S5 reduction
   convergence, S6 compression. Augmentation (S4) and per-sample-count
   downstream accuracy are declared future work (require destructive
   retrains).

## Data provenance

Numbers come from committed run artifacts (`experiments/run_20260630_235356/`),
the supervisor experiments notebook caches
(`src/training/training_results/formation_probes/`), the dataset-variant
run exports (`src/training/training_results/run_20260717_{161201,162928,180330}/`),
and the 2026-08-01 meeting evidence CSVs (PhD vault,
`raw/evidence/2026-08-01_blue_remarks/`). No values re-derived by hand.

## Figures

All figures are English. Regenerate with:

```bash
.venv/bin/python papers/concept_stability_2026/render_figures.py
```

Triptychs need Neo4j up with the baseline image graphs; the rest renders
offline from probe caches. Host venv needs `scikit-image==0.26.0`
(production image version) for the construction figure.

## Remaining before submission

- Convert to AIS requirements (Harvard citations, class/author block/page budget)
- Open the repository read-only and link it from the paper

## Build

```bash
make build   # → build/main.pdf
make clean
```
