.PHONY: build clean watch

build:
	latexmk -pdf -interaction=nonstopmode -output-directory=build main.tex
	@echo "PDF: build/main.pdf"

watch:
	latexmk -pdf -pvc -interaction=nonstopmode -output-directory=build main.tex

clean:
	latexmk -C -output-directory=build main.tex
	rm -rf build
