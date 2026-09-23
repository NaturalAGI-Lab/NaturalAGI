# ITSSI 2026 rework — plan

Rework of the rejected IEEE KhPI Week 2026 paper into a Ukrainian single-author ITSSI submission.
Author: Лапін Микита Олексійович (ORCID 0009-0003-6307-1172, Scopus 60171161300), НТУ «ХПІ», каф. САІТ.
All numbers from `experiments/run_20260630_235356/` (91.13% baseline). No pipeline runs.

## Title / abstract / keywords (closes remark 5)

- **Title (UA):** «Пояснюване розпізнавання рукописних цифр на основі графових концептів-атракторів, сформованих з малої кількості прикладів» — no abbreviations, no "competitive" framing, matches content.
- **Title (EN):** "Explainable handwritten digit recognition based on graph concept attractors formed from a small number of examples".
- **Abstract:** structured Предмет/Мета/Завдання/Методи/Результати/Висновки, 1900–2200 chars (counted mechanically), UA at front + EN at end per ITSSI layout for Ukrainian submissions.
- **Keywords (≤10, `;`-separated):** пояснюваний штучний інтелект; графове подання зображень; концепт-атрактор; структурна редукція; відстань редагування графів; скелетизація; розпізнавання рукописних цифр; навчання з малої кількості прикладів. "Artificial neural networks" dropped (reviewer #2).

## Section outline → sources

ITSSI fixed structure. Prose written fresh in Ukrainian (uniqueness ≥75% vs the published 2025 LNCS text), not translated.

| # | Section | Content | Sources |
|---|---|---|---|
| 1 | Вступ | Opaque pipelines, post-hoc XAI fragility; structure as the carrier of explanation; the project's recorded position: scientific level, no competition with neural networks, ceiling = human ~97% on MNIST | khpi content.py ideas (rewritten); vault `argument.md` (position quote) |
| 2 | Аналіз джерел та постановка проблеми | LIME/SHAP + adversarial manipulation; graph-based/structural shape representations; GED; few-shot (ProtoNet, MAML — cited as context, no comparison claims); neuro-symbolic; non-backprop (Forward-Forward); gap statement | khpi refs + concept_stability verified bib |
| 3 | Мета і завдання дослідження | Мета: показати, що графове формування концептів без зворотного поширення дає пояснюване розпізнавання; завдання: подання, формування, класифікація, оцінка на MNIST, демонстрація пояснюваності трасуванням рішення, вимірювання обчислювальної вартості | new |
| 4 | Матеріали та методи | Bipartite Point/Vector graphs, attributes, normalization; pipeline (binarization θ=110 → thinning → GNG → RDP ε=4.55 → graph); concept formation via reduction (3 strategies, interval generalization, stopping rule «концепт перестає змінюватись»); **sample-selection policy + justification (closes remark 4)**: 76 unique samples, 3–9 per concept (from `f34b049:datasets.zip`), chosen least-distorted/gap-free, justification = a correctly-classified instance carries the structural features of its class; sensitivity to the choice not measured — stated; ~10 augmented variants per original (805 images), ±10°/translation; GED classification: cost ladder 0/0.25/0.5/0.8/1.0/6.0, 13 features, diagnostic weights 1/(width+ε), ε=0.1, similarity = 1 − cost/(cost+max(n₁,n₂)), complexity pre-filter, WTA adjusted = sim + 0.10·log₂C, **ged_timeout = 5 s** (not 15) | run_config.json; vault concept-formation.md; CLAUDE.md scoring facts |
| 5 | Результати дослідження | **Completeness filter in body text (closes remark 2)**: 8,707 of 10,000 (1,293 = 12.9% excluded), per-class skew table (class 8: 582 = 51.6% of class 1's 1,129), modality defence (broken contours → associative recognition, a different mechanism), stated consequence: the headline number is conditional on the filter. Headline: 91.13% accuracy / 91.92 precision / 91.13 recall / 91.34 F1 on 8,685 (22 DLQ = 0.25%). Per-class table. Confusion structure (2→7 = 111, 4→7 = 62, 2→6 = 57 …). **Worked trace (closes remark 3)**: `mnist_test_2_00766` — image → skeleton graph → competitors → `7_1` wins 0.8317 vs `2_1` 0.7300; three out-of-interval features (`distance_to_centroid`, `normalized_x`, `length_ratio_to_max`, penalties 1.01/1.10/1.30); `2_2` (complexity 24) pre-filtered at input complexity 21; the decision read off the graph, incl. why the error happens. **Inference cost (closes remark 1)**: measured — whole run 575 s for 8,707 images (≈66 ms/image at 4/4/16 service parallelism); per-stage medians from the profiling column (skel 52.8 ms, contour 211.5 ms, classification stage 167.1 ms, max 1.41 s; profiled subset = misclassified images, stated); 5 s deadline never reached | run artefacts; vault 2-to-7-confusion.md; timing-scout findings |
| 6 | Обговорення результатів | What the trace shows about intrinsic explainability (decision = navigable graph object, errors diagnosed mechanistically); limitations honestly: filter-conditional metric, NP-hard GED with measured (not asserted) cost, rotation range ±10°, contour-only; applications: domains needing traceable decisions | vault argument.md; discussion rewritten |
| 7 | Висновки | Contribution restated without "competitive"; numbers; future work: associative recognition for broken contours, measured per-comparison timing, sensitivity study of sample choice | new |
| — | Декларації | Конфлікт інтересів (немає), Фінансування (без підтримки), Доступність даних, **Використання ШІ — TODO placeholder for the author** | ITSSI rules |
| — | References | Harvard BSI, Latin, quotas below | see below |
| — | Відомості про автора | UA + EN, degree/position, ORCID, Scopus ID, phone = TODO | canonical IDs |

## Reference list plan (closes remark 6)

~20–22 entries. Verified DOIs mined from `papers/concept_stability_2026/references.bib` (checked vs Crossref 14 Aug); the rest verified via Crossref before drafting. The mis-matched `liu2023 MATA` citation from the KhPI list is dropped.

Core: Ribeiro 2016 (LIME), Lundberg 2017 (SHAP), Slack 2020, Hooshyar 2024, Rajabi 2024, Rudin 2019, Han 2022 (Vision GNN), Chatbri 2016, Shen 2016, Conte 2004, Riesen 2009, Wang 2021 (GED embedding), Snell 2017, Finn 2017, Lake 2015, Nawaz 2025, Hinton 2022 (Forward-Forward), LeCun 1998, Fritzke 1995 (GNG, no DOI — the one allowed gap), Zhang & Suen 1984, Douglas & Peucker 1973.
Self (≤30%): Parzhyn 2025 (arXiv Architecture), Parzhyn/Lapin/Bokhan 2025 (AIS), Parzhyn 2022 (KhPI Week), Lapin 2025 (АСУ) → 4 of ~22 ≈ 18%.

Quota targets: total ≥15 ✓; DOI ≥90% (≤2 without); Scopus/WoS ≥60%; foreign English ≥40%; recent 2022+ ≥30%; self ≤30%. Measured values go into SUBMISSION_CHECKLIST.md.

## Figures & tables (≤3 pages combined)

- Fig 1: pipeline scheme, rendered ≥300 dpi, UA labels.
- Fig 2: worked-trace figure for `2_00766` (construction stages / triptych from vault evidence; UA caption).
- Fig 3: confusion matrix re-rendered with UA labels from `incorrect_results.csv` + per-class support (diagonal derivable).
- T1: per-class support incl. exclusion share; T2: per-class precision/recall/F1; T3: per-feature costs of the worked trace; (overall metrics in-text).

## Toolchain

Clone `papers/itssi_paper_2026/` machinery: `generate_paper.py` (10pt TNR, OMML math via pandoc, declarations, UA+EN author info), `Makefile`, `render_figures.py`. `content.py` holds Ukrainian text directly (no make_ua_version step). Build → LibreOffice PDF → read pages → iterate.

## Checklist

- [x] Read reviews, content.py, ITSSI rules, vault, baseline artefacts
- [x] Timing data located (measured, on disk)
- [x] Training-set counts extracted from `f34b049:datasets.zip`
- [ ] Gate 2: outline approved by team lead
- [ ] Gate 3: bibliography built + every DOI verified + quota table measured
- [ ] Draft sections (opus subagents, tight briefs) → integrate
- [ ] content.py + generate_paper.py + figures
- [ ] Build .docx → PDF → visual verification (page count, layout, figures+tables ≤3 pp, body ≥8 pp)
- [ ] Abstract char counts (UA/EN) 1900–2200 measured
- [ ] Adversarial review: ITSSI editor + hostile reviewer + Ukrainian language (opus × 3)
- [ ] SUBMISSION_CHECKLIST.md filled with measured quota values
- [ ] Final report to team lead
