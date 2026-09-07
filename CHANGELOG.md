# Changelog

All user-facing Quarries changes are recorded here from v0.9.1 onward.

## v0.9.3 — 2026-09-06

### macOS desktop application
- Moved the installed application bundle from `~/Applications/Quarries.app` to the system `/Applications/Quarries.app` directory.
- Installer now handles administrator privileges when required, removes quarantine attributes, fixes launcher permissions, and refreshes LaunchServices.
- Standardized the desktop launcher around the installed `quarries` entry point backed by `quarries.webapp:main`.
- Added CI validation for the `.app` bundle executable to prevent the missing/misnamed launcher regression seen during v0.9.2 installation.

### CI/CD and architecture
- Added `docs/CI-CD.md` with detailed workflow, permissions, privacy and release documentation.
- Added `docs/cicd.d2`, an editable D2 delivery diagram with GitHub, GitHub Actions, Apple, Linux and Docker icons.
- Expanded architecture documentation to distinguish runtime architecture from delivery architecture.

### Docker / Wiki / documentation
- Added Docker and Compose health checks against `/api/status`.
- Added Wiki pages for the macOS Desktop App and CI/CD pipeline.
- Updated README badges, installation paths, release instructions and v0.9.3 highlights.
- No intentional change to Archive encryption, password verifier formats, personal database location, Hebrew reference data, TorahCalc reference data or Observatory calculations.

## v0.9.2 — 2026-09-06

### macOS application
- Changed the desktop installation to a standalone runtime under `~/Library/Application Support/Quarries/runtime`.
- `Quarries.app` now launches that stable runtime directly instead of relying on a version-numbered Downloads directory or whichever `quarries` happens to be first on `PATH`.
- Preserved and bundled the Quarries `.icns` application icon.
- Added `scripts/build_macos_app.sh` and updated `install.sh` to install/repair the desktop application.

### Documentation / architecture
- Rebuilt `README.md` as detailed project documentation with feature, security, installation, Docker, development, CI/CD, Wiki and release sections.
- Added CI, Docker, Release, Python, macOS and localhost/privacy badges.
- Added canonical D2 architecture source at `docs/architecture.d2` plus a rendered `docs/architecture.svg`.
- Added Wiki seed pages for installation, architecture, security, Docker, development and releases.

### CI/CD / GitHub
- Added cross-platform test/package workflow for macOS and Linux.
- Added tagged-release workflow for source ZIP, wheel and sdist artifacts.
- Added GHCR Docker build/publish workflow.
- Added repository topic/description automation and Wiki enablement.
- Added `scripts/init_wiki.sh` to initialize or refresh the GitHub Wiki.

### Docker
- Added `Dockerfile`, `.dockerignore`, and `docker-compose.yml`.
- Added environment-driven Flask host/port/browser behavior for local desktop and headless container usage.
- Compose binds the host side to `127.0.0.1:8787` by default and persists Quarries data in a named volume.

### Security / compatibility
- Retained the v0.9.1 masked password modal for Archive and Watcher credentials.
- No intentional change to the personal Archive database path, encryption format, password verifier format, Hebrew lexicon, or TorahCalc reference data.

## v0.9.1 — 2026-09-06

### Security / UI
- Replaced the browser `prompt()` used to unlock Archive and Watcher with an in-app password modal.
- Archive and Watcher passwords are now entered through `<input type="password">`, so typed characters are masked.
- Password input is cleared when the modal closes.
- Enter submits the password; Escape and Cancel close the modal without unlocking.

### Project maintenance
- Added this persistent `CHANGELOG.md` so future release changes can be tracked version by version.
- No changes to the encrypted database format, password verifiers, bundled Hebrew data, TorahCalc data, or existing Archive contents.

## [0.9.3] - 2026-09-06

### Fixed
- Capped GitHub repository topics at the supported 20-topic maximum.
- Reworked `github_metadata.sh` to update topics through the GitHub API reliably.
- Repository Wiki initialization remains part of the release workflow.

