# Fabric PIN curtain

`lk lock` opens the configuration screen. `lk lk` immediately covers reachable
paired nodes with Flight Deck in the Bridge palette. `lk unlock` privately asks
for the four-digit PIN and dismisses reachable curtains.

This is an ambient privacy curtain, **not an operating-system lock**. App switching,
process termination, browser tools and normal desktop escape routes still work.
Use the operating system's lock screen when you need actual access protection.

## First use

Run `lk lock`, then **P** to choose and repeat a four-digit PIN. The PIN verifier
is distributed only to paired Fabric nodes, in private local files. Changing it
requires the current PIN; unlock before changing it. PINs are never shell arguments.
PIN entry submits automatically after the fourth digit; Enter is not needed.
Five wrong attempts cause a 30-second cooldown on that node.

The settings screen uses **L** lock, **U** unlock, **P** PIN, **G** prepare AI captions,
**R** refresh and **Q/Escape** back. `lk lock setup` and `lk lock status` also work.

**G** uses the existing explicit Fabric caption generator. Locking reads its cached
fictional captions and distributes them with the curtain; it never waits for AI.
Built-in captions work without AI or internet access.

## Screens

Desktop curtains require `lk saver setup` and an active graphical user session.
The node reports a launch request or an unavailable desktop, rather than claiming
to have visibly covered a screen. On Linux it checks the user service manager's
graphical environment. A node running only over SSH may have no desktop to cover.

Press Enter, Escape, or click to open the masked PIN prompt. Cancel leaves the
curtain up. **C** changes colors and **V** changes visuals. A successful unlock on
any reachable node dismisses the others. OS-level app switching remains available.

Open Signal and Albert pages receive curtain state
and provide a masked unlock form. There is no floating activation button. Explicit `/lock` or `lk lk` in their chat input
activates the curtain; `/unlock` focuses its PIN field. Never put your PIN in chat.
Reload existing browser pages once after installation to load the new integration.
A browser page cannot cover other applications or enter fullscreen automatically.

## Offline and recovery

Each command reports delivery to paired nodes. Offline nodes are not silently
counted as covered. Retry `lk lk` or `lk unlock` after reconnecting; this first
version does not replay old commands automatically to returning nodes. Open browser
pages poll their host and retain the curtain if the connection drops. Local PIN
verification works without other Fabric nodes, provided the local node is running.

State is stored in `~/.config/look/curtain.json`, including a salted PBKDF2-SHA256 verifier (older scrypt records remain readable on supported Python runtimes),
not the plaintext PIN. Treat it as private: a four-digit PIN has a small search
space and this feature is not intended to resist an attacker. If you forget it,
exit the curtain through your OS, stop the curtain process, remove this file only
on affected nodes, then choose a fresh PIN using `lk lock setup`.

## They Live Easter egg

`lk lktl` activates a special curtain across reachable paired nodes: white screens,
huge black lettering, and one ominous phrase held for twelve seconds. Open Signal
and Albert pages follow the same mode; `/lktl` also starts it from either chat.
Each desktop shuffles its phrase order independently; attached displays use different
slots, so up to eight monitors on that desktop show distinct phrases. Browser pages
shuffle independently too; separate devices may occasionally choose the same word.
Successful unlock closes with a brief CRT collapse to a line and point. Incorrect
PINs leave the curtain intact. Browsers honor reduced-motion preferences.
Click or press a key to reveal the usual four-digit PIN prompt; `lk unlock` works
as usual. This remains an ambient PIN curtain, not an operating-system lock.

The special mode belongs to that lock event. It does not change saved saver sets,
palettes or the normal curtain choice. The next `lk lk` or `/lock` uses your normal
curtain again. Offline peers are reported by the existing delivery status.
