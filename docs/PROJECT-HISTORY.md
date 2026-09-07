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

