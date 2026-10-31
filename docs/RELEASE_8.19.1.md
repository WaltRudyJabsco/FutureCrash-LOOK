# 8.19.1 — Reader setup upgrade compatibility

Bundle/node/Albert integration **8.19.1**; LOOK **4.66.1**.

The new maintenance helper can finish upgrading a node whose running version does
not yet expose reader setup status. A 404 for that optional endpoint is treated as
an older runtime; other HTTP errors still block maintenance. Existing disc-import
and active reader-setup guards remain in place.

Includes the terminal book reader and synchronized native artwork from 8.19.0.
Validation: targeted reader, preview, real terminal and maintenance tests, including
legacy endpoint compatibility and non-404 error propagation.
