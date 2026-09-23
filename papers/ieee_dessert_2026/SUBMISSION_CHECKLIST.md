# DESSERT'2026 submission checklist

Deadline **25 Aug 2026** (late slot opened by the organiser via K. Bokhan). Sources for every venue fact: `PhDObsidian/raw/analyses/dessert_2026/requirements.md`.

## Venue facts

- 16th IEEE DESSERT, 2–4 Oct 2026, Corfu, Greece, hybrid. Online presentation is allowed for authors from Ukraine.
- Proceedings: IEEE Xplore, Scopus. Language: English. Peer review by ≥3 reviewers, single-blind.
- Format: IEEE conference template, A4, **5–8 pages**, PDF. Ready-to-submit file: `dessert2026_submission.pdf` (copy of `build/main.pdf`).
- Portal: Microsoft CMT, https://cmt3.research.microsoft.com/DESSERT2026 (needs a CMT account).
- Subject area: *Trustworthy and explainable AI, AI as a Service, and resilient AI systems*. Fallback: *Image processing and recognition for smart and dependable systems*.
- Published dates: notification 2 Sep, camera-ready 9 Sep, registration and payment 12 Sep.
- Fee, online presentation, Ukrainian participant: 70 € (50 € IEEE member). Request the payment form from dessert@csn.khai.edu; registration form linked from https://www.dessert-conf.org/dessert-2026/registration-form/.
- "Submitted papers must be novel work and not published elsewhere." The ITSSI article (`papers/itssi_xai_2026/`) is a different text in a different language with a different title and author list; the KhPI Week version was rejected, not published.

## Author actions (cannot be done by the build)

- [ ] Co-authors read `build/main.pdf` and approve: title, author order (Lapin, Bokhan, Parzhyn, Perevoznyk, Aleksandrova), Bokhan's department line, Parzhyn's Augusta affiliation.
- [ ] Create the CMT account, add all five co-authors with the emails printed in the paper, pick the subject area above, upload the PDF.
- [ ] Confirm with K. Bokhan that the organiser's late-slot agreement covers CMT (the portal shows no closing marker, but the published deadline was 12 Aug).
- [ ] On acceptance: IEEE copyright form and camera-ready via CMT (expected, not published on the site); registration by 12 Sep.
- [ ] Repository URL `https://github.com/kbokh/NaturalAGI` is cited in the Conclusion — it must resolve throughout review; if the repository moves to an organisation account, keep a redirect.

## Build

```bash
cd papers/ieee_dessert_2026
make figures   # re-render figures/*.png from run_20260630_235356 and the vault evidence
make build     # latexmk → build/main.pdf
/opt/homebrew/bin/pdfinfo build/main.pdf | grep Pages
```

## Known limits stated in the paper (do not remove in camera-ready)

- Metric conditional on the hand-annotated completeness filter (8,707 of 10,000 admitted).
- Timing from the 770 misclassified images only; no per-comparison GED time; no end-to-end throughput.
- Augmentation parameters of the training corpus are not recoverable; the paper says "small rotation and translation" on purpose.
- No comparison with neural classifiers; the word "competitive" must not return.
