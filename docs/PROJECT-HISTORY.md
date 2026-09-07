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


## #10 — Implement Mispar Gadol final-letter values

**Status:** Completed — historical backfill

Implemented explicit Mispar Gadol final Hebrew letter values: final kaf 500, final mem 600, final nun 700, final pe 800, and final tsadi 900.

Related issue: #10

---


## #11 — Build local Gematria Dictionary from research corpus

**Status:** Completed — historical backfill

Built the structured local Gematria Dictionary with deterministic numeric lookup, source-page provenance, SQLite full-text concept search, and local related-concept similarity while keeping semantic matches separate from exact numeric matches.

Related issue: #11

---


## #12 — Implement multi-method deterministic gematria calculator

**Status:** Completed — historical backfill

Implemented Hechrachi, Gadol, Siduri, Katan, Perati, Shemi, Musafi, Bone'eh, Kidmi, Ne'elam, Meshulash, Ha'achor, Katan Mispari, Kolel, AtBash, Albam, Ofanim, Avgad, and Reverse Avgad calculations. Arithmetic metadata such as prime factorization and digit reduction remains separately classified.

Related issue: #12

---


## #13 — Build deterministic Swiss Ephemeris Observatory

**Status:** Completed — historical backfill

Implemented the Swiss Ephemeris Observatory with current, event, and natal calculations; tropical and sidereal modes; planets and nodes; retrogrades; ASC, DSC, MC, IC; house cusps; aspects; lunar phase and illumination; sunrise and sunset; and traditional dignity metadata.

Related issue: #13

---


## #14 — Keep Observatory calculations isolated from AI interpretation

**Status:** Completed — historical backfill

Removed automatic chart-to-Watcher interpretation so probabilistic AI output cannot silently replace or distort deterministic Swiss Ephemeris calculations.

Related issue: #14

---


## #15 — Convert Quarries to a Flask graphical interface

**Status:** Completed — historical backfill

Added the Flask graphical interface through quarries.webapp while preserving the original Textual TUI. Added templates, static frontend assets, localhost binding, browser launching, and shared access to existing Quarries functionality.

Related issue: #15

---


## #16 — Replace visible browser prompts with masked password dialogs

**Status:** Completed — historical backfill

Replaced JavaScript password prompts with application-native masked password fields for Archive and Watcher unlock flows, including Enter submission, Escape and Cancel behavior, and password clearing on close.

Related issue: #16

---


## #17 — Package Quarries as a macOS desktop application

**Status:** Completed — historical backfill

Created the Quarries.app desktop launcher with application icon, stable runtime integration, LaunchServices support, runtime logging, and separation between the application bundle and personal research data.

Related issue: #17

---


## #18 — Build Quarries macOS installer and stable runtime

**Status:** Completed — historical backfill

Implemented the macOS installer and stable runtime under Library/Application Support/Quarries, preserving personal Archive data across application upgrades and providing stable GUI and CLI launch paths.

Related issue: #18

---


## #19 — Containerize Quarries with Docker

**Status:** Completed — historical backfill

Added Docker deployment using Python 3.12 slim, a non-root runtime user, persistent application data, health checking, localhost-oriented port publishing, Docker Compose, Ollama host integration, and native build dependencies required by pyswisseph.

Related issue: #19

---


## #20 — Publish Quarries containers to private GHCR

**Status:** Completed — historical backfill

Configured GitHub Actions to build and publish Quarries container images to the private ghcr.io/iamrichmack111/quarries package.

Related issue: #20

---


## #21 — Add GitHub Actions CI matrix

**Status:** Completed — historical backfill

Added GitHub Actions validation across Ubuntu and macOS using Python 3.10 and 3.12, including package installation, pytest, Flask import testing, Textual import testing, and Python distribution builds.

Related issue: #21

---

