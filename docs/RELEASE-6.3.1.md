# 6.3.1 — Full Alphabet

Tiny but important LOOK input repair.

Interactive filters now preserve ordinary lowercase text. In `lk media find` / `browse`, lowercase `j` and `k` are searchable characters; arrows or uppercase `J/K` move the focus. In shared LOOK selectors, lowercase `j/k` retain browse navigation outside filter mode but become normal characters while the filter is active.

This fixes the class of bug where keyboard command handling could silently steal letters from the user's query. `q` still exits an empty media selector, but becomes ordinary query text once filtering has begun.
