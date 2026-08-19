# Quarries v0.5 Private Roadmap

This build adds a read-only Hebrew / Strong's research tab using the uploaded Hebrew Fuzzy v10 database. Its 8,674 `words` rows are bundled unchanged. `gloss`, `definitions`, and `notes` are displayed separately and are never written by Quarries.

The supplied Hebrew Fuzzy database currently contains **0 verse rows**, so v0.5 does **not** claim to include a complete Strong's-tagged Bible. Adding a licensed Hebrew Tanakh / verse-token corpus remains a P0 follow-up.

The embedding default is now `embeddinggemma`. Chunk rows record model name, vector dimension, and index version. RAG skips incompatible vectors and Re-index identifies stale indexes created by a prior model.

Repository/privacy rule: keep the project private and never publish Archive content or custom lexical material without explicit approval.
