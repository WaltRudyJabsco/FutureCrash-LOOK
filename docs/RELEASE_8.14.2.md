# 8.14.2 — Automatic Mac CD metadata

Mounted macOS audio CDs provide a table of contents for MusicBrainz lookup.
A single matching release preloads album, artist and track names without asking
for a release number. Multiple matches remain an explicit choice. Finder labels
are retained when no release matches; the artist field is optional, and Return
keeps detected album defaults.

Bundle/Albert 8.14.2; LOOK 4.61.2; Future Crash 1.3.0.

Validation: 1,026 tests passed. A real 14-track SuperDrive CD returned one
MusicBrainz match; repaired tags were verified against the original decoded audio.
