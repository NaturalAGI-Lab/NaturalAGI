# Error Anatomy and Stability of Structural Concept Formation (2026)

**Status: DRAFT** — venue not yet selected; IEEEtran conference layout used
as a neutral default (switching class affects only preamble + author block).

## Scope

Answers the supervisor's two questions against the 91.13% baseline
(`experiments/run_20260630_235356/`):

1. **Why do 2s fall into 7s** despite the WTA design favoring the more
   complex concept — Section III (post-mortem of all 111 errors, exemplar
   figures: image → construction stages → graph → concepts).
2. **Six stability studies** — Section IV:
   - S1 dataset variants (10k full / 60k train / 70k aggregate)
   - S2 sample-presentation order
   - S3 sample count
   - S4 augmentation — **results pending Tier C retrains** (red TODO)
   - S5 reduction convergence
   - S6 concept parameters & compression

## Data provenance

Every number comes from committed run artifacts or the supervisor
experiments notebook (`src/training/supervisor_experiments.ipynb`,
kernel `natural-agi`). No values were re-derived by hand.
Figures are copies of the notebook outputs (see `figures/`).

## Open TODOs (marked in red in the PDF)

- S4 augmentation table (notebook Section 6, Tier C retrain required)
- S3 downstream accuracy per sample-count condition (notebook Section 7)
- **Regenerate Figures 2–4 with English panel titles** — current PNGs are
  notebook outputs with Ukrainian labels («Стадії побудови графа»,
  «Оригінал», «Бінаризація» etc.); re-run post-mortem figure cells with
  English label strings
- Venue selection → adjust class/author block/page budget
- Related-work pass (grounding via NotebookLM + arXiv before submission)

## Build

```bash
make build   # → build/main.pdf
make clean
```
