# Mercury Mix

Run `lk mix`, or `/mix` in Signal or Albert. You can also open `/mix` on
an existing Signal or Albert browser address. It uses that host’s normal
Fabric access controls. `lk mix --host signal --url` prints the local address.

Start with **Demo set**, then press Play on each deck. These two original
loops are built into the instrument, so no library or internet is required.
Sound plays on the device running the browser; it does not start the Fabric
music player or change anyone else’s queue.

## Your hands

The crossfader is shared. Choose **ASDF** for your left hand or **JKL;** for
your right hand. Both layouts move the same fader from left to right; pressing
adjacent keys together gives an intermediate position. Choose a smooth blend
or sharp cut, latch on release or close the selected deck, and optionally
reverse the fader. Platter hand and fader hand are independent.

- **1 / 2:** select a deck.
- **Space:** play or pause that deck.
- **C:** pause and return to the main cue.
- **Z / X:** momentarily nudge the selected deck slower / faster.
- **R:** reverse; **V:** slip mode.
- Drag a record to scratch. Touchscreens support independent pointers on both
  records. Scroll over a record to nudge; hold **T** while scrolling to scratch.
- Drag the overview waveform to seek. Set hot cues with the four cue buttons;
  Shift-click a cue to clear it.

Trackpads supply browser scroll events, rather than separate physical left
and right touch zones. Keyboard shortcuts leave typing fields alone.
On phones, switch the visible deck with the deck selector; the shared fader
stays within reach. Controls also offers a paper finish and a deck-order swap.

## Mixing

Each deck has vinyl rate, an estimated beat grid, tap tempo, Beat 1, hot cues,
beat loops, three-band EQ, a combined low/high-pass filter, echo and channel
level. Sync aligns tempo and beat phase to the other deck. Adjust the estimate
with tap tempo, BPM and Beat 1 when necessary. **Vinyl rate changes pitch as
well as speed**; this version does not claim pitch-preserving time stretch.

The Fabric crate searches available music across the full catalog and pages
through results. Audio comes through the host’s existing media routes. You
can also select or drop local audio files; they stay in this browser.

For bounded device memory, each track must be under eight minutes and 48 MB.
Some formats depend on browser decoder support; MP3, M4A and WAV are good
starting points. Two decks are decoded into local PCM for responsive scratch
and reverse playback. Original files are never modified.

## Keep a session

**Save set** downloads a small JSON file with the track references, positions,
cues, grid, loops, effects and playing preferences. **Open set** restores
paused decks. Local audio files must be selected again because the set does
not embed or upload their audio.

**Record mix** captures the stereo mixed output locally, including EQ and
effects. Stop recording to download it; browser support determines WebM/Opus
or MP4 format. Output mute affects monitoring, not the recording. Recordings
stop after 30 minutes. No microphone permission is needed.

AudioWorklet needs a trusted HTTPS Fabric address or localhost. An insecure
remote HTTP address can browse the crate but cannot enable this audio engine.
The assistant’s `mix_library` tool finds real track references and the launch
command; it does not pretend to operate a browser session remotely.
