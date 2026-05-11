# ITSSI 2026 — Pre-Submission Checklist

**Status as of 2026-04-27:** body and abstracts written, references list meets all journal quotas, declarations and author block populated except for the items below.

**Hard deadlines** (per NotebookLM transcripts of supervisor meetings):
- **2026-05-04** — draft to supervisor (Yu. Parzhyn) for final review
- **2026-05-10** — journal submission deadline (June publication target)

---

## 1. Items requiring HUMAN action before submission

### 1.1 Author-block fields — current state (after 2026-04-27 web verification)

Verified via ORCID public API + OpenAlex cross-reference:

| Author | ORCID | Scopus Author ID |
|---|---|---|
| Лапін М. О. | **CORRECTED** to `0009-0003-6307-1172` (was wrong in 2025 paper — old ID was someone else's private profile; new ID confirmed via Crossref on team's АСУ paper) | **MISSING** — ORCID profile has no Scopus link, log into scopus.com/freelookup/form/author.uri |
| Бохан К. О. | **CORRECTED** to `0000-0003-3375-2527` (was wrong in 2025 paper — old ID belonged to Luis Jiménez-Ortega) | **57191592568** ✓ |
| Перевозник К. М. | **CORRECTED** to `0009-0009-2327-1501` (was wrong in 2025 paper — confirmed via Crossref on co-author paper with Parzhyn) | **MISSING** — ORCID profile has no Scopus link, log into scopus.com/freelookup/form/author.uri OR set to `"-"` if no profile yet |
| Паржин Ю. В. | **CORRECTED** to `0000-0001-5727-1918` (was wrong in 2025 paper — old ID had no public employments) | **57224412390** ✓ |

**Implication**: ALL FOUR ORCIDs in the 2025 paper were wrong — likely the team typed them in haste. Treat any author ID copied from `papers/itssi_paper_2025/` as suspect, always verify against Crossref/ORCID.

**Phone numbers removed by request 2026-04-27** — the journal's author-guidelines technically list `контактний телефон` as required, but this draft omits the field. If the OJS editorial check bounces the paper for missing phones, re-add `phone` keys to each author dict in `content.py:61-150` and the `моб. {phone}` / `mob. {phone}` lines to `generate_paper.py` (was `add_author_details_block`).

**Bokhan's patronymic** "Олександрович" remains unverified — neither the NTU "KhPI" departmental staff page nor his ORCID profile expose it. Confirm with the co-author.

If any author has no Scopus profile, replace the `?` placeholder with `"-"` rather than leaving the question mark — the OJS submission form will reject the `?` placeholder.

### 1.1.1 Department naming ambiguity (BLOCKING — needs co-author resolution)

Each author's verified ORCID points to a DIFFERENT department within NTU "KhPI":

| Author | Department per ORCID | Maps to |
|---|---|---|
| Лапін М. О. | "Системний аналіз та інформаційно-аналітичні технології" | **САІАТ** (web.kpi.kharkov.ua/say/) |
| Бохан К. О. | "Computer science and intellectual property" | КНІВ (Computer Science and Intellectual Property) |
| Перевозник К. М. | (ORCID profile has no employments — likely his department wasn't filled in) | unknown |
| Паржин Ю. В. | (Augusta) — earlier at NTU "KhPI" was "Computer Science and Intellectual Property" then "Systems Analysis and Information-Analytical Technologies" | КНІВ → САІАТ → Augusta |

The current 2026 draft uses «кафедра систем інформації ім. В. О. Кравця» for ALL THREE NTU "KhPI" authors — but neither Lapin nor Bokhan actually lists that department on their ORCID. Two possible explanations:

1. The team has restructured and now all three are in «Кравця» but their ORCID profiles aren't updated yet
2. The team is split across САІАТ (Lapin), КНІВ (Bokhan), and possibly «Кравця» (Perevoznyk)

Action: ask Bokhan, Lapin, and Perevoznyk individually which department they are CURRENTLY enrolled in for the 2025/26 academic year, and update each `department_ua` / `department_en` / `position_ua` / `position_en` field in `content.py:61-150` accordingly. This may differ between PhD students (Lapin, Perevoznyk) and teaching staff (Bokhan).

### 1.2 Word-only manual edits (the python-docx generator cannot do these)

After running `make build`, open the `.docx` in Microsoft Word and do:

1. **Insert the MathType formula** in §4 Methods. The generator writes a placeholder paragraph `[TODO MathType: C_{i+1} = CRO(C_i, G_{i+1})]`. Delete the placeholder text and insert a MathType object on its place via *Insert → Object → MathType Equation*. Number stays right-aligned as `(1)`. Word's built-in equation editor is **forbidden** by the journal — use MathType only.

2. **Insert Figure 1** (pipeline image → skeleton → graph → concept → GED). The generator emits `[Рисунок 1: ...]` placeholder. **Source**: needs to be drawn in Visio, draw.io, or similar, ≥300 dpi, exported as `.png`. See `figures/fig_1_pipeline_TODO.md` for a full description of what to depict. Place the image where the placeholder line is, with the caption "Рис. 1. Пайплайн перетворення растрового зображення на концепт-граф і класифікації за GED" centred below.

3. **Insert Figure 2** (graph representation of one digit-7 image). See `figures/fig_2_digit7_TODO.md` for the Cypher query that pulls a single digit-7 graph from Neo4j and the matplotlib snippet to render it. Replace the placeholder.

4. **Insert Figure 3** (concept-attractor 7_1 after reduction). See `figures/fig_3_concept_7_1_TODO.md`. Replace placeholder.

5. **Insert Figure 4** (confusion matrix). PNG already produced at `figures/fig_4_confusion_matrix.png` (300 dpi). Replace the placeholder via *Insert → Pictures → This Device*.

6. **Insert Table 1** (comparison with classical baselines). Data prepared in `figures/table_1_baselines.csv`. Recommended: open the CSV in Excel, copy-paste into Word as a Table, then format header row with bold + centred. Place where the `[Таблиця 1. ...]` placeholder line currently sits. Caption above the table.

7. **Insert Table 2** (per-class metrics). Data in `figures/table_2_per_class.csv` (Ukrainian headers). Same procedure as Table 1.

8. **Insert Table 3** (top-10 confusion pairs). Data in `figures/table_3_confusions.csv`. Same procedure.

9. **After all insertions** — verify total figures + tables footprint **does not exceed 3 pages combined** (journal hard rule). If too long, shrink Figure 4 (confusion matrix) or move part of Table 3 into supplementary material.

### 1.3 Title-case (cosmetic)

The generator currently uppercases the title via `.upper()` (`generate_paper.py:146`). The 2025 ITSSI accepted papers used title case rather than ALL CAPS. If the editorial assistant requests a change, edit `generate_paper.py:146` from `title.upper()` to just `title`.

### 1.4 Plagiarism check

Run the manuscript through StrikePlagiarism (the journal's chosen tool) before submission. Originality must be **≥75 %**. The generator-emitted text inherits content the assistant wrote — verify there are no near-duplicates of public sources. Most at-risk sentences:
- Anything that paraphrases LeCun 1998, Slack 2020, or Sanfeliu & Fu 1983 — verify the prose is your own.
- The two self-citations (Parzhyn 2025 ×2) should be cited with `Parzhyn (2025)` not block-quoted.

### 1.5 English-abstract certification (BLOCKING — added 2026-04-27 after re-reading submission_checklist.md)

**The journal explicitly requires** that the English abstract + English keywords (for any Ukrainian-language manuscript with Ukrainian authors) be **certified** by EITHER:

- a translation bureau, with a stamp on the certification document; OR
- the head of the foreign-languages department of the author's higher-education institution, with a stamp.

> "Without that certification, English content from non-foreign authors will be rejected." — `journal_rules/submission_checklist.md`

Action: take the EN abstract + EN keywords from `content.py` (`ABSTRACT_EN_*`, `KEYWORDS_EN`) and the EN title (`TITLE_EN`) on a single sheet of paper, get one of the above stamps, scan, and upload alongside the manuscript on OJS.

Do NOT skip this step — the editorial office will return the manuscript without registration, costing days against the May 10 deadline. Lapin and Bokhan are at NTU "KhPI" — the «кафедра іноземних мов» there can stamp; for the fastest turnaround, schedule the visit in the same week as supervisor sign-off (target: 2026-05-04 to 2026-05-08).

### 1.6 Bilingual check by an external English speaker (recommended)

ITSSI Ukrainian-language submissions only require an EN abstract; the body stays Ukrainian. But the EN abstract is what international readers see first. Get a native English reader to spot-check the EN abstract for any awkward phrasing introduced by the assistant. This is separate from (and weaker than) the certification requirement in 1.5 — do both.

---

## 2. Items already satisfied — quick reference

| Journal requirement | Status | Where verified |
|---|---|---|
| Microsoft Word `.docx` | ✓ | `make build` produces .docx |
| 10 pt single-spaced single-column | ✓ | `generate_paper.py:43, 76` |
| Body ≥ 8 pages | **see 2.1** | `make pages` |
| Abstract 1900–2200 chars (UA + EN) | ✓ (UA 2098, EN 2077) | run validation script |
| Keywords ≤ 10, semicolon-separated | ✓ (9 each language) | `content.py:32-54` |
| Structured abstract (6 labels) | ✓ | `generate_paper.py:154-178` |
| References ≥ 15 | ✓ (22) | `content.py REFERENCES list` |
| Self-citation ≤ 30 % | ✓ (9.1 %) | validation script |
| Foreign English ≥ 40 % | ✓ (100 %) | validation script |
| 2023+ recent ≥ 30 % | ✓ (36.4 %) | validation script |
| DOI coverage ≥ 90 % | ✓ (100 %) | validation script |
| Scopus/WoS ≥ 60 % | ✓ (95.5 %) | validation script |
| Mandatory closing sections (CoI, Funding, Data, AI) | ✓ | `content.py:DECLARATION_*` |
| UDC code | ✓ (004.93) | `content.py:21` |
| ORCIDs for all authors | ✓ (real values from ITSSI 2025) | `content.py AUTHORS` |
| Quotation marks `" "` only (no `«»` or `""`) | ✓ | validation script |
| Worked example in §4 | **see 2.1** | `SECTION_4_METHODS` |

### 2.1 Body page count and worked example

After the figures and tables are inserted manually in Word (steps 1.2.1 through 1.2.8), recount pages with:

```bash
make pages
```

Body alone (sections 1-7, before "Конфлікт інтересів") should be **≥8 pages**. The current text-only state is 6-7 pages of prose; the 4 figures + 3 tables add ~2-3 pages, hitting the requirement. If it falls short after insertion, the candidate sections to expand are §2 Literature and §5 Results (lowest density vs target). The §4 worked example for digit-7 → concept_7_1 reduction was added by the body-expansion subagent — verify it is present and concrete.

---

## 3. Build and preview commands

```bash
cd /Users/mlapin/Development/personal/NaturalAGI/papers/itssi_paper_2026

# Generate .docx from content.py
make build

# Render PDF for visual review (LibreOffice headless)
make preview

# Print page count and reminder of ITSSI 8-page minimum
make pages

# Validate abstract length, reference quotas, TODO leakage
/Users/mlapin/Development/personal/NaturalAGI/natural-agi/bin/python -c "
import content as c
ua = sum(len(getattr(c, f'ABSTRACT_UA_{k}')) for k in ['SUBJECT','GOAL','TASKS','METHODS','RESULTS','CONCLUSIONS'])
en = sum(len(getattr(c, f'ABSTRACT_EN_{k}')) for k in ['SUBJECT','GOAL','TASKS','METHODS','RESULTS','CONCLUSIONS'])
total = len(c.REFERENCES)
recent = sum(1 for r in c.REFERENCES if r['year'] >= 2023)
self_cit = sum(1 for r in c.REFERENCES if r.get('self_citation'))
with_doi = sum(1 for r in c.REFERENCES if r.get('doi'))
scopus = sum(1 for r in c.REFERENCES if r.get('scopus'))
print(f'Abstract UA: {ua} chars (1900-2200)')
print(f'Abstract EN: {en} chars (1900-2200)')
print(f'Refs: {total} (>=15), 2023+: {100*recent/total:.1f}% (>=30%), self: {100*self_cit/total:.1f}% (<=30%), DOI: {100*with_doi/total:.1f}% (>=90%), Scopus: {100*scopus/total:.1f}% (>=60%)')
"
```

---

## 4. Files in this folder

| File | Purpose |
|---|---|
| `content.py` | All editable text, references, author block — the source of truth |
| `generate_paper.py` | python-docx renderer (do NOT put text here, only formatting) |
| `Makefile` | Build/preview/page-count targets |
| `itssi_paper_2026.docx` | Generated artefact (commit when stable) |
| `itssi_paper_2026.pdf` | Preview render (do NOT submit — submit the .docx) |
| `journal_rules/` | Cached ITSSI journal policies, author guidelines, peer-review process — verbatim from the journal site as of 2026-04-27 |
| `figures/` | Figure 4 PNG + 3 figure-TODO descriptors + 3 ready-to-insert table CSV/MD files |
| `notebooklm_context_2026-04-27.md` | Supervisor instructions and target framing pulled from the project NotebookLM |
| `draft_review_2026-04-27.md` | Pre-edit assessment of the draft (now mostly resolved) |
| `SUBMISSION_CHECKLIST.md` | This file |

---

## 5. After submission

If the journal returns the paper for revisions, authors must respond within **2 weeks** or the "date received" is reset (per `journal_rules/peer_review_policy.md`).
