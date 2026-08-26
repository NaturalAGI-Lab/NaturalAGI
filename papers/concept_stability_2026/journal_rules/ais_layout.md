# AIS layout specification

Journal: *Advanced Information Systems* / «Сучасні інформаційні системи», NTU
"KhPI", ISSN 2522-9052, quarterly, Category B, Index Copernicus.
Submission portal: <https://ais.khpi.edu.ua>.

Two sources, and they disagree in one place. The site's author page states the
rules; the team's own published AIS article
(`PhDObsidian/raw/papers/ours/parzhyn_lapin_bokhan_2025_energy_models_AIS.pdf`,
Vol. 9 No. 4, 2025, pp. 100–119, `doi:10.20998/2522-9052.2025.4.13`) shows what
the journal actually prints. Every geometric number below was measured off that
PDF with `pdftotext -bbox-layout`; where the site is silent the PDF decides.

## Site rules

- Manuscript file: Microsoft Word `.doc`.
- Times New Roman 10 pt, line spacing 1.0.
- A4, margins: left/right 2.25 cm, top 2.0 cm, bottom 2.5 cm.
- Minimum 4 full pages, Ukrainian or English. No maximum.
- References: minimum 8 sources, ≤10 years old, ≥50 % from foreign journals,
  self-citation ≤30 %, DOI where available. Ukrainian-language articles carry
  two reference lists; an English article carries one.
- Article structure: problem statement and relevance → analysis of recent
  research and publications → statement of the article tasks → main part →
  conclusions and prospects for future work.
- ORCID required for every author. Plagiarism screening via Unicheck.
- Publication fee 500 UAH.

## Page geometry (measured)

| Element | Value |
|---|---|
| Page | A4, 595.32 × 841.92 pt |
| Left / right margin | 63.86 pt = 2.25 cm |
| Text width | 467.96 pt = 16.51 cm |
| Columns | 2 × 226.92 pt (8.0 cm), gap 14.12 pt (0.5 cm) |
| Running head baseline | 39.4 pt from top edge (header distance ≈ 1.39 cm) |
| First body element | 59.2 pt from top edge |
| Footer | page number + copyright line, ≈ 1.8 cm from bottom edge |

## Font sizes (measured)

| Element | Size | Style |
|---|---|---|
| Running head, UDC/doi line, body text | 10 pt | regular, justified |
| Author line | 11 pt | regular, superscript affiliation markers |
| Affiliation lines | 11 pt | regular |
| Article title | 12 pt | ALL CAPS, centered |
| Abstract, keywords | 9 pt | justified, left indent 0.75 cm |
| Section headings | 11 pt | regular, centered |
| Figure and table captions | 9 pt | fig. caption centered below, table caption left above |
| References | 9 pt | numbered list |
| First-line paragraph indent | 21.2 pt = 0.75 cm | body and abstract |
| Line spacing | Word single | 10.35 pt at 9 pt, 11.5 pt at 10 pt |

## Front matter order

1. Running head — odd pages `Advanced Information Systems. YYYY. Vol. N, No. M`
   left / `ISSN 2522-9052` right; even pages `ISSN 2522-9052` left /
   `Сучасні інформаційні системи. YYYY. Т. N, № M` right; rule below.
2. `UDC <code>` left, `doi: https://doi.org/10.20998/...` right — the DOI is
   assigned by the editor, so a submission leaves it out.
3. Author line with superscript affiliation numbers.
4. Affiliation lines, one per superscript.
5. Title, all caps, centered.
6. Abstract, opening with letter-spaced `A b s t r a c t .` followed by the
   structured labels the journal prints in letter-spaced type: *Relevance.*,
   *The object of research*, *The subject of the research*, *The purpose of this
   paper*, *Research Results.*
7. `K e y w o r d s :` letter-spaced, entries separated by semicolons.
8. Section break to the two-column body.

## Back matter order

1. `References` heading, small caps, centered; numbered entries in AIS Harvard:
   `1. Surname, I., Surname, I. and Surname, I. (Year), "Title", Source, vol. N,
   no. M, pp. X–Y, doi: <url>` — `available at: <url>` when there is no DOI.
2. Right-aligned `Received (Надійшла) DD.MM.YYYY` and
   `Accepted for publication (Прийнято до друку) DD.MM.YYYY`.
3. `ВІДОМОСТІ ПРО АВТОРІВ / ABOUT THE AUTHORS`, centered small caps. Per author:
   bold Ukrainian name — Ukrainian degree/position/affiliation; English name –
   English equivalent; `e-mail:`; `ORCID Author ID:`; `Scopus ID:`.
4. Ukrainian block: bold centered title, author line, `А н о т а ц і я .` with
   the same structured labels (`Об'єкт дослідження`, `Предмет дослідження`,
   `Метою даної статті`, `Результати дослідження`), then
   `К л ю ч о в і   с л о в а :`.

## Choices this paper makes where the sources are silent

- **Subsection headings**: the reference article has none. Rendered here as
  bold italic 10 pt on their own line, indented like a paragraph — subordinate
  to the centered 11 pt section headings without inventing a competing style.
- **Wide tables and figures**: placed in a full-width single-column section
  break, matching how the reference article prints Table 1 and its wide
  figures.
- **Reference age**: the ≤10-year rule is applied as the journal itself applies
  it — the reference article cites Landauer 1961 and Hopfield 1982 — so
  foundational GED and skeletonization sources stay.
