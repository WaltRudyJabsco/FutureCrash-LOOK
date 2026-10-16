# Local speech input

Speech-to-text is optional and separate from the existing speech output/voice
profiles. Audio stays on this computer. No microphone starts at installation,
startup or when a text field receives focus; transcription never executes words.

## Start here

Open Settings and search for **Local speech input**, or run:

```sh
lk transcribe status
lk transcribe setup
lk transcribe recording.m4a
lk transcribe recording.wav --output transcript.txt
lk transcribe recording.wav --note "Meeting notes"
lk dictate --note "Spoken notes"
```

Setup explicitly downloads dependencies into
`~/.local/share/look/transcription/venv` and caches Phonon-2 through Fermion.
Normal LOOK installation does not download this runtime or model. On the tested
Apple silicon Mac, the isolated runtime occupies about 1.3 GB, in addition to
model/cache storage. The Phonon-2 download is about 164 MB, unpacking to roughly
178 MB; it currently recognizes English. Its weights are CC-BY-4.0, derived from
NVIDIA Parakeet TDT 0.6B v3. See the [model documentation](https://www.fermionresearch.com/docs/speech-models/).

Setup fetches/verifies model files. A successful offline transcription verifies
inference separately; `status` only reports runtime/configuration presence.
File transcription explicitly sets Hugging Face/Transformers offline mode. A
missing model produces an error and setup instructions rather than downloading
silently. Network access is needed for initial setup, not routine inference.
First load/compilation can be slower than the actual decoding operation.

File input accepts WAV/FLAC/OGG/AIFF directly. Other media is converted locally
with ffmpeg to a temporary 16 kHz mono WAV; the original stays untouched.
Long files use the engine's chunking. No automatic source recording is retained.
`--output` creates a new UTF-8 file and refuses to overwrite an existing file.
`--note` creates a normal note in the Transcripts project with normal sync behavior.
Without either option, transcript text goes to standard output; `--json` returns
structured text and a note ID when one was created.

`lk dictate --note "Spoken notes"` names the new note before recording.
Ctrl-C finishes recording and returns captured text. In the Notes quick editor,
**Ctrl-D** starts dictation; **Ctrl-C** finishes and inserts text at the caret.
The draft stays editable until Ctrl-S/Shift-Enter saves. Uppercase D remains text.

Apple silicon uses Fermion’s live dictation engine. Linux and Intel Macs record
locally first, then transcribe after Ctrl-C; Linux setup uses CPU PyTorch wheels
by default rather than downloading CUDA libraries. A larger model is optional,
not required. Capture needs the optional speech environment even when a local
server provides transcription. Successful temporary recordings are removed; if
capture/transcription fails after audio was recorded, a private WAV is retained
under `~/.local/share/look/transcription/recovery/` for manual retry.

macOS may request microphone permission for your terminal; Linux needs an available PortAudio input device. This does not select
speakers, modify Bluetooth pairing or change the system audio output.
Microphone input has not been exercised by the automated tests.

## Replace the engine

The reusable Python entry point is `transcription.transcribe(path) -> str`.
Applications can adopt it without depending on Phonon-specific details. A local
OpenAI-compatible speech server provides an alternate file backend:

```sh
lk transcribe configure --server http://127.0.0.1:8000/v1 --model YOUR_MODEL
lk transcribe recording.wav
lk transcribe configure --model phonon-2
```

Configure without `--server` returns to the local Fermion CLI backend. Settings
live in `~/.config/look/transcription.json`. Alternate servers must use a loopback
HTTP address and expose `/audio/transcriptions`; LOOK does not launch the server,
install its model, guarantee its offline behavior, or send audio to remote nodes.
Uploads are limited to 32 MiB; use the file engine for longer recordings. On this
backend, microphone dictation records locally and sends the finished file to that
server.

CLI file/dictation capture, Notes output and Notes quick-editor insertion share
this interface. Signal/Albert microphone buttons are not included; those can
share this boundary without changing the storage/engine model.
