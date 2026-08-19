---
name: Quarries v0.5 Hebrew + Embedding Roadmap
about: Private development checklist for the v0.5 research layer
---

## P0
- [ ] Verify the bundled Hebrew Fuzzy/Strong's source and licensing before redistribution.
- [ ] Preserve `gloss`, `definitions`, and `notes` verbatim; never overwrite them during future Strong's imports.
- [ ] Import a verse-tagged Hebrew Tanakh corpus into the currently empty `verses` table.
- [ ] Add token-level verse morphology / Strong's mappings where the source license permits.
- [ ] Complete EmbeddingGemma migration and force stale Nomic indexes to rebuild.

## P1
- [ ] Add Hebrew root-family exploration.
- [ ] Add surface-form → lemma → Strong's → verse-context translation workbench.
- [ ] Add lexical evidence to Watcher prompts with explicit source labels.
- [ ] Add retrieval threshold and per-Leaf diversity to semantic RAG.
- [ ] Add RAG/index diagnostics screen.

## P2
- [ ] Add exact-vs-semantic Archive search toggle.
- [ ] Add Watcher citations back to Leaves and lexical entries.
- [ ] Add local lexicon update/import command with provenance and schema versioning.

## Privacy requirement
This roadmap assumes the repository remains private. Do not publish archive data, user definitions, notes, exports, or private lexicon modifications.
