# 8.16.1 — Preserve Linux maintenance through node shutdown

The Linux updater runs in a separate transient user service, so stopping the
node’s service cannot kill its own updater. Systems without a working user
service manager fail before stopping any services. Other platforms keep their
existing pinned detached runner.

Includes 8.16.0 node libraries, inboxes and remembered import destinations.
Bundle/Albert 8.16.1; LOOK 4.63.1; Future Crash 1.3.0.

Validation: 1,058 tests passed, including independent Linux runner dispatch
and rejection before service shutdown when isolation fails. Real 3090 rollout
requires a local install to replace the older updater.
