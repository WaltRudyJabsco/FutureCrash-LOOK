# Fabric Pulse architecture

The fabric has three primitives, intentionally kept separate.

1. **Events are immediate.** Requests, tokens, tool results, completion and cancellation do not wait for a clock tick.
2. **Jobs hold leases.** A lease names owner, priority, phase, worker and last meaningful progress. Human work outranks ambient work.
3. **Pulse reconciles truth.** Once per second each node rechecks progress age, model state and peer advertisements. The pulse is a metronome, not a conductor.

The design avoids a permanent master. Every machine runs the same node. A request origin can select any eligible worker from fresh advertisements. Capability is a hard filter; measured latency/load/residency are later scheduling preferences.

## Model evidence

A model profile is deliberately multidimensional:

- declared: capabilities reported by the inference engine;
- operational: resident/warm state and hardware placement;
- qualified: tiny node-local self-test evidence;
- observed: real-job timing history (next layer).

The network should never collapse this into one grade. A fast text router and a slower vision model are useful for different jobs.

## Recovery law

Elapsed time alone never proves a job is dead. The supervisor watches time since meaningful progress. A pulse can mark work quiet/stale and trigger reconciliation. Executor-specific cancellation/termination remains an explicit edge so a generic supervisor never blindly kills an unrelated process.
