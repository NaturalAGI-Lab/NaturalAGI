#!/bin/bash
cd "$(dirname "$0")"
cat prompt.md | codex exec -m gpt-6-astra -c model_reasoning_effort='"high"' -s workspace-write -C . -o codex_report.txt - 2>&1 | tee codex.log
