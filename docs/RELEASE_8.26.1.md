# 8.26.1 — A word with every launch

Bundle/node/Albert integration **8.26.1**; LOOK **4.73.1**.

`lk wd` is an alias for the complete `lk words` command, including its arguments.
A blank local word desk offers a **Word of this launch** card with an actual
WordNet definition, part of speech and source. A curated learning pool cycles
without repeats, avoids an immediate repeat between cycles, and keeps progress
local to this OS account. Concurrent launches serialize their small progress file.

The card disappears on the first typed/pasted text or submitted search, and does
not return when that input is cancelled. Explicit lookup/spelling/pattern queries
stay focused. No installed dictionary means the normal setup guidance; launch
words never trigger downloads or inference. Dictionary data remains read-only.

Validation: **660 affected tests passed**. An isolated real terminal with the
actual offline dictionary verified the `lk wd` launch card, removal on typing,
and a different sourced word on the next launch. Unit checks cover pool cycling,
missing data, source integrity, frame bounds and alias argument dispatch. Generated
references, shell syntax, installer dry-run and diff checks passed.
