# Librarian — Triage & Repair stage: integration run (2026-10-22)

Status: **stage complete; toolchain installed and first repairs executed (see addendum)**

## What ran

```powershell
python .\scripts\build_manifest_from_db.py   # new: DB ledger -> files_manifest.json (11,533 files)
python .\scripts\classify_documents.py       # repo script, unmodified
python .\scripts\triage_document_health.py   # repo script + 3 rule completions (below)
python .\scripts\repair_bad_files.py         # repo script, unmodified
```

Outputs (gitignored, `data/reviews/`):

- `needs_review.json` — 1,125 flagged of 11,533 (triage ran 510-690 s; it
  re-hashes the full 4.15 GB collection twice from disk — expected, not a hang)
- `repair_log.json` — 1,125 planned actions with suggested open-source commands
  and tool availability

## Triage results

| status | count | action (repair plan) |
|---|---:|---|
| `needs_review` (unsupported type) | 746 | manual_review |
| `duplicate` (SHA-256) | 358 | keep canonical copy only |
| `office_corruption` (genuine) | 4 | LibreOffice rescue -> re-extract |
| `lock_file` (`~$`) | 12 | skip_and_exclude |
| `empty_file` (0 bytes) | 2 | quarantine_or_skip |
| `text_zero_chars` (images-only) | 2 | manual_review |
| `pdf_damage` | 1 | qpdf/Ghostscript -> re-extract |

## Reconciliation with the app-side report (`needs-review-2026-10-22.md`)

**All 23 app-side NEEDS_REVIEW documents are covered by the ledger:**

- 12 lock files — exact match
- 2 zero-byte `.md` — exact match
- 2 images-only Office files — caught by `text_zero_chars`
- 4 genuinely broken ZIP containers (1 `.xlsx`, 1 `.pptx` Bad CRC slide layout,
  1 `.docx` Bad CRC endnotes, 1 `.pptx` not-a-zip) — caught by zip validation
- 1 PDF with `Stream has ended unexpectedly` (PROPONENT'S ENVIRONMENTAL
  ASSESSMENT.pdf, 8 MB, unique) — caught by `pdf_damage`
- 2 truncated factorial-experiment PDFs — caught earlier as `duplicate`
  (both copies are byte-identical); they are also `pdf_damage`-class files

## Rule completions made to `triage_document_health.py`

The repo's own documents promise these checks, but the script did not
implement them (completed, not re-designed):

1. **Bad CRC-32 detection** — `zf.testzip()` returns the first bad member name
   instead of raising; the return value was ignored. README ("invalid
   ZIP-based Office files") and `docs/REPAIR_WORKFLOW.md` ("bad CRC-32") both
   require it. This promoted AE-01.pptx and AE-02.cs.docx to `office_corruption`.
2. **`text_zero_chars`** — required by `config/review_rules.yaml`
   (`triage.categories`) and README ("files that extract zero characters").
   Uses the `chars` field the DB-backed manifest bridge now provides; catches
   files that parse cleanly but yielded no text (images-only decks).
3. **ZIP-container scope** — `.xls` removed from zip validation: legacy `.xls`
   is OLE/CFB, never a ZIP container, so all 72 `.xls` files were false
   `office_corruption`. `.opencode/instructions.md` says "validate Office ZIP
   containers". Result: `office_corruption` 74 -> 4, all genuine.

## Decisions for the owner

1. **Toolchain not installed** — `repair_log.json` reports
   `qpdf/gs/soffice/7z = false`. 75 planned repairs (4 office + 1 pdf) cannot
   execute until local open-source tools are installed (commands in
   `config/review_rules.yaml`: `winget install qpdf.qpdf`, Ghostscript and
   LibreOffice installers, 7-Zip, `winget install jdupes`). Installs require
   owner approval (downloads + system changes).
2. **746 unsupported-type files** — `.html` 347, `.doc` 264, `.ppt` 55,
   `.jpg` 31, `.xml` 21, `.txt` 19, `.png` 5, `.csv` 3, `.htm` 1. Note the
   `app/` extractor already handles HTML/TXT successfully, so "unsupported"
   here is the *triage classifier's* policy, not an extraction failure.
   Options: extend `classify_documents.py` + triage policy, or accept as a
   standing review list.
3. **358 duplicate files** — dedupe ledger already records
   `Duplicate of <canonical>` in `documents.error_message`; decide whether to
   change their DB status (e.g. `SKIPPED`/`INACTIVE`) or leave as-is.
4. **23 app-side NEEDS_REVIEW rows** — unchanged, awaiting dispositions.

## Deliberate omissions

- `scripts/quality_gate.py` was not run: it only measures serialized manifest
  JSON size and would mark all 10,604 manifests `manual_review_required`. The
  `app/` quality gate already enforces the same threshold
  (`QUALITY_THRESHOLD=0.35` = `review_rules.quality.minimum_quality_score`).
- No cloud/SaaS tools used anywhere; all scripts are stdlib + pypdf.

## Timing / operations notes

- Full stage: manifest 1 s + classify <1 s + triage 510-690 s + repair <1 s.
- Triage re-hashes from disk every run (no cache) — run it detached
  (log: `logs/triage-stage-2026-10-22.log`).

## Addendum — toolchain install + repair execution (2026-10-22 afternoon)

### Toolchain (winget, Tim-approved)

| Tool | Version | Location | On PATH (user) |
|---|---|---|---|
| qpdf | 12.4.2 | `C:\Program Files\qpdf 12.4.2\bin` | yes |
| 7-Zip | 26.05 | `C:\Program Files\7-Zip` | yes |
| LibreOffice | 26.8.1.1 | `C:\Program Files\LibreOffice\program` | yes |
| Ghostscript | — | skipped (Tim decision) | — |

`repair_bad_files.py` re-run: all 1,125 items report `qpdf/7z/soffice`
available (`gs` false — only affects the third suggested command on the one
`pdf_damage` item). Repair plan: `data/reviews/repair_log.json`.

### First repairs (copies only, originals untouched)

Executed 2026-10-22 against the 7 genuine repair candidates. Outputs under
`data/reviews/repair/<NN>_<name>/`; ledger in
`data/reviews/repair/repair_results.json` (+ `_retry.json`).

| # | File | Triage status | Outcome |
|---|---|---|---|
| 1 | ITEC 6005 Project Annex 2.xlsx | office_corruption | rescued -> PDF (2 pp, 1,531 text chars) |
| 2 | AE-01 Introduction to Electrical Engineering(3).pptx | office_corruption | rescued -> PDF (15 pp, 1,100 chars) |
| 3 | AE-02.cs.docx | office_corruption | rescued -> TXT (2,195 chars) |
| 4 | ERDC Base Camp Tools 2017.pptx | office_corruption | **not recoverable** — LO "source file could not be loaded" |
| 5 | Inserts for Assignment 4.pptx | text_zero_chars | rescued -> PDF (2 pp; image-only slides, faithful) |
| 6 | ITEC 6407 Project proposal.docx | text_zero_chars | **empty shell** — TXT export = 5 bytes; nothing to recover |
| 7 | PROPONENT'S ENVIRONMENTAL ASSESSMENT.pdf | pdf_damage | **not recoverable by qpdf** (exit 2, no trailer); needs Ghostscript re-distill or manual |

4 rescued, 1 faithful image-only rescue, 1 genuinely empty, 2 unrecoverable.
Items 4 and 7 stay `needs_review`; a Ghostscript install can retry item 7 later.

### Quarantine decisions

- `empty_file` x2 (`VGLI.md`, `Untitled.md`): left in place, already excluded
  from indexing by zero-byte gate; no action needed.
- `lock_file` x12 (`~$*`): auto-excluded by classifier; never indexed.
- Destructive commands (`qpdf --replace-input`, in-place conversions) were
  deliberately **not** used on `D:\References` originals.

### Operational notes

- soffice quirks encountered: (a) cannot write output over its own input —
  move source into a `src/` subdir first; (b) bare `xlsx` export filter name
  fails — use `pdf` or full filter names; (c) `--version` hangs on first run —
  use file existence instead; (d) harmless stderr line
  `Could not find platform independent libraries <prefix>`.
- winget quirks: `Start-Process -Wait` deadlocks on winget's child tree — use
  `-PassThru` + `WaitForExit()`; resolve real winget exe via
  `Get-AppxPackage Microsoft.DesktopAppInstaller`; transcript logging collides
  if a previous elevated session still holds the file — use unique log names.

## Dispositions (Tim, 2026-10-23)

- **Duplicates:** the 216 non-canonical members of the 148 exact-hash groups
  (already carrying `Duplicate of ...` in `error_message`) were set to
  `INACTIVE` in `data/librarian.db`. Invariant verified: every group keeps
  exactly one active member. DB backup:
  `data/backups/librarian.db-20261023-060743`. Status counts after:
  INDEXED 10,451 / DISCOVERED 847 / INACTIVE 216 / NEEDS_REVIEW 19.
- **Unsupported-type (746):** kept as a standing review list — no DB status
  change. Full ledger: `reports/standing-review-unsupported-2026-10-23.md`
  (+ machine-readable `data/reviews/unsupported-standing-review.json`).
- **Git:** everything above pushed to `origin/main` (flo7-png/librarian).
