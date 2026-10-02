# Fabric Memory 5.2

Fabric Memory is a small user-owned memory layer shared by the trusted Future Crash + LOOK fabric.
It is deliberately boring JSON, inspectable from the shell, and separate from model identity.

## Scopes

- `shared` — facts/context any persona may use; replicated across live Fabric nodes.
- `persona:<name>` — durable context for one personality, such as `persona:oracle`; replicated.
- `node:<name>` — machine-local context; never replicated by Fabric sync.

LO's existing candidate/durable memory remains intact and local. Future Crash's old compact memory remains local to that Future Crash instance. 5.2 adds a small replicated layer rather than replacing those systems prematurely.

## Commands

```text
lk memory
lk memory fabric
lk memory shared
lk memory persona oracle
lk memory local
lk memory add-shared TEXT [--importance N]
lk memory add-persona oracle TEXT [--importance N]
lk memory add-local TEXT [--importance N]
lk memory sync
```

Adding `shared` or `persona` memory attempts a bounded sync immediately. `lk memory sync` explicitly reconciles live peers later. Node-scoped items never leave their owner.

## Replication

The local Unified Node exposes `/v1/memory`. Sync pulls shared/persona items from live peers, merges by stable content id and `updated_at`, then pushes the resulting union back. This is not distributed consensus and does not need to be: the personal Fabric is trusted, small, and human-owned.

Memory is context, not authority. A personality cannot gain filesystem or shell power from memory. User/session access profile remains a separate capability boundary.
