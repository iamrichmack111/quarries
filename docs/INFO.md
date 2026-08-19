# Quarries 0.7.3 — Architecture and Release Information

## Modules
- Application gate: shell access only.
- Archive: encrypted Leaves, semantic indexing, exports.
- Watcher: encrypted local AI conversations.
- Hebrew / Strong's: read-only lexical reference + user study list + Mispar Gadol.
- Observatory: deterministic Swiss Ephemeris calculations only; no LLM bridge.

## Models
- General Watcher: `huihui_ai/qwen3.5-abliterated:4b`
- Reference Context: `gemma3:4b`
- Embeddings: `embeddinggemma`

## Security
Argon2id key derivation and ChaCha20-Poly1305 encrypted fields. Application, Archive, and Watcher remain independently locked. Lock All / Ctrl+L clears in-memory keys.

## Hebrew data
The packaged lexicon currently contains 8,674 lexical entries and no complete verse corpus.

## 0.7.3 release focus
- Consolidated README.
- Added `quarries(1)` man page.
- Added global installer.
- Added GitHub metadata helper.
- Retained live Mispar Gadol and MacBook-friendly Hebrew layout.
- Retained Observatory as calculation-only.
