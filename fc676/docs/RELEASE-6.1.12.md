# Future Crash + LOOK 6.1.12 — Live Node Version Repair

The installer now verifies the version of the process actually answering the Unified Node port rather than treating any successful pulse as proof that the new daemon owns the socket.

If an older user-owned Future Crash node is still listening on `:7332`, the installer retires that stale listener, restarts the managed node service, and waits until `/v1/health` reports the exact release being installed. A foreign listener is never killed automatically; installation stops with an explicit diagnostic instead.

This closes the split-brain upgrade case where new files were installed while `lk dash` continued to report an older live node.
