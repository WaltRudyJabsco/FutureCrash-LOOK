# Future Crash + LOOK 5.3.0 — Decision Plane

## Mental model

A request for human input is not a blocking prompt. It is a small portable Fabric object with a deadline and an explicit fallback policy. Any trusted surface may answer it; if nobody does, policy decides whether the work continues, defers, or cancels.

```text
uncertainty
   ↓
DecisionRequest
   ├── terminal
   ├── Dash
   └── Signal / browser
        ↓
answer OR deadline
        ↓
normal authorized Fabric continuation
```

## Cheap failure policy

- High-confidence, low-consequence, reversible decisions can act directly.
- Medium uncertainty can be exposed as a tiny choice instead of spending more model work.
- Workspace/Conservative silence defers.
- Power/Unsafe silence may continue only low-consequence reversible work.
- High-consequence or irreversible actions still require explicit confirmation and cancel on timeout.

## OpenJev shadow worker

`core/decision.py` contains an optional client for an OpenJev-compatible `/v1/systemone` service. It is shadow evidence only: Fabric remains fully functional without the service, and the adapter does not install/download model weights. Set `FCL_DECISION_URL` to point at a local decision server.

Useful probes:

```sh
lk fabric ask "Use chapter-12.md?" yes no more
lk fabric decisions
lk fabric answer DECISION_ID yes
FCL_DECISION_URL=http://127.0.0.1:3000 lk fabric decision-shadow \
  "active media session" "Which operation?" next previous stop
```

## Distributed human input

A DecisionRequest is not owned by the terminal that created it. `lk fabric decisions` can see pending Fabric-wide requests, Dash reports pending input and highlights decision events, and Signal renders the newest request as a compact card with node, countdown, choices, and timeout behavior. Answering from Signal resolves the request on the node that owns it.

This makes human judgment a Fabric capability rather than a blocking UI primitive. If no human answers before the deadline, the request's explicit policy resolves it without leaving a hidden prompt wedged in some other terminal.

## Architectural boundary

Renderers never execute selected work. A decision choice may carry a continuation FWP, but resolving the decision only submits that packet back through the existing authorization and job machinery.
