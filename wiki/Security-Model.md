# Security Model

Quarries uses independent Application, Archive, and Watcher gates. Archive and Watcher do not unlock automatically when the Application gate opens. Password-derived keys are held in process memory only. Lock All clears active keys and transient Reference Context.

Encrypted Archive fields use ChaCha20-Poly1305. Export bundles use the QRYX4 format with a password-derived encryption key.
