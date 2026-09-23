PYTHON := ../../.venv/bin/python
SOFFICE := /Applications/LibreOffice.app/Contents/MacOS/soffice
PDFINFO := /opt/homebrew/bin/pdfinfo

DOCX := itssi_xai_2026.docx
PDF  := itssi_xai_2026.pdf

.PHONY: all build preview pages clean install-deps

all: build preview pages

build:
	$(PYTHON) generate_paper.py

preview: build
	$(SOFFICE) --headless --convert-to pdf --outdir . $(DOCX)

pages: preview
	@$(PDFINFO) $(PDF) | grep -E 'Pages|Page size'
	@echo "ITSSI requires >= 8 pages of main text"

install-deps:
	$(PYTHON) -m pip install python-docx

clean:
	rm -f $(DOCX) $(PDF)
