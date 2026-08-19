# Quarries v0.8.4

- Added a Hebrew-inspired terminal-safe eye/logo treatment to the top of `man quarries`.
- Kept the full PNG branding in `assets/quarries-logo.png` and the macOS application icon.
- No database migration or reset; existing `~/.local/share/quarries/archive.qry` data remains untouched.

# Quarries v0.8.3

- Added context-aware `F6` clipboard behavior. Hebrew / Strong's copies the selected Hebrew lemma; Gematria Dictionary copies the active Hebrew input or selected value as Hebrew numerals; Archive keeps its existing Hebrew substitution copy action.
- Added a visible **Copy Hebrew [F6]** button to Hebrew / Strong's.
- Added the Hebrew-focused Quarries logo and a macOS `Quarries.app` launcher bundle.
- Updated `install.sh` to install the macOS application in addition to the CLI and man page.
- Documented that the personal `archive.qry` database lives outside the release and is preserved across normal upgrades.

# Quarries v0.8.2

- Strong's entries now display all 19 gematria methods.
- Strong's method calculations can be exported to CSV.
- F9 saves Gematria Dictionary results/calculations.
- Added Hebrew numeral rendering and same-value Strong's/gloss-ranked matches.
- Fixed literal `\\n` sequences in multi-method display.

# Quarries v0.8.1

Release-ready documentation and installation packaging.

## Added
- Consolidated README.
- `quarries(1)` man page.
- Global `/usr/local/bin/quarries` installer with safe fallback.
- Man-page installation.
- `docs/INFO.md`.
- `GITHUB.md`.
- `github_metadata.sh`.
- Safer `.gitignore`.

## Current behavior
- Independent Application / Archive / Watcher locks.
- Lock All / Ctrl+L.
- Huihui default Watcher.
- Gemma 3 4B Reference Context.
- EmbeddingGemma semantic index.
- Hebrew/Strong's custom glosses + live Mispar Gadol.
- Saved Hebrew list + CSV export.
- Local Swiss Ephemeris Observatory.
- No Observatory-to-Watcher interpretation bridge.


## Gematria reference corpus
- Added structured `torahcalc.db`.
- Parsed 1,381 numbered source sections across 1,380 distinct values.
- Added exact gematria-number lookup.
- Added concept/definition FTS search.
- Added source-page provenance.
- Added local related-concept recommendations.
- Added source gematria-method reference view.


## v0.8.1
- Added plain-English number-structure explanation for dictionary values.
- Added digit-reduction chains and prime factorization.
- Added 19 supported gematria methods/transforms.
- Added live Hebrew multi-method calculation.
- Added CSV export for all method results.
- Marked spelling-dependent Shemi/Ne'elam calculations explicitly.
