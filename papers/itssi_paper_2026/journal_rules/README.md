# ITSSI Journal Rules — Cached Reference (Fetched 2026-04-27)

This folder caches the official author-side and editorial requirements for the journal:

> **«Сучасний стан наукових досліджень та технологій в промисловості»**
> *Innovative Technologies and Scientific Solutions for Industries (ITSSI)*

Source: <https://www.itssi-journal.com/index.php/ittsi/index>

All files were captured on **2026-04-27** by fetching the public OJS pages and downloading the journal's PDF documents (author guidelines, peer review policy, publication agreement). The intent is so that future agent sessions can answer formatting/policy questions WITHOUT re-fetching from the web.

## Files

| File | Content |
|------|---------|
| `journal_overview.md` | Journal identity: ISSN, scope, frequency, language, indexing, founders, MoES Category A registration |
| `author_guidelines.md` | **VERBATIM** copy of the author guideline PDF (checklist, manuscript formatting rules, formal article structure, references rules, author-info template) |
| `submission_checklist.md` | Distilled OJS submission checklist authors must satisfy before upload |
| `peer_review_policy.md` | Verbatim copy of the «Положення про рецензування статей» PDF (review process, reviewer/author rights and duties) |
| `publication_ethics.md` | Editorial policies, open access policy, copyright, author agreement |
| `scope_and_sections.md` | Scientific scope, MoES specialty codes covered, types of articles accepted/rejected |
| `source_urls.md` | All URLs fetched, plus list of binary PDFs to (re-)download manually with `curl` if needed |

## Key facts at a glance (for paper-writing decisions)

- **Languages accepted**: Ukrainian or English (English manuscripts: from foreign authors only — Ukrainian authors writing in English need translation-bureau certification of abstract+keywords or department-of-foreign-languages approval).
- **Manuscript format**: Microsoft Word (.docx).
- **Font size**: 10 pt, single line spacing (1.0).
- **Body text length**: NO LESS THAN 8 pages (excluding annotations and references), single-column layout (no two-column split).
- **Abstract**: 1900–2200 characters, structured (Subject matter… Goal… Tasks… Methods… Results… Conclusions…), free of unexplained abbreviations. Required in BOTH Ukrainian and English.
- **Keywords**: up to 10 keywords, separated by semicolon `;`, in BOTH Ukrainian and English.
- **References style**: Harvard Style (BSI) — Latin transliteration of all Ukrainian/Russian sources. References labeled as **References** (not «Список літератури»). DSTU 8302:2015 is **NOT** required for ITSSI (this is a DEPARTURE from the 2025 paper assumption — see comparison in `author_guidelines.md`).
- **Reference quotas**: ≥15 sources total; self-citation ≤30%; foreign English-language ≥40%; recent (≤4 years) ≥30%; with DOI ≥90%; in Scopus/WoS journals ≥60%.
- **UDC code**: required (top of article).
- **JEL classification**: not explicitly required by the new template, but historically used for economics-leaning articles. Engineering articles list UDC only.
- **ORCID + Scopus ID + e-mail + phone**: required for every author in the «Відомості про авторів / About the Authors» block (BOTH languages).
- **Plagiarism**: checked via StrikePlagiarism. Originality MUST be ≥75 %.
- **AI usage**: explicit declaration mandatory (model name, version, where used, what was done, how authors verified the output, impact on conclusions). AI may NOT be used to write substantive sections; only technical tasks (e.g. grammar checks).
- **Figures**: created in Visio or supplied as `.jpg`, `.jpeg`, `.png` at ≥300 dpi. AI-generated images must be tagged "Imagined with AI". Total pages occupied by figures + tables must NOT exceed 3.
- **Formulas**: typed via **MathType** ONLY. Word's built-in equation editor and graphical objects are forbidden. Numbering right-aligned, format `(1), (2)–(4)`. A formula is part of the sentence so a punctuation mark follows it.
- **Tables**: header rows must NOT contain empty cells. Tables placed vertically (portrait), not landscape.
- **Quotation marks**: only `" "` (straight ASCII double quotes) — NOT `« »`, NOT `“ ”`.
- **Mandatory sections** at end of body, before References: «Конфлікт інтересів», «Фінансування», «Доступність даних», «Використання засобів штучного інтелекту».
- **Article fee**: from 900 UAH (discounts negotiable). Submission itself is free.

## Submission workflow

1. Register / log in on the OJS site (<https://www.itssi-journal.com>).
2. Upload `.docx` manuscript + signed publication agreement (`PublicationAgreement_UA.pdf` template).
3. Editorial check (originality, scope, formatting compliance, plagiarism via StrikePlagiarism).
4. **Double-blind peer review** by 2 external experts (typically Doctors of Sciences / Professors). Reviewer turnaround: ~14 days, ≤1 month maximum.
5. If revisions requested: author returns the revised version within **2 weeks** (otherwise the «date received» is reset).
6. Final decision by the Editor-in-Chief; ratified by the Scientific-Technical Council of Kharkiv National University of Radio Electronics.
7. Article is assigned a **DOI** upon acceptance.

## Categorisation status (2026)

- Order of the Ministry of Education and Science of Ukraine **№1693 dated 23.12.2025** — journal included in the List of Scientific Professional Editions of Ukraine, **Category A**.
- Indexed in **Scopus**, Index Copernicus, DOAJ, Ulrich's, WorldCat, OpenAIRE, BASE, Google Scholar, ROAD, MIAR, etc. (full list in `journal_overview.md`).

## How this differs from the 2025 ITSSI paper assumptions

| Aspect | 2025 paper assumed | 2026 actual rules |
|---|---|---|
| References style | DSTU 8302:2015 (per global memory note) | **Harvard Style (BSI)**, Latin transliteration, label `References` |
| Abstract length | not explicitly enforced | **1900–2200 chars, structured** |
| Source quotas | none enforced | ≥15 refs, ≤30 % self-cite, ≥40 % English, ≥30 % recent, ≥90 % with DOI, ≥60 % Scopus/WoS |
| AI declaration | none | **mandatory section** — must enumerate model, version, where used |
| Originality threshold | unspecified | **≥75 %** (StrikePlagiarism) |
| Mandatory sections | Intro, Analysis, Aim, Methods, Results, Discussion, Conclusions | adds **Conflict of Interest, Funding, Data Availability, AI Usage** |
| Figures format | LaTeX `\includegraphics` (we generated PDFs) | **Word + raster** (`.jpg`, `.jpeg`, `.png` ≥300 dpi) — the 2025 paper was LaTeX, but the journal explicitly demands Word |
| Formula editor | LaTeX `amsmath` | **MathType** in Word |
| Quote marks | LaTeX defaults `` `` ' ' `` | **Only `" "`** straight ASCII quotes |

The 2025 paper was prepared in LaTeX (`itssi_paper_2025.tex`). For 2026 the manuscript MUST be a Word document — this matches the 2025 ITSSI paper that was generated via `python-docx` (per `papers/itssi_paper_2025/` analogue and the project memory note about python-docx as the established mechanism for ITSSI submissions). For 2026 paper generation, continue with python-docx + MathType-compatible OMML, NOT LaTeX.
