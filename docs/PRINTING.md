# LK Print

Bare `lk print` opens a small terminal desk with one entry per identified physical
printer. Enter/o opens Options, j shows Jobs, r shows underlying Routes, n sets a
Nickname, and R refreshes. Arrows/Tab select; Page Up/Down scroll detail views;
q/Esc returns or closes. Options show aligned setting/current-default columns
with available choices beneath each setting, blue labels and subdued hints.
Jobs and Routes show readable labeled fields, including owner/queue and errors,
rather than JSON. Narrow panes wrap details without dropping choices. Key hints use LOOK's standard blue/subdued footer and
wrap in narrow terminals. `lk print options` or `jobs` without a name opens the
same printer picker; files/receipts without `--printer` also offer a picker.

`lk print list` lists physical printers without the desk. `list --queues` exposes
owner/queue routes for troubleshooting. `--json` preserves machine-readable data.
Zsh completion is copied by the normal installer. Existing Fabric installs can
review `lk print completion --node OWNER`, then add `--confirm` to update the
LOOK-owned script with a backup of its prior contents. Rollout uses this explicit
setup action; the runtime updater does not gain access to arbitrary shell config.

Zsh Tab completion after `lk print options ` or `--printer ` offers current friendly
printer names; start a new shell after updating the completion script.

Physical identity uses observed DNS-SD/IPP UUIDs and normalized endpoints, never
model names alone. CUPS `lpstat -v` supplies configured connections; optional
`ippfind` supplies read-only Bonjour UUID/endpoint links, cached for a minute.
Linux cups-browsed `implicitclass://` routes are resolved only when their service
name corresponds to one observed Bonjour UUID. Minimal installations without
`ippfind` can use the UUID-bearing DNS-SD entries from `lpinfo -v`. Ambiguous
service matches remain unverified. If identity cannot be verified, queues stay
separate rather than merging two printers of the same model. No CUPS queue is deleted or rewritten.

An automatic route selects an enabled local queue first, then an enabled peer
queue, before preparing or inspecting. Owner availability means the spooler is
reachable; an idle queue is not proof that paper/device is ready. Disabled queues
are excluded. Jobs show all routes. A prepared plan pins queue + owner and its
send command: it is never rerouted/retried after dispatch. Exact `--node OWNER`
plus queue remains available for direct control. Names apply to reachable routes;
partial nickname changes are reported. Queues verified as the same physical
printer can share a nickname locally.

## Discover and configure

```
lk print
lk print list --node local
lk print discover --node OWNER
lk print options QUEUE --node OWNER
lk print jobs QUEUE --node OWNER
```

macOS uses its existing CUPS tools. Linux needs a running CUPS installation and
`lp`, `lpstat`, `lpoptions`, `lpinfo`, `lpadmin` and `cancel` for the corresponding
operations. Use that OS's printer settings/package manager; LK never installs
packages, grants USB permissions or invokes sudo automatically. Windows is not an
adapter in this first release.

`discover` asks CUPS for device URIs, including USB and network discoveries; it
is not a general network port scan. Configure ordinary printers in system printer
settings, or review a driverless IPP queue before adding it:

```
lk print add office --uri ipps://printer.local/ipp/print --node OWNER
# After reviewing the proposed command:
lk print add office --uri ipps://printer.local/ipp/print --node OWNER --confirm
```

Existing queues are never overwritten. CUPS may require local administrator
permission. Vendor-specific drivers, authentication and paper trays remain in
system settings; `options` shows the installed driver's choices. Queue creation
neither shares the printer publicly nor changes the system default.

## Documents and text

```
lk print file chapter.pdf --printer office --node OWNER --pages 1-3,5 --copies 1 --media Letter
lk print text 'A small reminder' --printer office --node OWNER
printf 'A reminder\n' | lk print text - --printer office --node OWNER
lk print inspect PLAN_ID --node OWNER
lk print send PLAN_ID --node OWNER --confirm
lk print cancel office office-123 --node OWNER --confirm
lk print discard PLAN_ID --node OWNER --confirm
```

You can name a destination without renaming its system queue:

```
lk print nickname receipt 'Little Printer' --node OWNER
lk print nickname receipt 'Little Printer' --node OWNER --confirm
lk print receipt 'Buy paper' --printer 'Little Printer' --node OWNER
```

Nicknames select the physical printer; use Routes when you want the exact queue
and owner. The send confirmation always retains its chosen owner.
Text plans include a bounded content preview for review.

File/text/receipt commands **prepare** a plan on the printer's owner and show a
send command; they never invoke `lp`. Review the original document, exact owner,
queue and options before sending. Omit `--confirm` on send to inspect instead.
`--json` is available for scripts, before or after the subcommand. `lk help print`
and `lk print COMMAND --help` expose the same live parser.

Supported document inputs are PDF, UTF-8 text, PNG and JPEG, up to 3 MiB. Export
Mercury Writer manuscripts, DOCX or EPUB to PDF in their application first; LK
never sends project/ZIP bytes to a printer. Driver support determines media,
duplex and page-range behavior; LK validates option syntax, not physical hardware
capabilities. Copy count is limited to 20. The original input is retained.

Plans retain exact spool bytes, SHA-256, profile, options and a receipt in a
private owner-local SQLite spool (`~/.local/share/look/print/jobs.sqlite3`). Send
expires after 24 hours, refuses changed profiles and claims each plan once even
under concurrent requests. Repeated send requests inspect the existing state.
Timeouts, interrupted submissions and missing job IDs must be investigated with
`jobs`; LK never retries them automatically. A verified CUPS job ID means
**accepted by the spooler**, not physically printed. Cancellation cannot recall
pages already printed. Completed submissions and discards clear stored content and text previews; prepared plans
can be discarded explicitly. Pending content is capped at 32 MiB.

## Receipt printers and small raster art

First connect the printer to its owner and run `discover`. Identify its model,
protocol and **printable dot width**, which is smaller than the roll width. Do not
assume a 58 mm or 80 mm printer speaks ESC/POS, or that a label printer supports
receipt commands. Connect/configure one device at a time; use the manufacturer’s
instructions for USB permissions and drivers.

For a verified ESC/POS device and a compatible CUPS raw queue:

```
# Use the real discovered URI, not this example:
lk print add receipt --uri usb://VENDOR/MODEL --driver raw --node OWNER
# Review, then repeat with --confirm if appropriate.
lk print profile receipt --kind escpos --width 384 --columns 32 --node OWNER
# Review, then repeat with --confirm after checking the printer manual.
lk print receipt 'A small thought for today.' --printer receipt --node OWNER
lk print receipt --image sketch.png --printer receipt --node OWNER
# Both return plans; sending requires their exact ID and --confirm.
```

384 dots/32 columns are an editable example, not a guarantee for all 58 mm devices;
a common wider profile is 576 dots/48 columns, but verify the actual model. Text
uses CP437, wraps to configured columns, rejects control sequences and unsupported
characters, and feeds a few lines. It never operates a cash drawer or cutter.
Image preparation needs Pillow: it composites transparency on white, scales to
the configured maximum width, dithers to monochrome, and generates bounded
ESC/POS **GS v 0** raster data. This is a legacy compatibility command, not a
universal printer protocol. Only use it on a model confirmed to support it.
Document PDF jobs are refused on an ESC/POS profile. Raw CUPS queues are legacy
and may be unavailable in newer print stacks; this first version has no direct
USB/libusb or port-9100 writer. Other sticker/label languages and native application
print dialogs can be added as separate adapters after identifying the hardware.

## LO and integration hooks

Say “print my shopping list from Notes on Little Printer” in LO, Albert or
Signal. The assistant discovers the named destination, reads the actual note,
and uses `print_text` to submit one copy. A generated recipe can likewise be
printed with its title, ingredients and steps. Notes are never modified by printing.

For a direct terminal command:

```sh
lk print quick "Remember the milk" --printer "Little Printer"
printf 'Shopping list\nEggs\nMilk\n' | lk print quick - --printer "Little Printer"
```

`quick` explicitly sends one copy, automatically selecting document or ESC/POS
format from the printer profile. It accepts at most 8,000 characters. No default
printer, driver or device nickname is installed for other users.

The shared `print_text` model tool requires workspace-or-higher access and a
current explicit print/send request containing the exact discovered printer
label. Questions and previews do not authorize printing. The host permits only
one attempt per user message, including after uncertain failures. It returns
CUPS acceptance, not proof that paper emerged. Model interpretation still depends
on the chosen model; use the direct command if it asks unnecessary questions.

`printers_list` and `printer_inspect` remain read-only. `print_prepare` stages
text or workspace-contained files for review and returns a confirmation command;
it never sends paper. File printing and longer documents retain that review path.
Read-only profiles cannot upload or print, and models cannot configure printers.

Other applications can use `printing.prepare` or the paired Fabric API:
`GET /v1/print`, `GET /v1/print/fabric`, `POST /v1/print` with `action` matching the
CLI operation. File bytes are bounded base64, never a remote arbitrary file path.
Preparing returns an immutable ID on the owner; sending requires that ID and
`confirm: true`. Forwarding is local-control only and uses existing paired-node
credentials; peers cannot chain requests through a third node. This provides the
hook for future reminder/aphorism or Mercury PDF actions without adding automatic
printing schedules now.

References: [CUPS printing/options](https://www.cups.org/doc/options.html),
[CUPS lp command](https://www.cups.org/doc/man-lp.html),
[Epson legacy raster command](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_lv_0.html).

[Formatted Options preview](screenshots/print-options-readable.png) uses the real
Epson driver option list with synthetic printer/owner labels, in a private demo HOME.
Linux class behavior: [OpenPrinting cups-browsed](https://github.com/OpenPrinting/cups-browsed).

## Printing a selected LOOK file

In LOOK’s file selector or preview, **Shift+N** opens printing for the highlighted
file (or one marked file). Choose the physical printer, review the file, owner,
queue and options, then press **P** to submit. Enter/Esc cancels and discards the
unsent plan. After a submission, Enter returns to the same LOOK selection. The
working set is preserved. Lowercase n still types into the filter; folders and
multiple marked files are refused with a clear message.

The file action, `lk print file`, and LO’s workspace-file tool share
`printing.prepare_file`: supported PDF/text/PNG/JPEG input, bounded upload,
physical-printer routing and a pinned owner/queue. A configured receipt destination
takes text files as receipt text and PNG/JPEG as monochrome raster art. PDF needs
a document printer. Other application formats, including manuscript projects,
need export to PDF first. This is also the reusable file hook for Albert/Signal
clients; it does not add a separate web print button or bypass job confirmation.
