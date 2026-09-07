# macOS Desktop App

Quarries installs as a normal macOS application at:

```text
/Applications/Quarries.app
```

The app bundle contains its `.icns` icon and launches the stable Python runtime at:

```text
~/Library/Application Support/Quarries/runtime/
```

Personal Quarries data remains separate at:

```text
~/.local/share/quarries/archive.qry
```

Install or repair with:

```bash
chmod +x install.sh
./install.sh
```

The installer refreshes LaunchServices after copying the bundle. The GUI entry point is `quarries.webapp:main`; `quarries-tui` remains available for the Textual interface.
