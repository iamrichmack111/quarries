#!/usr/bin/env bash
set -euo pipefail

REPO="iamrichmack111/quarries"

echo "==> Configuring GitHub repository metadata for $REPO"

gh repo edit "$REPO" \
  --description "Private encrypted research workspace with local AI, Hebrew and Strong's study, gematria, RAG, Swiss Ephemeris, Flask, macOS desktop support, and Docker." \
  --enable-wiki=true

echo "==> Setting repository topics"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/$REPO/topics" \
  -f 'names[]=python' \
  -f 'names[]=flask' \
  -f 'names[]=textual' \
  -f 'names[]=sqlite' \
  -f 'names[]=encryption' \
  -f 'names[]=local-ai' \
  -f 'names[]=ollama' \
  -f 'names[]=rag' \
  -f 'names[]=embeddings' \
  -f 'names[]=hebrew' \
  -f 'names[]=gematria' \
  -f 'names[]=strongs-concordance' \
  -f 'names[]=swiss-ephemeris' \
  -f 'names[]=astrology' \
  -f 'names[]=research-tools' \
  -f 'names[]=privacy' \
  -f 'names[]=docker' \
  -f 'names[]=github-actions' \
  -f 'names[]=macos' \
  -f 'names[]=terminal-ui'

echo
echo "==> Current repository metadata"

gh repo view "$REPO" \
  --json nameWithOwner,description,visibility,repositoryTopics
