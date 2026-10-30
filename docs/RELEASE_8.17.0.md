# 8.17.0 — Consolidated Fabric release

Bundle, Albert integration and Unified Node: **8.17.0**. LOOK: **4.64.0**.
Future Crash retains its component version **1.3.0**; Signal retains **1.11.0**.
The bundle version identifies the integrated release. The Git commit and managed
runtime digest identify its exact code, including any later maintenance fixes.

This release gives the work since 8.16.1 a new numbered baseline:

- Media desks separate music and video, show previews, durations and sorting,
  support queues, offline copies and sibling shell panes, and retain readable
  alternating rows across terminal palettes.
- Playback supports owner-generated AAC delivery for lossless audio and improved
  browser media delivery, full-screen controls and artwork handling.
- Notebook supports rendered links, command blocks, dictation, clipboard access
  and responsive columns; Web has a notebook-style home and browser integration.
- Fabric maintenance, backup setup and disc imports have guided workflows and
  verified update receipts. Existing settings, media and backups are preserved.
- Recent maintenance removes media search stalls, ignores terminal protocol
  replies as keystrokes and isolates artwork helpers from interactive input.
- Artist-and-song requests such as “Play some Artist, Song Title” use exact
  catalog evidence. Signal lookup errors offer browser-accessible next steps.

The standalone **Look-Shell** repository has a separate publishing lifecycle;
this release does not copy the integrated bundle over that repository.

No new commands are introduced by the release pass. Generated command reference
and man pages are refreshed for the version labels. Previously opened terminal
interfaces must be reopened to load updated Python code. Managed updates retain
existing playback/import safeguards; a staged update is not a completed update.

Packaging correction: the fresh installer now includes `media_duration.py` and
`media_ui_work.py`, matching the managed runtime inventory.

Validation: focused media, release and packaging checks pass, generated command
reference is current, and the unified installer dry run accepts the bundle. A
real-catalog prepare of the reported UB40 request selects exactly one correct
track on its owning node without starting playback. The broad suite had 1,881
passes and 38 failures; all 38 reproduce on unchanged main in the same sandbox.
One of those failures exposed the installer omission fixed here. Remaining
failures include restricted local listeners, missing Node.js on PATH and older
assertions/fixtures; the full historical suite is not claimed clean.
