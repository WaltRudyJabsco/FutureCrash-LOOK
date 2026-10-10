# 8.14.0 — Everyday Fabric media and attention

- LO can append, edit and reschedule existing notebook records. Read-before-write
  revisions protect against concurrent edits; unrelated fields stay intact.
- Reminder occurrences request native desktop/sound delivery per targeted node.
  Speech is opt-in, Future Crash has a cue, and Albert/Signal can enable their
  browser sound/notification channel through a user gesture.
- Artist/album browsing opens groups and ordered tracks through existing playback
  and queue actions. Album artist metadata supports compilations.
- Optical import discovers owner-local drives and runs durable CD/DVD/Blu-ray
  adapter jobs. Paired nodes can submit, watch and cancel jobs. Verified output
  is published atomically and joins the existing Fabric catalog. Failed or
  cancelled work retains staging/logs. The installer offers platform-aware tools.
- Albert static runtime files join the maintenance inventory. Older peers can
  bootstrap the new allowlist with a registry excluding Albert, then update
  again with the complete registered runtime. User notes/catalogs stay outside
  the deployment inventory.

Bundle/Albert 8.14.0; LOOK 4.61.0; Future Crash 1.3.0.

The user's SuperDrive is not connected. Physical CD/DVD/Blu-ray checks remain
a hardware test; software tests use controlled readers and real codecs.

Validation: 1,017 tests pass. Controlled CD-reader tests run real ffmpeg FLAC
encoding and ffprobe verification, exercise failure/cancellation and catalog
publication, and verify owner routing and browser/native alert behavior.
Generated command help, code-health, shell syntax and Python 3.10 parsing pass.

Automatic MakeMKV installation on this Mac was unavailable: Homebrew disables
the cask for Gatekeeper compatibility. HandBrakeCLI and ffmpeg are installed.
The adapter supports a normally installed MakeMKV CLI on either platform.

Deployment checks also hardened CLI routing: reads try authenticated fallback
routes; writes discover a live route and verify the paired node identity first,
then send once. TLS validation and pairing remain enforced.
