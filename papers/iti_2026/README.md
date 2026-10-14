# IT&I(s)-2026 — regular presentation (2026)

XIII International Satellite Conference "Information Technology and Implementation",
Taras Shevchenko National University of Kyiv, 20 Nov 2026. Proceedings are planned
as a separate volume; the site states no indexing.

## What goes here

An English 1–2 page version of the Error Anatomy paper
(`papers/colins_2026/manuscript.md`), with the whole team as authors.

- 11 Sep 2026 meeting: COLINS never answered, so the paper goes "на конференцію в
  Київ" (vault `raw/meetings/2026-09-11_dysertaciya-ta-robochi-plany.md`, 08:21–08:55).
- Aug 2026: "Тільки перероби її під шаблон конференції." … "Включи всю команду."
  (vault `raw/evidence/2026-08_publication_followup/messages_1.png`, 20:49–20:50).
  Author order follows DESSERT: Lapin, Bokhan, Parzhyn, Perevoznyk, Aleksandrova.
- Decided 19.09: the main track (Springer CCIS) closed on 15 Sep, so the supervisor
  chose the satellite, regular presentation: "Ок, подавай на регулярну презентацію."

## Build

`content.py` holds the text, `build_docx.py` pours it into the template and writes
`iti_2026_lapin.docx` (2 pages, 670 words). The script also sets the running header to
IT&I(s)-2026 and starts page numbering at 1; the template ships with the 2025 header
and numbering from 3, and stays untouched in `journal_rules/`.

```bash
.venv/bin/python papers/iti_2026/build_docx.py
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf \
    --outdir papers/iti_2026 papers/iti_2026/iti_2026_lapin.docx
```

The paper reports two formation probes: the stabilization markers and the sample-count
curves. It leaves out the order probe, because the current code pairs samples in an
order-dependent way (Linear NIK-384) while the method is order-independent. The 2→7 error anatomy stays out, because DESSERT'2026
publishes it and the conference rejects overlapping submissions. Numbers re-verified
2026-09-20 by rerunning `training.supervisor_experiments` over the cached probes.

## Requirements

Source: `http://iti.fit.univ.kiev.ua/en/paper-submission-itis/` (http only; the https
certificate belongs to another host).

| Item | Rule |
|---|---|
| Deadline | 1 Nov 2026; notification 5 Nov; camera-ready 10 Nov |
| Length | 1–2 pages (regular presentation) |
| Language | English, checked for grammar and style |
| Format | Word template `journal_rules/ITIS-Word-template.doc` (`.docx` copy made with LibreOffice) |
| Originality | Not submitted to another journal or conference at the same time |
| Plagiarism | Unicheck; significant overlap is rejected without review |
| Submission | E-mail to `iti.fit@knu.ua` |
| Fee | 200 UAH per publication; 100 UAH for postgraduate students; printed volume +150 UAH |

## Template layout

Read from the `.doc`, not stated on the site.

- A4, 2 cm margins on all sides, mirrored header with the running title and page number.
- Times New Roman 14 pt, single spacing, justified, 1.25 cm first-line indent.
- Author block, left-aligned: name bold italic; position and faculty on the next line;
  affiliation italic.
- Title bold, all caps, centred.
- Run-in section heads in bold inside the paragraph: `Introduction.`, `Background.`,
  `Conclusion.`
- Numbered equations right-aligned, `(1)`; caption below the figure, `Figure 1. …`.
- `References:` bold 12 pt, numbered list 12 pt, APA-like; citations as `[1–2]`.

Page 1 of the template holds 385 words, so two pages fit roughly 750 words with
the author block and references and no figure. The source manuscript is about 5,700 words.
