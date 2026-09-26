# Future Crash + LOOK 6.8.0 · MODEL GROUND TRUTH

6.8.0 joins model testing, curation, runtime defaults, routing, and observability around one principle: model choice should come from measured deployment evidence rather than historical names.

## Role-based defaults

Future Crash asks the local Fabric curator for the BALANCED role. Signal Window asks for REFLEX. Explicit `--model` and runtime model changes remain authoritative. If the node is unavailable, both surfaces fall back gracefully to existing LOOK selection and finally the compatibility model.

## Explainable routing

`lk fabric route reflex|balanced|deep` prints the selected deployment and alternatives using the same score components as production routing. It does not submit work or change residency.

## Evidence freshness

Benchmarks are fresh for seven days, aging through thirty days, and stale after thirty days. Stale evidence remains visible but is marked as such so a machine can be retested instead of silently treating old measurements as current truth.

## Dash

The Fabric dashboard now shows curator mode, role profile, and target resident set alongside model residency and qualification evidence.
