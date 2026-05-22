# Source URLs and Fetch Log

> All fetches performed on **2026-04-27** from a Mac via `mcp__fetch__fetch` (HTML pages) and `curl` (PDFs).
> The journal site is in Ukrainian; the OJS instance is OJS 3.2.1.4.

## HTML pages successfully fetched (cached as Markdown in this folder)

| URL | Cached as | HTTP status |
|---|---|---|
| <https://www.itssi-journal.com/index.php/ittsi/index> | `journal_overview.md` | 200 OK |
| <https://www.itssi-journal.com/index.php/ittsi/about> | `journal_overview.md`, `scope_and_sections.md`, `publication_ethics.md` | 200 OK |
| <https://www.itssi-journal.com/index.php/ittsi/about/submissions> | `submission_checklist.md`, `publication_ethics.md` | 200 OK |
| <https://www.itssi-journal.com/index.php/ittsi/about/contact> | (used in `journal_overview.md`) | 200 OK |
| <https://www.itssi-journal.com/index.php/ittsi/about/aboutThisPublishingSystem> | (note: OJS 3.2.1.4) | 200 OK |

## HTML pages that returned 404

| URL | Note |
|---|---|
| <https://www.itssi-journal.com/index.php/ittsi/about/editorialPolicies> | No standalone editorial-policies page; content lives on `/about` and inside the peer-review PDF. |
| <https://www.itssi-journal.com/index.php/ittsi/about/sectionPolicies> | No standalone section-policies page. The journal has no parallel sections. |
| <https://www.itssi-journal.com/index.php/ittsi/about/authorFees> | Fees are declared inline on `/about/submissions` (from 900 UAH). |

## PDFs downloaded with curl

These PDFs were downloaded into `/tmp/` because `WebFetch` cannot parse binary files cleanly. The main agent should re-download them into `papers/itssi_paper_2026/journal_rules/` if a permanent local copy is needed (or just keep them at `/tmp/`).

| URL | `/tmp` filename | Size | Pages |
|---|---|---|---|
| <https://itssi-journal.com/files/PeerReviewingProcess_UA.pdf> | `itssi_peer_review.pdf` | 131 266 bytes | 4 |
| <https://drive.google.com/uc?export=download&id=1gnAnxtuhGMIhCmCkZRJVg5uubuDk-Xar> *(originally <https://drive.google.com/file/d/1gnAnxtuhGMIhCmCkZRJVg5uubuDk-Xar/view?usp=sharing>)* | `itssi_author_guidelines.pdf` | 208 809 bytes | 6 |
| <https://itssi-journal.com/files/PublicationAgreement_UA.pdf> | `itssi_publication_agreement.pdf` | 286 503 bytes | 1 |
| <https://itssi-journal.com/files/Certificate.pdf> | not downloaded | n/a | n/a — Media-registry certificate, not needed for authorship. |
| <https://itssi-journal.com/files/OrderMESU.pdf> | not downloaded | n/a | n/a — MoES Order №1693 dated 23.12.2025 (Category A). Useful for the abstract/cover-letter wording but not the article body. |

### Manual download commands (for the main agent)

If/when the main agent wants permanent local copies inside the repository (versus the `/tmp/` cache), run:

```bash
curl -sL "https://itssi-journal.com/files/PeerReviewingProcess_UA.pdf" \
  -o /Users/mlapin/Development/personal/NaturalAGI/papers/itssi_paper_2026/journal_rules/PeerReviewingProcess_UA.pdf

curl -sL "https://drive.google.com/uc?export=download&id=1gnAnxtuhGMIhCmCkZRJVg5uubuDk-Xar" \
  -o /Users/mlapin/Development/personal/NaturalAGI/papers/itssi_paper_2026/journal_rules/AuthorGuidelines_UA.pdf

curl -sL "https://itssi-journal.com/files/PublicationAgreement_UA.pdf" \
  -o /Users/mlapin/Development/personal/NaturalAGI/papers/itssi_paper_2026/journal_rules/PublicationAgreement_UA.pdf

curl -sL "https://itssi-journal.com/files/Certificate.pdf" \
  -o /Users/mlapin/Development/personal/NaturalAGI/papers/itssi_paper_2026/journal_rules/MediaRegistry_Certificate.pdf

curl -sL "https://itssi-journal.com/files/OrderMESU.pdf" \
  -o /Users/mlapin/Development/personal/NaturalAGI/papers/itssi_paper_2026/journal_rules/OrderMESU_1693_2025-12-23.pdf
```

## No Word/PDF article template

Despite multiple cross-references in the OJS pages, the journal **does not publish a downloadable Word template** — only the formatting-rules PDF (`AuthorGuidelines_UA.pdf` above). Authors must build their `.docx` from scratch using the rules captured in `author_guidelines.md`.

## Not template, but useful exemplar

For example layouts the main agent can study, browse the latest issue at:

- <https://www.itssi-journal.com/index.php/ittsi/issue/archive>

Each article PDF in there is a working example of how an accepted manuscript looks after the technical editor's pass.

## Repository tracking note

`/tmp/` is volatile (macOS clears it on reboot). If the main agent intends to refer to the PDFs across sessions, run the `curl` commands above to land them inside the repo (alongside this folder) before relying on them.
