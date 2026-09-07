# CI/CD

Quarries has three GitHub Actions workflows:

- **CI** — Python 3.10/3.12 on macOS and Ubuntu, pytest, import checks, macOS `.app` bundle validation, and Python package build.
- **Docker / GHCR** — Buildx build and publication to the private `ghcr.io/iamrichmack111/quarries` package.
- **Release** — `v*` tags produce a wheel, sdist, source ZIP, and GitHub Release.

The canonical pipeline documentation lives in `docs/CI-CD.md`; editable diagrams are in `docs/cicd.d2` and `docs/architecture.d2`.

## Release

```bash
pytest -q
git add .
git commit -m "Release Quarries vX.Y.Z"
git push origin main
git tag -a vX.Y.Z -m "Quarries vX.Y.Z"
git push origin vX.Y.Z
```

Never add personal Archive data or password material to CI artifacts.
