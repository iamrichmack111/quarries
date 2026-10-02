# Changelog

## 2026-10-02 — Daily Mishnah + Black Square Pipeline

### Added
- Added **Mishnah** to `quarries-daily`.
- Daily Mishnah references are discovered through the existing Sefaria calendar flow.
- Mishnah Hebrew source text now passes through the normal Quarries analysis and ZIP export pipeline.
- Mishnah ZIPs are recognized by `quarries-black-square` and receive their own Black Square workspace.

### Changed
- Renamed the daily **Rambam 3 Chapters** output label to **Rambam** while retaining the existing Rambam calendar aliases for source discovery.
- `quarries-black-square` recognizes both new `Rambam` ZIP names and legacy `Rambam-3-Chapters` ZIP names.
- Black Square validation failures now warn and continue instead of aborting the remaining daily studies.

### Pipeline
The daily workflow now supports:

- Daf Yomi
- Tanakh Yomi
- Rambam
- Mishnah

Each extracted study is analyzed by Quarries, exported as a Hebrew study ZIP, and can then be processed into the BSTM adversarial manual, defense manual, and shared source appendices.

## 2026-10-02

- Replaced mixed BSTM rulebook generation with ten paired second-person adversarial commands and mechanism-focused defenses in separate manuals.
- Centralized generation instructions in `BSTM_CODEX_PROMPT.md`; added `bstm.py` prompt rendering and output-structure validation.
- Moved shared source discipline, lexical mismatch notes, glossary, numerical field, chronology, gematria registers, and references into one shared appendix per study.
- Rewrote the existing Bekhorot 13 and II Chronicles 34:2–35:5 manuals under `exports/bstm-2026-10-01/`, preserving their exported sources and technical registers.

## 2026-10-01

### Added
- Added `quarries-daily` CLI for downloading and analyzing Daily Sefaria studies.
- Added support for Daf Yomi and Tanakh Yomi daily Hebrew/Aramaic exports.
- Added Rambam 3 Chapters calendar matching logic with broader Daily Sefaria discovery.
- Added Hebrew-focused study ZIP exports with Quarries whole-study analysis.
- Added dated Desktop workspaces under `~/Desktop/Quarries-Daily-YYYY-MM-DD/`.
- Added `quarries-black-square` workflow for extracting each study ZIP into its own workspace.
- Added automatic detection of the exported `analysis.md` file as the primary BSTM analysis source.
- Added Codex integration for generating:
  - `BLACK_SQUARE_RULEBOOK.md`
  - `BLACK_SQUARE_DEFENSE.md`
- Added BSTM rulebook prompting with transliteration, gematria, symbolic sequences, numbered laws, practical defenses, adversarial red-team sections, and defense cross-references.
- Added Codex `workspace-write` sandbox support and `--skip-git-repo-check` for standalone Desktop study workspaces.

### Changed
- Daily Sefaria CLI now mirrors the web app's `/api/sefaria/analyze` flow.
- Daily study output is organized into separate per-study workspaces instead of loose files.
- BSTM processing now analyzes the exported Markdown study document rather than the entire extracted archive indiscriminately.

### Fixed
- Fixed incorrect CLI analysis endpoint usage.
- Fixed Sefaria analysis payload shape to send `segments` directly, matching `analyzeEntireSefaria()`.
- Fixed empty CLI script/wrapper issues.
- Fixed Codex failures caused by untrusted non-Git workspaces.
- Fixed Codex read-only execution by enabling workspace write access.

## v0.10.10 - 2026-09-29

- Added an in-app Sefaria manuscript gallery.
- Added manuscript image thumbnails with full-size in-app viewer.
- Added previous/next manuscript page navigation.
- Added manuscript metadata including title, Hebrew title, anchor ref, page ID, description, source, and discovery ref.
- Added manuscript discovery for Sefaria Sheets by expanding sheet source refs instead of querying the sheet ID directly.
- Added progressive manuscript discovery with `Scan More` across broader Tanakh reference batches.
- Added browser-side manuscript gallery caching and cache reset controls.
- Added direct manuscript API search by Sefaria textual reference.
- Added separate gallery modes for individual Pages and grouped Collections.
- Changed manuscript gallery cards to a horizontal layout for better use of the Sefaria center pane.
- Added gallery filtering for discovered manuscripts and pages.
- Improved deduplication of discovered manuscript pages by manuscript slug, page ID, and image URL.

## v0.10.9 - 2026-09-29

- Fixed Sefaria Sheet handling so `Sheet ####` references use the Sheets API instead of the Texts v3 endpoint.
- Added Sefaria Sheet normalization into Hebrew/English study segments.
- Added whole-study Sefaria analysis with `Analyze Entire Study + Save` and `Inspect Entire Study`.
- Added Strong's / Hebrew lexicon candidate data alongside Gematria analysis for Sefaria whole-study exports.
- Preserved closest-percentage lexical matching and candidate confidence information.
- Added browser-download workflow for completed Sefaria study analysis.
- Updated Sefaria exports to include full-study structured analysis rather than only the last clicked word.
- Fixed Dock launcher targeting so `/Applications/Quarries.app` launches the current `~/Applications/quarries` v0.10.7 runtime.
- Improved Sefaria Sheet error handling for unavailable, private, or stale sheet IDs.
- Confirmed live Sefaria Online access from the local Quarries application.


## v0.10.8 - 2026-09-25

- Restored Parashah browser-save workflow.
- Analyze Entire Portion + Save now automatically downloads the completed analysis through the browser.
- Removed the redundant separate Export Portion button.
- Preserved local Parashah research archival saves.
- Fixed Quarries package launch/runtime path so bundled TorahCalc reference data resolves correctly.
- Restored Gematria reference lookups used by Parashah analysis and Tanakh word studies.
