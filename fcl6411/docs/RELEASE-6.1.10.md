# Future Crash + LOOK 6.1.10 — Media Mount Race Repair

This is a narrow repair to the local media edge. A removable/desktop-mounted filesystem may be healthy but momentarily unavailable at the instant LOOK resolves a queue. LOOK now gives local media one bounded queue-level retry window before declaring catalog paths unavailable. The retry happens once for the whole queue, never once per track, and local rows are never rewritten as localhost Fabric streams.
