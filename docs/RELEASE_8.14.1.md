# 8.14.1 — Mac audio CD import repair

Local Mac disc imports run from the foreground terminal, which can read mounted
CD tracks even when the background node lacks removable-volume access. Remote
requests retain owner-node routing. Track numbers sort numerically, and AIFF/AIF/
AIFC filenames are supported. Volume access failures give actionable errors.

Fabric CLI failures now return a nonzero exit status and preserve the server’s
error message instead of appearing as successful commands with empty JSON.
Long disc labels also stay within the dashboard row width.
Drive labels omit the unrelated drutil SupportLevel column.

Bundle/Albert 8.14.1; LOOK 4.61.1; Future Crash 1.3.0.

Validation: 1,022 automated tests; real SuperDrive discovery of 14 tracks;
one-second detached FLAC encode and ffprobe verification from the mounted CD.

Installer follow-up: copy tailscale_serve.py and the core package initializer
before registering the runtime, so older peer installs pass checkout verification.
The installer inventory regression executes the actual copy commands in an
isolated home and verifies every registered core Python module.
