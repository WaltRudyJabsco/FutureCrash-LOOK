# 1.3.4 — media status feedback

- Replaces the combined macOS status script with direct queries for player state, artist, and track name.
- `lk media` shows current player/state/track.
- `mm`, `mn`, `mp`, and full media transport commands now print the resulting state/track after success.
- macOS media commands only control already-open Music or Spotify instances; they do not launch a player.
- All aliases/help/README/man/command docs are synchronized.
