# Fabric receipt cards

`lk receipts` is the human-readable archive for notable results, command cards,
notes and release records. It complements diagnostic logs. The original transaction log remains available as `lk receipts transactions [N]`,
`lk receipt [N]`, or the backward-compatible `lk receipts N`. Creating a card never
prints it. Cards are immutable; automatic queue/download events have stable keys
so repeated observations do not create duplicate receipts.

```sh
lk receipts --node YOUR_ARCHIVE_OWNER
lk receipts command ytr
lk receipts command museum
lk receipts create "Market list" --body-file shopping.txt
lk receipts create "New feature" --kind feature --body "What changed and how to use it"
lk receipts list museum
lk receipts show RECEIPT_ID
lk receipts print RECEIPT_ID --printer "Little Printer"
lk receipts print RECEIPT_ID --printer "Little Printer" --columns 48
```

Print prepares an immutable job through LK Print and returns the exact
`lk print send … --confirm` command for review. It does not send paper. Printer
nicknames resolve to physical destinations and their configured routes. The
common pipeline chooses document or ESC/POS output from the actual printer
profile. Width defaults to 32 columns (typical 58 mm); 48 suits many 80 mm devices.
Actual printable width, encoding and USB protocol must be checked on the device.

## Automatic records

- YTR additions: **queued**, explicitly not playback or download completion.
- Finished Fabric downloads: **download**, after final media publication.
- Healthy maintenance updates: **deployment**, with release and commit.
- Command cards: generated from the installed command reference on request.
- User-authored feature notes and lists: labeled with their source.

Receipt failures do not turn a successful download or queue addition into a
failure. Producer results carry a warning where available. Receipts are stored
on the node performing the action. Set the shared archive owner with `--node`;
use `--node NODE` to inspect a different producer. The 3090 is a useful owner for
shared downloads/queues, but no particular host is hardcoded.

Each card is private JSON under `~/.local/share/look/receipts/cards/`. This tree
already belongs to Fabric's essential-state/FabBack recovery inventory. The
node API `/v1/receipts` supports list, show and create; paired Fabric requests use
`target=OWNER`. LO exposes read-only `receipts_search`. A receipt records a
producer's result; user-authored cards are not independent proof of execution.

## Images and the little printer

The existing `lk print file IMAGE --printer NAME` pipeline prepares raster images
for a configured receipt printer, or a normal document printer. Museum images,
photos and Signal artwork can use that path once exported to a local file.
`lk print receipt --image IMAGE --printer NAME` explicitly selects receipt-image
preparation. There is no automatic printing subscription or new Signal image
button in this first milestone. The USB printer must be discovered and configured
on its owner when it arrives; setup installs no guessed driver and prints no test
paper until requested.
