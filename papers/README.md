# Papers

This directory contains academic papers for the NaturalAGI project.

## Structure

- `practical_paper_draft/` - Practical paper on ComAN architecture
- Each paper has its own subdirectory with:
  - LaTeX source files (`.tex`)
  - `build/` directory for compilation artifacts (gitignored)

## Building Papers

Use the Makefile to build papers:

```bash
make build  # Build the paper
make clean  # Clean build artifacts
```

## Adding a New Paper

1. Create a new directory: `mkdir papers/new_paper_name`
2. Add your `.tex` file to the directory
3. Update the Makefile to include the new paper

