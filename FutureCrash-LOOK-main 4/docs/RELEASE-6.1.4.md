# Future Crash + LOOK 6.1.4 — Media Resolver Repair

6.1.4 repairs the media edge exposed after Fabric authorization and Tailcat transport changes.

## Playback resolution

Merged catalog entries can contain several physical locations. LOOK now checks every location for bytes available on the playback node, then lazily identifies and streams a remote source only when no local copy exists. Credentials and transport details remain inside Fabric rather than leaking into player-facing queue semantics.

When every entry fails to resolve, LOOK prints the first concrete resolver errors so path, authorization, or transport failures are visible immediately.

## Conversational artist names

Artist matching ignores one leading conversational `the`. `play the talking heads` therefore resolves the `Talking Heads` artist grouping, while stored metadata remains unchanged.

## LO command passthrough

An explicit `lk ...` entered at the LO prompt now executes LOOK directly with inherited terminal I/O. This keeps interactive commands such as `lk media find` interactive and prevents them from being mistaken for model prompts. Nested `lk lo` is blocked.
