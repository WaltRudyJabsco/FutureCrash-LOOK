# LK Print

`lk print` lists configured queues on trusted Fabric computers. Each printer is
identified by **queue + owner**: printing on a Mac can send to a USB printer
attached to a Linux peer without installing that USB driver on the Mac. Printer
availability is observed from CUPS; a queue can exist while its device is offline.
Missing peers/spoolers are shown as an incomplete list. Discovery never prints,
changes a default printer, or adds a queue.

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

Nicknames are unique on an owner and shown alongside the real queue. The owner
remains explicit, so two computers' queues cannot silently become one destination.
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

“LO, print this to-do list from Notes on the Little Printer” is the intended
workflow: LO reads the actual Notes body through notebook search/list/read, chooses
the discovered nickname and owner, and prepares receipt text for review. It never
invents a replacement list or marks tasks complete. Notes are not modified by
printing. The model-driven phrasing still depends on the selected model following
the provided tools; the underlying Notes read and print-plan hooks are tested.

Ask LO “what printers are available?” for observed queues and owners. Model tools
`printers_list` and `printer_inspect` read capabilities/jobs; `print_prepare`
stages text or workspace-contained files in workspace-or-higher profiles. It does
not send paper. LO returns the exact confirmation command, which can also be run
as an explicit `lk print ...` line inside terminal LO. Read-only profiles never
upload document contents. No printer-submit or setup tool is exposed to a model.

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
