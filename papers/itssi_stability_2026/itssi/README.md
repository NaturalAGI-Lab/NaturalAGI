# ITSSI submission files

`lapin_itssi_2026_en.docx` (English body) and `lapin_itssi_2026_uk.docx` (Ukrainian body) are the working copies. Edit them directly: the author fills the yellow marks (abstract length, sentence at the end of 1.1, phone numbers, reviewed draft paragraphs) and replaces formulas with MathType.

`build_itssi.py` creates both files from `../ais/writing_kit/lapin_ais_2026_submission.docx`, the translation, the drafts and `drafts/references.json`. Running it overwrites the docx and PDF files, so run it only to start over:

```
cd papers/itssi_stability_2026
uv run -q --with python-docx --with lxml --with pymupdf python itssi/build_itssi.py
```

It converts both files to PDF with LibreOffice and prints the checks (formulas, images, references, page counts). Exit code is 0 only when all checks pass.
