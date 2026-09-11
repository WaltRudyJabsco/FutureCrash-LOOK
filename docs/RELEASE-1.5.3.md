# 1.5.3 — Fortune layout + cleanup

Versions:
- Future Crash + LOOK 1.5.3
- LOOK 3.8.0
- Future Crash 1.0.3

- Fortune now has a fixed `FORTUNE //` label plus exactly three reserved body lines.
- Footer/menu position no longer jumps as fortunes wrap between one, two, or three lines.
- Fortune generation may use up to 36 words.
- Fortune prompt more strongly requires final artifact only.
- Fortune contamination detection catches remaining task/goal/instruction paraphrases.
- Fortune generation gets a slightly larger output budget so a final sentence is less likely to be truncated.
