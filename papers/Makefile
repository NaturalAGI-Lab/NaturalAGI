.PHONY: build clean validate-bib help

PAPER_DIR = practical_paper_draft
TEX_FILE = $(PAPER_DIR)/practical_paper_draft.tex
BUILD_DIR = $(PAPER_DIR)
PDF_NAME = practical_paper_draft.pdf

build:
	@echo "Building paper..."
	@mkdir -p $(BUILD_DIR)
	@cd $(PAPER_DIR) && latexmk -pdf -output-directory=build -interaction=nonstopmode practical_paper_draft.tex
	@echo "PDF created at: $(BUILD_DIR)/$(PDF_NAME)"

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete."

validate-bib:
	@if [ -z "$(BIB_FILE)" ]; then \
		echo "Error: Please specify BIB_FILE=path/to/file.bib"; \
		exit 1; \
	fi
	@python3 validate_bib.py $(BIB_FILE)

help:
	@echo "Available targets:"
	@echo "  make build              - Build the paper PDF"
	@echo "  make clean              - Remove build artifacts"
	@echo "  make validate-bib BIB_FILE=<path> - Validate and auto-fix BibTeX file"
	@echo "  make help               - Show this help message"

