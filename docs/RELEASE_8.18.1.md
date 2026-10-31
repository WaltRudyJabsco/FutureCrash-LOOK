# 8.18.1 — Clean Books startup

Bundle/node/Albert integration **8.18.1**; LOOK **4.65.1**.

Books clears terminal text and the previous Kitty graphics placement before
loading the catalog, preventing a stale media preview from remaining on screen.
Non-Kitty terminals receive the ordinary screen clear without graphics commands.

The shelf header now shows its import owner. `lk books --node SERVER` opens the
shelf here while imports and confirmed Gutenberg downloads run on that paired
server and use its configured books folder. The existing default owner remains
unchanged. See [Books](BOOKS.md).

No commands or shortcuts changed. Close and reopen Books after updating.
