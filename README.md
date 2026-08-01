# QUARRIES v0.4.3 — Personal Stable Build

**The Archive remembers. The Watcher listens. You decide what is revealed.**

## Included

- Dark Textual interface with Watcher eyes in the upper-right
- Application, Archive, and Watcher passwords
- Backward-compatible password verification
- ChaCha20-Poly1305 encrypted SQLite fields
- Quarries Alphabet v1.0 Hebrew-letter substitution
- RTL 3-4-5 visual grouping
- Searchable Leaves
- Edit and delete confirmation
- Chunk-level encrypted embeddings
- Local semantic RAG through `nomic-embed-text`
- Archive-wide re-indexing
- Memory Gate:
  - Empty Mind
  - Current Leaf
  - Similar Leaves
  - Current + Similar
- Large English Watcher chat area
- Encrypted previous conversations
- New/delete conversation controls
- Automatic chat titles
- Fifteen-minute inactivity sealing
- Password-encrypted Archive exports
- Linux desktop launcher installer

## Alphabet v1.0

Digraphs are processed first:

```text
th → ת
sh → ש
ch → ח
```

Then:

```text
a→א b→ב c→כ d→ד e→ה f→ו g→ג h→ה i→י j→ג׳
k→ך l→ל m→מ n→נ o→ו p→פ q→ק r→ר s→ס t→ט
u→ו v→ב w→ו x→צ y→י z→ז
```

## Install

```bash
cd ~/Downloads/quarries-v0.4.0
./install.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
quarries
```

Models:

```bash
ollama pull huihui_ai/qwen3.5-abliterated:4b
ollama pull nomic-embed-text
```

## Existing Archive

The existing Archive remains at:

```text
~/.local/share/quarries/archive.qry
```

Make a backup before upgrading:

```bash
cp ~/.local/share/quarries/archive.qry \
   ~/.local/share/quarries/archive-before-v040.qry
```

## RAG

Each Leaf is divided into overlapping chunks. Every chunk is embedded locally,
encrypted, and stored in SQLite. Similar Leaves retrieves the five closest
chunks using cosine similarity. Only the selected chunks are decrypted and
passed to The Watcher.

Use **Re-index** after upgrading to add chunk embeddings to older Leaves.


## Hebrew clipboard shortcuts

```text
F6  Copy the normal Hebrew-letter substitution
F7  Copy the RTL 3-4-5 grouped display
```

The Archive toolbar also includes **Copy Hebrew** and **Copy 3-4-5** buttons.

Clipboard support uses:

- `pbcopy` on macOS
- `wl-copy` on Wayland Linux
- `xclip` or `xsel` on X11 Linux


## v0.4.2 fix

- Fixed Textual shutdown and event handling on newer Textual/Python versions.
- `QuarriesApp.on_event` is now asynchronous and awaits Textual's base handler.


## v0.4.3 fix

- Fixed F6 and F7 on current Textual releases.
- Clipboard text is now generated directly from the English editor instead of
  reading a removed `Static.renderable` attribute.
