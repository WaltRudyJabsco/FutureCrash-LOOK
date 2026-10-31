# 8.26.0 — Curated visuals and Haunted Hollow

Bundle/node/Albert integration **8.26.0**; LOOK **4.73.0**.

Capital V opens a shared checkbox picker in `lk player`, MP and TV results.
Arrows move; Shift-arrows page/jump; Space toggles; a selects all; n selects none;
Enter saves atomically; Escape cancels. `lk visualizers` and Settings expose the
same picker. MP/TV text entry keeps V literal; Media Find's V source-view shortcut
remains unchanged.

Lowercase v and the ten-second Cycle both skip disabled entries. Normal view is
always reachable, including when no visuals are enabled. Disabled stable names
live in `~/.config/look/visualizers.json`, shared across terminal implementations
for the local OS account. Other player panes refresh within a second, without
reading the configuration on every animation frame. New visuals start enabled.
Selections are per computer; this does not introduce a Fabric preference-sync
protocol. Playback and queue controls stay independent of the picker.

**Haunted Hollow** adds a moonlit graveyard, fluttering bats and quietly glowing
jack-o'-lanterns. It is ambient animation, freezes while paused and participates
in the curated rotation year-round. Full-screen visual controls wrap to width.

Validation: **655 affected tests passed**, covering selection persistence, manual
and timed cycles, all/none, malformed settings, cancel semantics, frame bounds,
pause, media search and transport. A real 40-column PTY in a fresh temporary
account verified checkbox save, Escape cancellation and the persisted JSON view.
Generated references, shell syntax, installer dry-run and diff checks passed.
