# Quarries CI/CD

Quarries uses GitHub Actions for three independent delivery paths: verification, container publication, and tagged releases. The workflows are intentionally separated so a failing test blocks packaging while release and GHCR permissions remain narrowly scoped.

## Pipeline map

The editable D2 source is [`cicd.d2`](cicd.d2). The system architecture remains in [`architecture.d2`](architecture.d2).

```text
Developer push / pull request
          |
          v
       CI workflow
     /      |       \
Linux     macOS    package
 tests      tests    build
  |          |        |
  +----------+--------+
             |
             v
          main/tag
          /      \
         v        v
     Docker      Release
      GHCR     wheel/sdist/zip
```

## CI — `.github/workflows/ci.yml`

Triggers on pushes to `main`, pull requests, and manual dispatch.

- Tests Python 3.10 and 3.12 on Ubuntu and macOS.
- Runs the full `pytest` suite.
- Performs an import smoke test of the Flask GUI, Textual TUI, gematria, and Observatory modules.
- On macOS, builds `Quarries.app` and verifies that `CFBundleExecutable` exists and is executable. This specifically protects against desktop bundle regressions.
- Builds wheel and source distribution artifacts after tests pass.

## Docker / GHCR — `.github/workflows/docker.yml`

Triggers on pushes to `main`, version tags, and manual dispatch.

- Uses Docker Buildx with GitHub Actions cache.
- Publishes `ghcr.io/iamrichmack111/quarries`.
- Emits `latest` for the default branch, tag names for releases, and immutable SHA tags.
- Uses `GITHUB_TOKEN` with only `contents:read` and `packages:write`.

The repository and GHCR package should remain private unless the owner explicitly changes visibility.

## Release — `.github/workflows/release.yml`

Triggers only when a `v*` tag is pushed.

- Builds wheel and source distribution.
- Creates a source ZIP directly from Git, excluding untracked runtime state.
- Creates/updates the GitHub Release and generates release notes.

## Recommended release sequence

```bash
pytest -q
git status
git add .
git commit -m "Release Quarries vX.Y.Z"
git push origin main
git tag -a vX.Y.Z -m "Quarries vX.Y.Z"
git push origin vX.Y.Z
```

Before tagging, update `CHANGELOG.md` and the version in `pyproject.toml`.

## Secrets and privacy

No Archive database, password, key, Watcher conversation, export, or user runtime directory should be committed or uploaded as a CI artifact. CI operates only on repository fixtures and bundled reference databases.
