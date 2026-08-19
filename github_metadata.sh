#!/usr/bin/env bash
set -euo pipefail
REPO="${REPO:-iamrichmack111/quarries}"
DESCRIPTION="Private encrypted research workspace with local AI, Hebrew/Strong's study, Mispar Gadol, semantic RAG, and Swiss Ephemeris charts."
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required." >&2; exit 1; }
gh auth status >/dev/null
gh repo edit "$REPO" --description "$DESCRIPTION"   --add-topic python --add-topic textual --add-topic sqlite --add-topic encryption   --add-topic privacy --add-topic local-ai --add-topic ollama --add-topic rag   --add-topic embeddings --add-topic embeddinggemma --add-topic hebrew   --add-topic strongs-concordance --add-topic gematria --add-topic mispar-gadol   --add-topic swiss-ephemeris --add-topic astronomy --add-topic astrology   --add-topic terminal-ui --add-topic research-tools --add-topic knowledge-management
gh repo view "$REPO" --json nameWithOwner,description,repositoryTopics,visibility
