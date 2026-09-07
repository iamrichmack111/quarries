# GitHub setup

Repository: `iamrichmack111/quarries` (keep private).

## Metadata and topics

```bash
./github_metadata.sh
```

## Initialize / refresh the Wiki

```bash
./scripts/init_wiki.sh
```

## CI/CD

- `CI`: tests Python 3.10/3.12 on Ubuntu and macOS, then builds Python artifacts.
- `Docker / GHCR`: publishes a private image to `ghcr.io/iamrichmack111/quarries` on `main` and version tags.
- `Release`: tags such as `v0.9.2` create Python distributions, source ZIPs, and a GitHub Release.

## Push a release

```bash
git add .
git commit -m "Release Quarries v0.9.2 desktop app, CI/CD, Docker and docs"
git push origin main
git tag -a v0.9.2 -m "Quarries v0.9.2"
git push origin v0.9.2
```
