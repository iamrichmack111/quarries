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
