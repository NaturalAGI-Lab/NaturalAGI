# AIS Word build

`fix.py` turns the Pages-to-Word export (`pages_export.docx`) into `../lapin_ais_2026_submission.docx`: layout fixes, figure and table placement, plain-text math converted to OMML. `verify.py` checks that the text did not change (normalized paragraph multiset, exit code 1 if it differs).

```
bash build.sh            # rebuild from the committed pages_export.docx
bash build.sh --export   # first export the open Pages document 1 (macOS, osascript)
bash build.sh --log      # also write the math conversion log next to the output
```

Run it from any directory. Needs `uv`; lxml is fetched on the fly. Never open or save the `.pages` file from a script.

Every paragraph is found by a text or structural anchor. If a step stops with `fix.py: anchor failed: ...`, the author's edit changed the anchored text (or its neighbours). Read the named anchor in `fix.py`, compare it to the new text in `pages_export.docx`, and update the regex. Do not fall back to a paragraph index.
