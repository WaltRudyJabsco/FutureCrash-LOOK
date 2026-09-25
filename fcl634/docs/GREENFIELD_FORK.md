# Greenfield Fork — start over without starting over

This is an experimental brief, not a migration plan for the stable Future Crash + LOOK tree.
The current projects keep their identities:

- **LOOK / `lk`** — Unix-native navigation, inspection, and control. Useful without AI.
- **LO** — the dynamic cognitive work network.
- **Future Crash** — the playful retro ambient workstation and Oracle interface.
- **Signal** — the tiny browser-native visual/conversational instrument.
- **Fabric** — shared plumbing: bounded work, discovery, placement, lifecycle, events, artifacts, and trust metadata.

## Counterfactual question

If we knew at the beginning what we know now, what is the smallest coherent system we would build?
The fork exists to answer that question without destabilizing the successful main project.

## Central experiment

Treat a person's already-awake hardware as one heterogeneous cognitive compute pool.
Discover **capabilities/workers**, not merely Ollama servers.

A worker is a bounded capability offered by some resource:

- small / medium / large language inference
- embeddings, reranking, classification, extraction
- vision, speech, image generation
- filesystem/search/storage
- deterministic CPU work
- CUDA / Metal / WebGPU / WebAssembly work

A computer is a resource pool and may host several simultaneous workers. A 3090 may, when measurements prove it safe, keep both a tiny reflex model and a larger reasoning model resident. Macs advertise a safe inference budget rather than pretending all unified memory is free. Browser/iPhone/iPad workers are ephemeral: useful while present, never owners of critical state.

## Scheduling rule

Choose the smallest sufficient currently-available worker expected to finish useful work soonest.
Placement considers hard capability requirements first, then queue delay, residency/load cost, prompt/context cost, measured latency/throughput, transfer cost, and availability.
Do not distribute work merely because distribution is possible.

## Cognitive model

The system is a juggler, not a permanent giant prompt. Maintain a small active working set: current conversation, current task, a few relevant memories, waiting work, trusted receipts, and transient associations. Let unused state decay. Promote only repeatedly useful evidence into durable memory.

Small models can do cheap cognitive maintenance—intent classification, reference resolution, memory selection, context compression, entity extraction, packet preparation—and escalate compact work to a stronger model only when needed.

## Ephemeral browser workers

Signal is a natural experimental host for attached compute. A capable browser may advertise WebGPU/WebAssembly workers such as embeddings, tiny classifiers, speech, or very small language models. Closing the browser simply expires its lease; unfinished work returns to the pool.

## Trust and provenance

Facts and expression are different products. Deterministic/source-backed capabilities emit receipts. Model synthesis is explicitly inferred. UIs may render provenance quietly, but the distinction lives in structured data rather than model prose.

## Demo / Show Work

The best demonstration exposes observable construction rather than hidden model reasoning:

1. user request
2. capability/source receipt
3. work placement across nodes/workers
4. model/capability events
5. Signal primitive program / artifact creation
6. result returns to the requesting interface

A Signal drawing is especially useful: the renderer knows only primitive drawing operations; it does not know what weather, Portland, or a cloud means. Asking for the same facts with a strange visual constraint makes retrieval-vs-composition visible.

## Ambient observability

Dash/Signal may render real Fabric events as restrained colors. This is peripheral vision as telemetry, not decorative animation. Production Dash keeps this passive and optional; theatrical synchronized demos belong in a separate demo surface.

## Rules

Use what is already awake.
Load as little as possible.
Move as little data as possible.
Spend the smallest sufficient intelligence.
Lose any worker without losing the thought.
