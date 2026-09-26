# 5.4.2 — Island Resilience + Workstation Editor

Future Crash + LOOK now treats single-node autonomy as a release invariant. `lk doctor island` audits only loopback/local capabilities so an M-series Mac can be tested with Wi-Fi/Tailscale absent without looking like a broken distributed system. Deterministic LOOK remains useful even with no model; local Ollama, memory, media, and OpenJev are reported independently.

Future Crash Ask and Workstation input now use a single logical buffer/cursor renderer. The full editor row is redrawn from state on every frame, including a horizontally scrolling viewport for long input. Backspace/Delete and left/right/Home/End editing therefore cannot drift into terminal padding or leave deleted glyphs behind.

All public command surfaces are synchronized: `lk help`, starter help, canonical command registry, Zsh completion, README, command reference/grammar, man page, architecture notes, changelog, and release history.
