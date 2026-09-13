# Future Crash + LOOK 2.1.1 — Living AI release hardening

2.1.1 is the distribution-ready maintenance release of Living AI.

The only runtime behavior change from 2.1.0 is status semantics: `lk ai status` now returns success when it correctly reports either a running or stopped broker. A stopped broker is a valid inspected state, not a command failure.

This release also synchronizes version metadata across README, installer, LOOK runtime, and release documentation and revalidates the broker/memory package for deployment across multiple machines.

Versions:

- Future Crash + LOOK: 2.1.1
- LOOK: 4.1.1
- Future Crash: 1.1.7
