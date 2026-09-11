# 1.3.2 — macOS media detection fix

- Removes the brittle System Events process check from `lk media`.
- Uses direct AppleScript `application "Music" is running` / `application "Spotify" is running` checks.
- Queries and controls the running app directly after detection.
- `mm`, `mn`, and `mp` are unchanged.
- Paging, memory, skills, AI, and capability behavior are unchanged.
