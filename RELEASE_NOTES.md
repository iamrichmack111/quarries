# Quarries 0.10.6

Word studies now visibly demonstrate vowel/cantillation removal before Gematria and make correlated Tanakh occurrence verses fully interactive. Occurrence matching now uses complete normalized consonantal segments and is explicitly described as a textual correlation rather than guaranteed lexical identity.

# Quarries 0.10.6

Adds an explicit vowel/mark-removal stage to Hebrew word analysis. Quarries preserves the original pointed Hebrew for reading and lexical context, displays the unpointed consonantal form, and clearly shows the exact text used for every Gematria method. This applies in both Tanakh Reader and weekly Parashah word studies and is included in saved full studies.

# Quarries 0.10.4

Quarries now includes an offline Hebrew/English Tanakh reader integrated with the existing Strong's, fuzzy Hebrew, Gematria, weekly Parashah, and local reference-dictionary tools. Selecting a biblical Hebrew word produces ranked lexical candidates, morphology, other biblical occurrences, all Gematria methods for both the surface form and best lemma, and the associated local reference entries for each value.

# Quarries v0.9.1

- Password entry for Archive and Watcher in the Flask GUI is now masked instead of using a visible-text browser prompt.
- Added an in-app password unlock modal with Enter/Escape/Cancel handling.
- Added `CHANGELOG.md` for cumulative release history going forward.
- Existing encrypted user data and password records remain unchanged.

# Quarries v0.9.0

## Local Flask GUI

- Rebuilt the Quarries interface as a local Flask GUI at `127.0.0.1:8787`.
- Preserves the existing encrypted database at `~/.local/share/quarries/archive.qry`.
- Preserves all three independent passwords and Lock All behavior.
- Carries forward Archive, Watcher/RAG, Hebrew/Strong's, Gematria Dictionary, Observatory and Vault features.
- Bundled Hebrew and TorahCalc SQLite reference databases are unchanged.
- `quarries` / `quarries-web` launch the GUI; `quarries-tui` preserves the original Textual interface.
- macOS Quarries.app now starts the GUI directly without a Terminal window.

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

## Quarries 0.10.1
This release connects Hebrew / Strong's, the Gematria Dictionary, and the weekly Parashah to one enriched Gematria pipeline. Every calculated method can display same-value entries from the local structured TorahCalc reference, including source PDF pages. Research entries can be saved to `~/.local/share/quarries/research/gematria-entries.jsonl`, while whole-Parashah runs are saved under `~/.local/share/quarries/research/parashah/`. Exponents use caret notation such as `2^2` for consistent rendering.
