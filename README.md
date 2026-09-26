# Future Crash + LOOK

## 6.7.0 · BEACON

BEACON begins Fabric's independent Internet discovery layer. Already-paired nodes can optionally announce short-lived, Ed25519-signed presence through a tiny public rendezvous service. Pairwise authorization tokens stay on the devices; only one-way capability slots are published. Resolved addresses become temporary Tailcat candidates while the certificate pinned during pairing remains the authority.

This is deliberately the first networking stage, not a fake Tailscale replacement: 6.7.0 adds secure rendezvous but leaves UDP hole punching and encrypted relay for the next stages. Tailscale remains a fallback while those pieces are built.

Also includes the 6.6.5 native mpv video fix, SHOWTIME startup receipts, MOVIE NIGHT selector normalization, TRUE CURSOR terminal editing, ONE BRAIN cognition, and LIVING MIND memory.

**One personal computer made from the machines you already own.**

Future Crash + LOOK is a local-first terminal environment and personal computing Fabric. LOOK is the practical interface, LO is the conversational interface, Future Crash is the ambient workstation, and Fabric lets machines contribute files, models, services, media, sensors, and outputs without turning any one machine into a mandatory server.

```text
one node  = a complete system
more nodes = the same system with more capabilities
```

A laptop can work alone on an airplane. Reconnect it and larger models, indexed files, media, web search, and other capabilities on your workstation become available again.

![Future Crash](FC_screenshots/Error_2.png)

## What it does

- **LOOK (`lk`)** — navigation, filtering, file operations, machine inspection, catalogs, media, models, memory, Fabric controls and small terminal utilities.
- **LO (`lo`)** — conversation plus explicit tools. LO interprets intent; LOOK resolves resources; deterministic commands do the work.
- **Future Crash** — the terminal/workstation personality and ambient interface over the same underlying system.
- **Fabric** — capability discovery and routing across trusted personal machines. Nodes advertise what they can actually do rather than pretending every machine is identical.
- **Signal** — browser endpoint for conversation, camera input, visual output and media control. A browser is an endpoint, not automatically a compute node.

![LOOK file filter](FC_screenshots/LOOK_Shell_filter_find.png)

## Install

macOS and Linux are the primary targets. Clone or unpack the release and run:

```sh
./install.sh
```

Then open a new shell and start with:

```sh
lk doctor
lk machine
lk
lo
future-crash
```

The installer is intentionally additive. Optional capabilities degrade cleanly when their dependencies are absent.

## Files: discovery first, understanding second

LOOK maintains a cheap local SQLite catalog. A normal scan records filesystem metadata and incrementally extracts bounded text from formats where extraction is deterministic and inexpensive.

```sh
lk scan
lk catalog
lk find "GDP happiness"
lk find "largest pdf"
```

Content search uses SQLite FTS5. Supported sources include text/Markdown, source and common config files, HTML, DOCX, EPUB, and text-bearing PDFs. There are no embeddings, OCR, model calls or mandatory hashes in the basic indexing path.

`lk find` is interactive on a terminal: navigate the ranked matches, inspect evidence, select a result, and hand a locally reachable result into the normal LOOK file workflow. Fabric search stays data-local: each node searches its own catalog and returns bounded matches/snippets rather than shipping its index around the network.

![LOOK AI](FC_screenshots/LOOK_AI.png)

## AI and models

Future Crash + LOOK uses Ollama-compatible local inference. The interface and model do not have to live on the same machine: a small laptop can use its local model while disconnected and use a larger GPU node when Fabric makes one available.

```sh
ollama pull qwen3:8b
lk ollama models
lk ollama host
```

Commercial/cloud model services are optional edges, not architectural requirements.

## Web search: accountless by default

Generic web search now prefers **self-hosted SearXNG**. A node with a healthy SearXNG JSON endpoint advertises the Fabric capability `web.search`; LO on another machine can use that capability without having SearXNG installed locally.

Provider order is deliberately boring:

```text
Fabric SearXNG
    ↓
local SearXNG
    ↓
optional Ollama hosted search
    ↓
offline / unavailable
```

No Ollama account or API key is required for the default self-hosted path. If an `OLLAMA_API_KEY` is already configured, hosted Ollama search remains a fallback.

On a Linux machine using the bundled Local Labs server controller:

```sh
server install searxng
server normalize searxng
server configure searxng
server check searxng-api
server search "Future Crash LOOK"
```

SearXNG is installed as an ordinary system service and remains independently inspectable. LOOK does not hide or replace the underlying Linux service management.

## Fabric

Fabric separates *what a machine can do* from *which machine it is*.

```text
                 FABRIC

 files       models       media       web search
   \            |           |             /
    \           |           |            /
             capabilities
                  |
        choose an appropriate node
                  |
              do the work
```

Useful surfaces include:

```sh
lk fabric
lk fabric nodes
lk fabric events
lk fabric decisions
lk media fabric
fcl-node dash
```

The dashboard is responsive to terminal geometry: wide/short, ordinary, compact and narrow layouts preserve the important state instead of assuming every laptop has the same terminal dimensions.

### Island Mode

Fabric is an extension of a machine, not a dependency of it. Local files, local memory, deterministic LOOK tools and available local inference continue when peers disappear.

```sh
lk doctor island
```

## Fabric identity and accountless pairing

Every node now owns a local **Ed25519 Fabric identity**. The stable node ID and human-readable fingerprint are derived from its public key; the private key stays on that machine. Tailscale names and IP addresses are transport hints, not identity.

```sh
lk fabric identity
lk fabric trust
```

A trusted node can open a one-use five-minute invitation:

```sh
lk fabric pair-code
```

When Tailscale HTTPS is available, LOOK can infer the reachable bootstrap endpoint automatically. The invitation prints an eight-digit, five-minute, one-use code and a simple join command; if `qrencode` is installed it also renders a human-readable QR courier. On the joining node:

```sh
lk fabric pair 3090 48219371
```

Pairing is still bilateral in 6.1: a direct M4↔M3 relationship needs its own pairing even if both machines are already paired with the 3090. Fabric-wide membership sponsorship is a separate trust-topology problem, not part of Tailcat transport.

The nodes exchange public identities, validate the node ID against the public key, record one another in their local trust stores, and consume the invitation. No Fabric account, email address, central identity server, or Tailscale identity is involved.

```text
identity       Fabric Ed25519 keypair + stable node ID
trust          local Fabric trust store
discovery      capabilities and reachable peers
transport      localhost / Tailcat / Tailscale fallback
```

Remote Fabric APIs now enforce paired node authorization. **Tailcat** is the preferred native node-to-node transport when a paired peer is directly reachable: it serves the guarded Fabric API over TLS on port `7443`, pins the peer certificate learned through Fabric trust, and falls back to Tailscale when direct reachability is unavailable. It does not yet attempt NAT traversal or relay traffic; those are later transport layers, not identity work.

Inspect the active path with:

```sh
lk fabric transport
```

## Media and browser endpoints

Media is a reference workload for artifacts, sessions and output routing rather than a separate product silo.

```sh
lk media scan ~/Music
lk media find "Talking Heads"
lk media play "Remain in Light"
lk media outputs
lk player
```

A Signal browser can act as an ephemeral endpoint for display, camera and playback. Media queues and artifact identity belong to Fabric; the browser is simply one possible renderer.

![Machine context](FC_screenshots/PNC.png)

## Permission model

LO separates reasoning from permission.

| Profile | Permission |
| --- | --- |
| Conservative | Read/search and reason; no writes |
| Workspace | Read and intentionally edit inside the starting workspace |
| Power | Workspace tools plus individually confirmed shell commands |
| Unsafe | Unrestricted shell commands with the current user's privileges |

External input is validated at the edges. Dangerous operations stay explicit. A model being capable of proposing an action does not grant permission to perform it.

## Memory and decisions

Fabric Memory is small, inspectable and scoped. Shared/persona memory can replicate among live trusted nodes while node-local memory stays local.

```sh
lk memory
lk memory fabric
lk memory shared
lk skills
```

The Decision Plane treats uncertainty as data. Deterministic rules remain fast; optional learned judgment such as OpenJev can provide bounded evidence; consequential ambiguity can be surfaced to the human without turning the UI into the execution authority.

## Design rules

Future Crash + LOOK tries to stay boring underneath:

- local-first and useful with one machine;
- capabilities instead of machine roles;
- metadata before hashing, lexical search before embeddings;
- work moves to data when that is cheaper than moving data;
- browser endpoints are not automatically trusted compute nodes;
- optional services fail gracefully;
- observable Linux/macOS primitives rather than hidden infrastructure;
- no account should be required merely to make the core system useful.

## Accountless pairing and endpoints

Pair two nodes without copying a long URI:

```sh
# machine A
lk fabric pair-code

# machine B
lk fabric pair 3090 12345678
```

A new Signal browser shows a six-digit authorization code. Approve it from **any reachable trusted Fabric node**; LOOK locates the node that owns the pending browser request and performs the approval there:

```sh
lk fabric endpoints
lk fabric allow 482193 once
lk fabric allow 482193 trust
lk fabric revoke-endpoint ep-...
```

For an iPhone, a trusted machine can mint a one-use browser invitation and render a QR when `qrencode` is available:

```sh
lk fabric endpoint-code https://signal.example trust
```

The browser receives a scoped HttpOnly credential; no Future Crash account, password, or third-party identity provider is involved.

## Documentation

Detailed command help lives in the installed tools and focused docs rather than at the top of this README:

```sh
lk help
lk man
fcl-node --help
server help
```

See `docs/COMMAND-GRAMMAR.md`, `look/docs/COMMANDS.md`, and `docs/RELEASE-HISTORY.md` for the deeper command/release record.

## Release

Current release: **6.1.10 — Media Mount Race Repair**.

Browser endpoint management is now Fabric-wide: `lk fabric endpoints`, `allow`, and `revoke-endpoint` work from any reachable trusted node rather than only the Signal host. Tailcat adds direct certificate-pinned TLS transport between paired nodes on reachable LAN/IP paths and is preferred automatically; Tailscale remains a fallback for reachability and bootstrap rather than the definition of Fabric networking. Existing 6.0 pairings learn Tailcat metadata from authenticated peer identity and do not require another re-pair.

Future Crash + LOOK remains an open, local-first project: **Fabric turns your computers and devices into one personal computer; LOOK is how you use it.**


## Albert remote browser access (6.4.0)

Albert stays on localhost. When Tailscale is installed, the installer publishes it through Tailscale Serve on HTTPS port 7330.

```bash
lk albert url      # print iPad/tailnet URL
lk albert qr       # QR if qrencode exists; always prints URL
lk albert ipad     # open the tailnet URL here
```

On an iPad connected to the same tailnet, open the URL printed by `lk albert url` in Safari.


## Albert cognition surface (6.4.3)

Albert is a first-class Fabric UI: synchronized beacon/disco presence, continuing answer-fold conversations, and artifact-aware paste/drop input. Pasted images and files are registered locally and supplied to the shared LO engine by reference rather than embedded into inference packets. Current-news/headline requests are routed through live search/tool evidence when available.


## LOOK Games (6.4.8 · SOUND CHECK)

`lk games` opens the WOPR recreation channel. Board games support `0p`, `1p`, and `2p`: `lk games chess 1p`, `lk games checkers 0p`, `lk games backgammon 2p`, and `lk games ttt 1p`. `lk games gtnw` keeps the Global Thermonuclear War simulation. The old `lk ttt` and `lk gtnw` commands remain aliases.


### 6.4.5 · JOSHUA

`lk games` deliberately reports `No games installed.` The hidden doorway is a named simulation such as `lk games chess` or `lk games gtnw`. On first interactive entry the WOPR recreation channel accepts `JOSHUA` at `LOGON:`; named games then show the simulation selector and player-count chooser. `lk games chess 0p` remains a direct shortcut.

Albert, Signal, and terminal LOOK now share the same host-owned intent gate for obvious game and current-news requests before inference. Surface code controls presentation; it no longer decides whether `gtnw` means a game or whether `headlines` means live web search.


### Fabric speech

Browser-local effects are resolved by the resident Fabric daemon, so endpoint listings and effect routing share the same live registry.

Speech is a routed local effect. Every node with a local synthesizer advertises `audio.speak`; cognition may run elsewhere while the selected endpoint speaks. `fcl-node speak --node NODE TEXT` targets a Fabric node directly, and `lk fabric speak @NODE TEXT` is the human LOOK doorway. The shared LO tool plane can also invoke `audio_speak` for explicit read-aloud and hands-busy notification requests.

The WOPR profile uses the same offline `espeak-ng` + SoX chain on macOS and Linux. macOS `say` is only a graceful fallback. Set `LOOK_GAMES_VOICE=0` to mute game speech.

## LOOK Games — WOPR recreation channel

`lk games` performs the theatrical `LOGON: JOSHUA` ritual, then denies that games are installed. Named simulations (`lk games ttt`, `checkers`, `chess`, `backgammon`, `gtnw`) enter the WOPR selector. Board games support 0p/1p/2p and return to the selector with `q`; `s` stops. WOPR speech is lightweight and offline: macOS uses `say`/Zarvox, Linux uses `espeak-ng` with SoX when available. Set `LOOK_GAMES_VOICE=0` to mute it.
