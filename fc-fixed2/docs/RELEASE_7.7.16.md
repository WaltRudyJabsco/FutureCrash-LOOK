# 7.7.16 — EDGE OWNERSHIP

Two bounded repairs after 7.7.15 field testing:

- macOS installer now retires a stale listener on localhost:7332 only when the owning process is provably the installed Future Crash Unified Node. It waits after launchd bootout, sends TERM, escalates only for that known process, and refuses to kill unrelated port owners.
- Albert catalog playback now uses the same browser-facing `/api/media/audio` contract as Signal while retaining the existing ticket and Range-capable Fabric item proxy. The legacy Albert `/v1/media/item` browser route remains as compatibility only.

No changes to LOOK media playback, Fabric item serving, MM/MN/MP, All Classical, Classic Arts, or Signal playback.
