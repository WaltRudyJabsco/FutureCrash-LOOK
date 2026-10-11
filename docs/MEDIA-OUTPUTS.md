# Fabric audio outputs

Open **Settings → Audio outputs**, press **o** in Player/MP (outside search),
or run `lk media outputs discover`. Choose a numbered output; each line says
which Fabric computer owns it. Discovery leaves playback and system defaults
alone. Enter without a number returns to your player.

A speaker is an output attached to a computer, not a new trusted Fabric node.
That computer handles playback, codecs and its local audio service. Video stays
on that computer; this interface routes audio, not AirPlay video or multiroom groups.

## First connection

- **Linux AirPlay:** run `lk media outputs enable-airplay --node NODE` on a
  PipeWire/PulseAudio bridge, wait a few seconds, then refresh. This explicitly
  enables RAOP discovery for the current audio-service session and preserves
  its system default. Re-enable after that service restarts. The host needs
  `pactl` and its RAOP discovery module; failures explain the missing service.
- **Mac AirPlay:** discovered network receivers appear with connection guidance.
  Connect in macOS Sound settings and refresh. LOOK can directly select outputs
  exposed by CoreAudio; a network advertisement alone is not a playable device.
- **Bluetooth:** pair/connect in the owning computer's OS sound settings, then
  refresh. LOOK lists outputs the host exposes; it does not change OS pairing.

The bridge and receiver must share a reachable local network. Isolated guest
Wi-Fi, sleeping computers and stale receiver addresses can prevent playback.
An advertised Linux receiver whose TCP endpoint is unreachable stays visible
with a reason and cannot be selected.

## Choose, play and move

```sh
lk media outputs discover --list
lk media outputs --json
lk media outputs select OUTPUT_ID --node NODE
lk media on NODE play "artist or album"
lk media outputs move --node NODE
```

Selection belongs to that node and the current OS account. It changes its active
LOOK player when present and is saved for future LOOK playback. A selection on a
remote bridge does not move your queue: use `move` explicitly, or `media on` to
start a new queue there. Move transfers the current local queue to the target
bridge before stopping its source; media bytes remain at their source. Public
web streams retain their original URLs.

Choose the node's **default** row to return LOOK to its system-selected output:

```sh
lk media outputs select default --node NODE
```

LOOK verifies an active player's selected device before saving it. If a saved
speaker disappears, playback fails with a choice of next steps rather than
silently switching to a different speaker. Speaker IDs for Linux RAOP receivers
survive changes of their advertised IP address. Settings live in the current
account's `~/.config/look/media_output.json`; upgrades preserve them.

An idle player can confirm device selection, but only playback confirms delivery.
A device may still reject a stream or lose its connection later; check the host
player log if a ready output goes silent.
