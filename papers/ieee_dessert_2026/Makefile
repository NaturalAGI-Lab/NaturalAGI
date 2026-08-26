.PHONY: build clean watch figures

PYTHON := ../../.venv/bin/python

build:
	latexmk -pdf -interaction=nonstopmode -output-directory=build main.tex
	@echo "PDF: build/main.pdf"

figures:
	$(PYTHON) render_figures.py

watch:
	latexmk -pdf -pvc -interaction=nonstopmode -output-directory=build main.tex

clean:
	latexmk -C -output-directory=build main.tex
	rm -rf build
