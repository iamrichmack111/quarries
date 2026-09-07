# Installation

## macOS desktop app

```bash
chmod +x install.sh
./install.sh
```

The installer deploys a standalone Quarries runtime under `~/Library/Application Support/Quarries/runtime`, installs `/Applications/Quarries.app`, and creates a CLI launcher. Personal data remains under `~/.local/share/quarries/archive.qry`.

Required Ollama models:

```bash
ollama pull huihui_ai/qwen3.5-abliterated:4b
ollama pull gemma3:4b
ollama pull embeddinggemma
```
