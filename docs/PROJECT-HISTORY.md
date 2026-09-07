# Quarries Project History

This is a retrospective engineering history of Quarries.

The project existed before formal GitHub issue tracking was introduced. The
entries below document major milestones that were already implemented.

These are explicitly historical backfill records. Original Git timestamps and
existing repository history have not been rewritten.

Quarries evolved from an encrypted terminal research environment into a
local-first multi-interface research platform containing deterministic research
tools, local AI, encrypted storage, Flask, a macOS desktop launcher, Docker,
and automated CI/CD.

---


## #1 — Establish the Quarries local-first research architecture

**Status:** Completed — historical backfill

Established the original Python and Textual-based Quarries architecture, local-first data model, modular research workspaces, and separation between deterministic research functions, personal data, and optional local AI.

Related issue: #1

---


## #2 — Implement independent Application Archive and Watcher security gates

**Status:** Completed — historical backfill

Implemented independent Application, Archive, and Watcher authentication gates. Application authentication does not implicitly unlock Archive or Watcher. Lock All clears active cryptographic keys and ephemeral Reference Context.

Related issue: #2

---


## #3 — Build encrypted Archive storage for research Leaves

**Status:** Completed — historical backfill

Implemented SQLite-backed encrypted research Leaves using Argon2id password derivation and ChaCha20-Poly1305 authenticated encryption, with search, editing, deletion, and persistent storage separate from application upgrades.

Related issue: #3

---


## #4 — Implement encrypted QRYX Archive exports

**Status:** Completed — historical backfill

Implemented password-encrypted QRYX Archive exports for portable backups and transfers without exposing plaintext Archive contents.

Related issue: #4

---


## #5 — Add Hebrew-letter substitution and RTL 3-4-5 transformations

**Status:** Completed — historical backfill

Implemented Quarries-specific English-to-Hebrew-letter substitution and right-to-left 3-4-5 transformation functionality for Archive research.

Related issue: #5

---


## #6 — Add semantic embeddings and RAG retrieval

**Status:** Completed — historical backfill

Added embeddinggemma-powered semantic retrieval, similar-Leaf search, RAG context generation, embedding model and dimensionality metadata, index versioning, and Archive re-index support.

Related issue: #6

---


## #7 — Build Watcher local AI research assistant

**Status:** Completed — historical backfill

Implemented the local Ollama-powered Watcher research assistant with huihui_ai/qwen3.5-abliterated:4b, gemma3:4b Reference Context support, Archive RAG retrieval, and Textual response-copy functionality.

Related issue: #7

---


## #8 — Implement ephemeral Watcher Reference Context

**Status:** Completed — historical backfill

Implemented explicitly staged and ephemeral Watcher Reference Context. Research material is supplied to the AI intentionally rather than automatically, and Lock All clears the staged context.

Related issue: #8

---


## #9 — Bundle Hebrew and Strong's lexical research database

**Status:** Completed — historical backfill

Added the bundled Hebrew lexical research database with approximately 8,674 entries supporting Strong's H-number search, Hebrew, transliteration, pronunciation, glosses, definitions, notes, study lists, CSV export, and Watcher staging.

Related issue: #9

---

