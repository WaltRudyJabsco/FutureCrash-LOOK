# Future Crash + LOOK 1.9.1

This release fixes a real transaction bug in multi-file copy/move.

LOOK's undo history is capped at 20 public records. Earlier batch code inferred newly-created undo entries by comparing the history length before and after the operation. Once the history was already full, its length stayed 20, so successful multi-file moves could be falsely reported as `undo journal mismatch`.

Batch operations now carry an explicit transaction ID. Temporary item records are allowed to exceed the public history cap until the operation commits; they are then collapsed into one batch undo record. This also makes batches larger than 20 items safe.

Success receipts identify what moved. Failure receipts identify the source that failed and report rollback status.

Interactive file prompts also retain Tab completion while giving bare Escape an explicit cancel binding.

LOOK is 3.13.1. Future Crash remains 1.1.7.
