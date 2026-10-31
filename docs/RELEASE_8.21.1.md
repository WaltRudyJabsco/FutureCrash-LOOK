# 8.21.1 — Classroom prompt repair

Bundle/node/Albert integration **8.21.1**; LOOK **4.68.1**.

Latin's Words path could fail with `AttributeError: module __main__ has no
attribute look_renderer`. The same dependency mistake affected practice,
search and settings input. Latin now imports its renderer directly. Wiki's
prompts and article copy action receive the same repair.

The source course, learner progress, reading positions and review records are
unchanged. New tests exercise prompt paths through the actual LK module and
enter/cancel search in a real terminal.

Validation: 134 affected tests passed, including Words/practice/filter prompts,
Wiki setup/copy paths and real-terminal search entry/cancellation and restoration.
