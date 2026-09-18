# Fabric Work Packet v1

Future Crash Fabric moves **work**, not prompts. A Fabric Work Packet (FWP) is an
immutable contract that can be submitted locally, forwarded to another trusted node,
stored, replayed, inspected, cancelled, and composed into dependency graphs.

The wire encoding in 4.3 is JSON over HTTP/Tailscale. JSON is not the protocol; the
semantic object is `fwp/1`, so a future CBOR/MessagePack encoding can preserve the same
meaning.

## Core laws

1. Packets are immutable after dispatch. Runtime status belongs to the job ledger.
2. A prompt is an execution detail, never the packet format.
3. Context is a manifest of references. Large bytes belong in content-addressed artifacts.
4. Requirements are hard; preferences are hints.
5. Capability is not authority. Mutating operations require explicit grants and confirmation.
6. Child work may never gain authority or budget merely by delegation.
7. Results carry provenance and point back to the task that caused them.
8. The supervisor remains deterministic. AI is invoked only for work requiring intelligence.
9. Human/interactive work outranks background work.
10. Unknown namespaced extensions must be safely ignorable.

## Packet shape

```json
{
  "fabric": "fwp/1",
  "id": "fwp_...",
  "kind": "task",
  "created": 1789770000.0,
  "origin": "sashas-macbook-air",

  "relationships": {
    "parent": null,
    "root": null,
    "dependencies": [],
    "caused_by": null
  },

  "work": {
    "operation": "model.qualify",
    "objective": "Measure this model on this node",
    "input": {"model": "qwen3.8:27b"},
    "acceptance": {"must_include": ["ok", "total_ms"]}
  },

  "capabilities": {
    "requires": ["ollama", "text"],
    "prefers": ["warm_model"]
  },

  "context": {
    "refs": [],
    "artifacts": [],
    "representations": []
  },

  "execution": {
    "priority": "interactive",
    "deadline": null,
    "cancellable": true,
    "idempotency": "...",
    "budget": {
      "wall_ms": 60000,
      "inference_tokens": 4000,
      "child_jobs": 0,
      "depth": 0,
      "bytes_transfer": 5000000
    }
  },

  "authority": {
    "principal": "user",
    "grants": ["model.qualify"],
    "confirmed_operations": []
  },

  "delivery": {
    "target": "3090",
    "reply_to": null
  },

  "provenance": {},
  "extensions": {}
}
```

Only `task` packets require `work.operation`. Packet kinds are intentionally few:
`task`, `event`, `observation`, `result`, `artifact`, and `control`.

## Runtime state is separate

A task is durable semantic work. An attempt is one execution of that work. A lease is
transient ownership of a scarce execution lane. Events record what happened.

```text
TASK 42
  ├─ attempt 1 @ M3      failed / node disappeared
  └─ attempt 2 @ 3090    ok
       └─ RESULT 91
```

The task never changes identity when an attempt changes worker.

## Dependency graphs

`relationships.dependencies` contains packet/job IDs. A node only starts a queued task
when its local dependencies have completed successfully. This is enough to express a DAG
without inventing an agent conversation protocol.

```text
trace analysis ─┐
code analysis  ─┼─> synthesis
benchmark      ─┘
```

4.3 provides the durable primitive; automatic graph decomposition and cross-node dependency
resolution remain higher-level scheduler behavior.

## Context and artifacts

Packets are capped at 512 KiB on purpose. Large resources should be referenced instead of
copied into every request. The node includes a small SHA-256 content-addressed store:

```text
POST /v1/artifacts
GET  /v1/artifacts/sha256:<digest>
```

An artifact can have several representations (original image, thumbnail, text description,
embedding) while the packet refers to the resource conceptually. Move meaning when possible;
move bytes only when necessary.

## Authority

The packet says both what the system knows how to do and what this request is permitted to
do. In 4.3, service mutation requires `service.control` (or the exact operation) plus the
operation in `confirmed_operations`. Fabric does not expose arbitrary remote shell execution.

Secrets are not packet cargo. A packet may require a capability; the executing node resolves
that capability against its own local secret store.

## Provenance

Result packets include the task parent/root, worker node, software version, and attempt. The
ledger also records timing and event history. This makes work inspectable and replay-friendly
without preserving private model chain-of-thought.

## 4.3 API

```text
POST /v1/jobs                       submit FWP
GET  /v1/jobs                       recent durable jobs
GET  /v1/jobs/<id>                  packet + attempt + result
POST /v1/jobs/<id>/control          cancel
GET  /v1/events?since=<seq>         append-only event tape
POST /v1/artifacts                  store small inline artifact (base64)
GET  /v1/artifacts/sha256:<digest>  retrieve artifact bytes
```

Existing node/model/service endpoints remain available. The new job layer is additive and is
where future distributed cognitive work should converge.

## CLI

```bash
lk fabric jobs [NODE]
lk fabric job [NODE] JOB_ID
lk fabric events [NODE]
lk fabric submit [NODE] fabric.echo hello=world
lk fabric submit [NODE] model.qualify model=qwen3.8:27b
lk fabric packet [NODE] packet.json
lk fabric cancel [NODE] JOB_ID
lk fabric watch
```

`packet` is the escape hatch for the complete FWP schema; `submit` is the convenient human
front-end for simple jobs.

## What 4.3 intentionally does not do

- no arbitrary remote shell
- no distributed consensus or central master
- no giant agent-chat protocol
- no automatic model/router policy yet
- no magical propagation of secrets
- no hidden chain-of-thought packets
- no automatic privilege escalation

The goal is a small, durable substrate. Routing intelligence, task decomposition, learned
performance selection, and richer context resolution can grow on top without changing the
packet's basic meaning.
