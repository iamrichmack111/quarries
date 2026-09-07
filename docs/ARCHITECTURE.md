# Quarries architecture

The canonical architecture definition is [`architecture.d2`](architecture.d2). It is intentionally kept as source so the diagram can be regenerated whenever the system changes.

Render locally with D2:

```bash
d2 docs/architecture.d2 docs/architecture.svg
```

## Trust boundaries

Quarries has three independent authentication gates: Application, Archive, and Watcher. Decryption keys remain process-memory state and are not written to browser cookies. The personal Archive database lives outside the installed application tree at `~/.local/share/quarries/archive.qry`.

The Flask GUI defaults to loopback only. Docker explicitly binds the host side to `127.0.0.1:8787`; this preserves the local-only design while allowing the process inside the container to listen on `0.0.0.0`.

## Deterministic vs AI components

Hebrew lookup, gematria, TorahCalc reference lookups, encryption, storage, and Swiss Ephemeris chart calculations are deterministic code paths. Watcher interpretation and semantic retrieval are the AI-assisted paths and use local Ollama models.

## Delivery architecture

CI/CD is documented separately in [`CI-CD.md`](CI-CD.md), with editable D2 source in [`cicd.d2`](cicd.d2). The macOS installer places the application bundle at `/Applications/Quarries.app` while keeping the runtime under the user's Library and personal data under `~/.local/share/quarries`.
