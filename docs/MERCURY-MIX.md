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

## Preview and spring-return playing

**Listen A / Listen B** selects records for the cue bus before the crossfader.
**Cue → main mix** blends that preview with the master in your headphones, and
**Headphone level** controls it independently. Press Play on the deck you want
to audition; a closed crossfader keeps it out of the main mix.

Choose **Preview here** to hear that bus instead of the main output on a single
device. A private simultaneous headphone feed needs another physical output:
use **Choose headphones output** where supported by the browser, leaving main
on your system output, or use **Split cable** with a DJ splitter (mono main on
left, mono cue on right). Choosing the same physical output for both will mix
them audibly. Unsupported browsers explain that limitation without requesting
microphone access. Output device routing is session-only, never silently
restored. Cue audio never enters a recording; recording remains stereo even
when monitoring uses a split cable.

**On key release → Return to deck A** makes the fader spring back to A after
all fader keys are released. With the left-hand layout, hold F for B, use S/D
for intermediate blends, then release for A. **Return to deck B** reverses the
resting deck. **Stay where I leave it** is the original latch behavior;
**Silence selected deck** closes the deck selected with 1/2.

**Dub space** on either deck adds a filtered repeating echo and a stereo reverb
space. Tap again to disengage; Reset EQ / FX also clears it. Saved sets retain
the deck’s dub setting and spring-return preference.

## Scratch Moves: play phrases from a marked sound

This mode treats the keyboard as a performance instrument. The starter bank
contains twelve playable interpretations of named scratch techniques, built
from record-position curves and timed cuts. They use the loaded track’s PCM;
there are no canned scratch sound effects. Technique names draw on
[School of Scratch’s demonstrations](https://studioscratches.com/scratch-techniques-demo-video/).
The patterns are stylized approximations, not a substitute for the articulation
of a turntablist.

1. Play the backing track on one deck and leave the crossfader on that side.
2. Select the other deck with **1/2** or its deck button. Load a useful sound,
   seek to it, and press **Mark sound here**. The mark is its main cue, retained
   in saved sets. **Hear marked sound** auditions that segment.
3. Tap a pad or key for one phrase. Hold to repeat; release finishes the current
   phrase. Roll between keys to change moves. **Escape / Stop moves** cancels.

| Key | Move |
| --- | --- |
| A | Baby |
| S | Forward cut |
| D | Reverse cut |
| F | Stab |
| G | Chirp |
| H | Transformer |
| J | One-click flare |
| K | Two-click flare |
| L | Tear |
| ; | Scribble |
| Q | Crab-style cuts |
| W | Echo scratch |

Phrase timing starts from the other playing deck’s tempo, or the selected
deck’s tempo when the other is paused. Intricate motions get additional time
to keep audible record speed controlled. Launch remains immediate rather than
waiting for a beat grid.

**Sound length** selects more of the marked sound and stretches the gesture
proportionally: one second of source makes a phrase four times as long as a
quarter-second selection, at the same scratch speed. It does not squeeze a
larger selection into a fixed interval and raise its pitch.

**Scratch pace** ranges from Gentle (0.5×) through Natural (1×) to Sharp (1.5×).
It changes subsequent gesture speed and duration independently of either
track’s playback tempo. Natural keeps audible peaks near normal vinyl speed;
rounded acceleration and reversals let a stroke move through slower and faster
motion. Faster motion still raises pitch, as real scratching does. The setting
is remembered and included in saved sets.

During a phrase, the selected deck is opened over the existing mix without
moving the main crossfader or interrupting the backing deck. On completion,
its original channel level is restored. A paused scratch deck returns to its
cue; a previously playing one rejoins its uninterrupted timeline. Changing
selected decks, opening Controls or losing window focus cancels the move to
prevent a held note from getting stuck.

**Keyboard mode → Manual fader** restores ASDF / JKL; crossfader playing.
The on-screen scratch pads remain playable in either keyboard mode.
