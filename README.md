# Quarries v0.7.3

**The Archive remembers. The Watcher listens. You decide what is revealed.**

Quarries is a private terminal research workspace that combines an encrypted personal Archive, local semantic retrieval, a local AI Watcher, a preserved Hebrew/Strong's lexical database with custom glosses, Mispar Gadol gematria, saved Hebrew study lists, and a local Swiss Ephemeris Observatory.

Quarries is designed to keep deterministic data and private writing local. The Observatory remains a calculation tool and is intentionally **not** sent to the Watcher.

## Highlights

### The Archive
- Password-protected encrypted Leaves stored in SQLite.
- ChaCha20-Poly1305 encrypted text fields.
- Searchable/editable personal notes.
- Quarries Hebrew-letter substitution and RTL 3-4-5 rendering.
- `F6` copies the Hebrew substitution.
- `F7` copies the RTL 3-4-5 view.
- Local semantic indexing with `embeddinggemma`.
- Model/dimension/index-version metadata prevents incompatible embedding spaces from being mixed.
- Re-index support for stale or previous-model embeddings.
- Password-encrypted `.qryx` Archive exports.

### The Watcher
- Separately password-protected local conversation workspace.
- Default chat model: `huihui_ai/qwen3.5-abliterated:4b`.
- Reference-context model: `gemma3:4b`.
- Local Ollama inference; no hosted LLM is required.
- Similar-Leaf retrieval from the encrypted Archive.
- Visible Reference Context for intentionally shared material.
- `F8` copies the most recent Watcher response.

### Hebrew / Strong's
- Bundled local Hebrew Fuzzy lexicon with **8,674 entries**.
- Search by Hebrew, Strong's `H####`, transliteration, pronunciation, gloss, or definition.
- Niqqud/cantillation-insensitive Hebrew matching.
- Preserved custom `gloss`, `definitions`, and `notes`.
- Mispar Gadol shown with dictionary entries.
- Live Mispar Gadol calculator: paste or type Hebrew and it calculates immediately.
- Final-letter values: `ך=500`, `ם=600`, `ן=700`, `ף=800`, `ץ=900`.
- Persistent saved-word study list.
- CSV export with Hebrew, Strong's ID, transliteration, morphology, custom gloss, definitions, notes, Mispar Gadol, and save time.
- Hebrew lexical entries can be intentionally sent to Watcher as Reference Context.

> The bundled Hebrew database currently contains lexical entries but no complete Strong's-tagged verse corpus. Quarries does not claim to include a complete interlinear Tanakh.

### Observatory
The Observatory uses Swiss Ephemeris locally and remains independent of the Watcher.

It calculates current/event and natal/birth charts, Tropical and Sidereal zodiac modes, multiple sidereal references, multiple house systems, planetary and node positions, Ascendant/Descendant, MC/IC, house cusps, retrograde motion, sign element/modality/polarity, traditional essential dignity, major/selected minor aspects, Moon phase/illumination, and sunrise/sunset for supplied coordinates/timezone.

Location is entered as latitude, longitude, and an IANA timezone such as `America/New_York`. Coordinates are the geographic location; the timezone identifier is only the local clock rule.

## Security model

Quarries uses three independent gates:

1. **Application password** — enters the Quarries shell.
2. **Archive password** — unlocks encrypted Leaves and Archive retrieval.
3. **Watcher password** — unlocks encrypted Watcher conversations.

The Archive and Watcher do not automatically unlock when the application gate opens.

`Ctrl+L` or the visible **Lock All** button clears the active application, Archive, Watcher, and ephemeral Reference Context keys from memory and returns to the application gate.

Auto-lock defaults to 10 minutes and can be configured for 1, 5, 10, 15, 30, or 60 minutes.

## Local data

The primary Quarries SQLite database is stored under:

```text
~/.local/share/quarries/archive.qry
```

Back up the Archive before major upgrades:

```bash
cp ~/.local/share/quarries/archive.qry ~/.local/share/quarries/archive-backup-$(date +%Y%m%d-%H%M%S).qry
```

## Requirements

- macOS or Linux
- Python 3.10+
- Ollama for Watcher/RAG features

Install the local models:

```bash
ollama pull huihui_ai/qwen3.5-abliterated:4b
ollama pull gemma3:4b
ollama pull embeddinggemma
```

## Install

```bash
chmod +x install.sh
./install.sh
```

The installer creates an isolated virtual environment, installs Quarries, places a global launcher in `/usr/local/bin` when possible, installs the `quarries(1)` man page, and falls back to `~/.local/bin` if system installation is unavailable.

Launch from any directory:

```bash
quarries
```

Read the manual:

```bash
man quarries
```

### Why `/usr/local/bin` instead of `/bin`?

On modern macOS, `/bin` is protected by System Integrity Protection and is reserved for operating-system commands. `/usr/local/bin` is the standard location for user-installed command-line programs.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Ctrl+L` | Lock all modules |
| `Ctrl+N` | New Leaf |
| `Ctrl+S` | Preserve Leaf |
| `F6` | Copy Hebrew substitution |
| `F7` | Copy RTL 3-4-5 |
| `F8` | Copy latest Watcher response |
| `Ctrl+Q` | Quit |

## Mispar Gadol example

```text
שלום
ש(300) + ל(30) + ו(6) + ם(600) = 936
```

Niqqud and cantillation are ignored.

## Privacy

Do not commit your personal `archive.qry`, `.qryx` exports, passwords, or private records. Review redistribution rights for any bundled lexical/reference data before making the repository public.

## Current limitations

- The packaged Hebrew lexicon does not yet include a complete Strong's-tagged Tanakh verse/token corpus.
- Observatory calculations are local; Quarries intentionally does not generate LLM astrology interpretations.
- Ollama must be running for Watcher and embedding features.

## Repository metadata

Suggested GitHub description:

> Private encrypted research workspace with local AI, Hebrew/Strong's study, Mispar Gadol, semantic RAG, and Swiss Ephemeris charts.

Suggested topics:

`python`, `textual`, `sqlite`, `encryption`, `privacy`, `local-ai`, `ollama`, `rag`, `embeddings`, `embeddinggemma`, `hebrew`, `strongs-concordance`, `gematria`, `mispar-gadol`, `swiss-ephemeris`, `astronomy`, `astrology`, `terminal-ui`, `research-tools`, `knowledge-management`

See `GITHUB.md` for commands.
