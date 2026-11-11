#!/usr/bin/env bash
# Usage: build.sh [--export] [--log]
#   --export  export the open Pages document 1 to pages_export.docx first (macOS only, uses osascript;
#             the export neither saves nor modifies the .pages file)
#   --log     also write <output>.mathlog.json
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$HERE/pages_export.docx"
OUTPUT="$HERE/../lapin_ais_2026_submission.docx"
PY=(uv run -q --with lxml python)

export_flag=0
fix_args=()
for arg in "$@"; do
  case "$arg" in
    --export) export_flag=1 ;;
    --log) fix_args+=(--log) ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [[ $export_flag -eq 1 ]]; then
  TMP_EXPORT="$HERE/.pages_export_new.docx"
  osascript - "$TMP_EXPORT" <<'APPLESCRIPT'
on run argv
  tell application "Pages"
    export document 1 to (POSIX file (item 1 of argv)) as Microsoft Word
  end tell
end run
APPLESCRIPT
  mv -f "$TMP_EXPORT" "$INPUT"
fi

"${PY[@]}" "$HERE/fix.py" "$INPUT" "$OUTPUT" ${fix_args[@]+"${fix_args[@]}"}
"${PY[@]}" "$HERE/verify.py" "$INPUT" "$OUTPUT"
