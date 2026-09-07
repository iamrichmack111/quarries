# Release Process

1. Update `CHANGELOG.md` and version in `pyproject.toml`.
2. Run `pytest -q`.
3. Commit and push `main`.
4. Tag `vX.Y.Z` and push the tag.
5. GitHub Actions builds Python artifacts, a source ZIP, a GitHub Release, and the GHCR container image.
