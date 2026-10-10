# 8.16.0 — Node media libraries and inbox delivery

Each node maps a canonical library root with music, movies, tv, books and inbox.
The initiating computer remembers a preferred library node/root, and individual
imports can override it. Existing scan roots remain separate. Remote optical
imports finish locally, then deliver all files through the recipient’s inbox in
a background job. Checksums gate publication and destination cataloging; sources
are retained, failure receipts are durable, and retries are explicit.

Bundle/Albert 8.16.0; LOOK 4.63.0; Future Crash 1.3.0.

Validation: 1,056 automated tests passed, including per-node settings, inbox
publication, checksum rejection, source retention, collision handling, delivery
worker receipts, cancellation identity checks and authenticated owner routing.
