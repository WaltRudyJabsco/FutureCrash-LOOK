# 8.21.0 — Offline Latin classroom

Bundle/node/Albert integration **8.21.0**; LOOK **4.68.0**.

`lk latin` provides a complete offline classical Latin study environment, with
pronunciation and all 79 lessons from D'Ooge's Latin for Beginners, its connected
readings, three appendices, index and dictionaries. The attributed source and
Project Gutenberg licence are retained in a separate data-only module.

LOOK adds 80 concept checks, 474 typed morphology cards and 481 source-vocabulary
cards. Checked exercises, self-rated vocabulary and open-ended textbook exercises
are distinguished explicitly. Optional macrons and listed inflectional alternatives
are supported. There is no AI answer checker, speech or network dependency.

The classroom uses existing LOOK palettes, selection, Unicode input and arrow/
Shift-arrow controls. Reading positions, study marks and spaced-review progress
stay local and outside runtime updates; export is explicit and non-overwriting.
Installer, completion, generated help/reference and man page include the command.

See [Latin](LATIN.md) for controls, assessment boundaries, source attribution and
course coverage.

Validation: 132 affected tests passed, including the real terminal lesson/paging/
study-mark/exit round trip, source integrity and course/card coverage, inflectional
alternatives, private/concurrent progress, spaced review and bundle installation.
Generated command references, shell syntax and installer dry run also passed.
