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
characters, and feeds a few lines. Receipt plans estimate paper length and reject
jobs above their allowance (one foot by default), including all copies and trailing feed. Text uses explicit
30-dot line spacing at 8 dots/mm; raster estimates use the rendered image height.
Oversize content is rejected, never silently truncated. It never operates a cash drawer or cutter.
Image preparation needs Pillow: it composites transparency on white, scales to
the configured maximum width, dithers to monochrome, and generates bounded
ESC/POS image data. The default `raster` mode uses **GS v 0**;
`profile --image-mode column24` selects **ESC * mode 33**, with 24-dot vertical
bands, explicit band spacing, white padding at the bottom and no leading reset.
Use the mode verified on the physical printer; do not infer graphics support
from successful text or built-in QR output. These are compatibility commands, not a
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

Museum supports **p** (or **Shift+N**) from its terminal list and viewers, and a
**Print** button in the web gallery. The receipt printer is suggested first;
users can choose any discovered printer, style, rotation, copies and paper allowance, then review before sending.

For portable printers with unverified large transfers, an owner can set
`profile --max-receipt-bytes N` alongside the verified image width and encoder.
This optional ceiling counts encoded bytes across all copies before a plan is
stored; it complements the paper-length limit. Oversized jobs fail without
printing or retrying. Omitting the option preserves a configured ceiling; zero
explicitly disables it. A byte ceiling is a precaution, not a diagnosis of USB
flow control or proof that a larger print will succeed.


## MXW01 Bluetooth receipt printers

An observed MXW01 can be registered on its Linux owner with:

```sh
lk print bluetooth pocket --address AA:BB:CC:DD:EE:FF --adapter hci0 --label "Tiny Printer"
```

Use the address and adapter discovered on your own computer. This first shows a
configuration preview; repeat with `--confirm` to save it. Registration does not
pair, print, create a CUPS queue, or change another printer. The owner needs
BlueZ `gatttool` and Pillow. Other Fabric nodes need no Bluetooth driver.

The destination appears in the shared printer picker for Museum, Notes and
selected text/image files. Existing USB printers retain their names and profiles.
Tiny Printer uses explicit Low Energy connections because some MXW01 devices
advertise misleading Classic support. Each connection negotiates and verifies
MTU before any print data, and bounds every write to that MTU. Text is rasterized
locally; images use the same 384-dot monochrome format. No vendor app is needed.

This initial transport accepts 1–20 copies within a maximum **30.48 cm (one foot)** per reviewed job,
including feed margin. This is a software default. An explicit banner allowance
can raise the job limit up to 3048 mm (ten feet); actual hardware capability and
remaining roll length are not automatically known. Over-allowance jobs are
rejected before printing. Long Bluetooth jobs run in a detached owner worker
and keep a durable status, so HTTP timeouts cannot interrupt delivery. PDF goes to a document printer. Listing
shows a configured Bluetooth destination, not a live claim that the device is
awake. Sending requires the printer to be powered on and in range. A per-device
lock prevents overlapping jobs; a failed or uncertain attempt is never resent
automatically. The driver waits for completion and checks the image checksum when reported; this confirms protocol delivery, not physical appearance.


## Image print options

Museum's terminal, fullscreen and browser print dialogs offer Image/ASCII,
0°/90° clockwise rotation and copies before preparing a reviewed job. Terminal
ASCII viewing defaults to ASCII printing. Change any web option and review again
before sending. Review reports the combined estimated paper length; limits and
printer-specific transfer ceilings still apply. Tiny Printer copies are one
bounded raster job with blank spacing, not independent automatic retries.

ASCII prints are rendered as dark characters on white paper, independent of the
terminal's colors. Rotation happens before sizing to the configured print width;
rotating a landscape image can therefore use more paper and show more detail.
The original artwork is never modified. Document printers receive a rendered PNG
when an image transformation is requested. PDF rotation is not supported here.

```sh
lk print file artwork.jpg --printer "Tiny Printer" --style ascii --rotation 90 --copies 1
```

This prepares a plan, never sends it immediately. Use the returned send command
only after reviewing the destination and estimated paper usage.

## Lettering and fortune keepsakes

`lk print setup` installs pinned pyfiglet and Pillow into this account's isolated
lettering directory. The workstation installer offers this setup too. Rendering
is offline after setup; missing dependencies produce a setup instruction instead
of a hidden download. `toilet` remains optional and can still feed plain text
into the receipt pipeline.

```sh
lk print banner "HAPPY BIRTHDAY" --font small
lk print banner "HAPPY BIRTHDAY" --font small --printer "Tiny Printer" --paper-limit-mm 3048
lk print fortune "A small kindness will find its way back to you." --printer "Tiny Printer"
```

Without a printer, banner prints a terminal preview. With a printer, both commands
prepare a reviewed job; use the returned send command to send it. Fonts are
standard, small, slant, banner and big. Banners fill the printable width and run
sideways along the roll; their estimated length includes all content.

A fortune is one to three short upright lines plus six random lucky numbers for
fun. Below it is a randomly chosen accessible saved Museum artwork, excluding
removal-marked works, with title/artist/date/museum credit. Landscape artwork
rotates clockwise; portrait artwork stays upright. Metadata remains upright.
The image is fitted within the normal receipt allowance, with no new external
art downloads. If no saved artwork is accessible, preparation explains that
nothing printed rather than silently omitting the artwork. Tiny text may need
to be shortened for narrower printers.

LO, Signal and Albert share `banner_render` (read-only preview) and `print_design`
(preparation or explicit printing). The AI writes an original, concise fortune;
the renderer provides its layout and numbers. Examples: “Show a small-font banner
saying Happy Birthday” or “Print me a fortune on Tiny Printer.” Printing requires
an explicit current request naming the exact discovered printer; unclear requests
create review plans. One print attempt per message applies across text/design
printing, including failures. Fortunes stay within the normal allowance; a longer
banner allowance must be deliberate. No physical appearance is inferred from a
job receipt.

## Deliberate banners

The printer options offer **Receipt: up to 1 foot** and **Banner: up to 10 feet**.
These are software allowances, not verified hardware or roll-length claims.
Copies, raster content and feed spacing all count toward the selected allowance;
existing device-specific encoded-byte limits remain in force (including Rongta's
conservative thumbnail setting). A failed or disconnected print never restarts
itself. Long Bluetooth jobs immediately return an owner job ID; use **Check
status** in the web print dialog or `lk print inspect ID --node OWNER` to see
completion. A worker that never reports completion becomes uncertain, not retryable.

Literal ASCII lettering can be piped into a sideways receipt without wrapping
away its spaces. Supply plain output without ANSI color codes:

```sh
toilet 'HAPPY BIRTHDAY' | lk print receipt - --printer "Tiny Printer" --rotation 90 --paper-limit-mm 3048
```

This only prepares a plan. Review the estimated length and then use its explicit
send command. `--paper-limit-mm` also accepts intermediate allowances, for example
609.6 for two feet. A ruler needs physical scale calibration before it is suitable
for measurements; raster sizing and printer mechanics can affect its scale.


Named fortune requests such as “print me a fortune on tiny printer” take a
narrow direct route shared by LO, Signal and Albert. It discovers the friendly
printer name case-insensitively, generates a short fortune through Fabric, then
submits once using the existing explicit-print guard. The model does not decide
whether the printer exists or whether to ask for redundant confirmation. Missing
printers, failed generation and submission errors produce an explicit result.
Bare follow-ups such as “immediately” do not replay an earlier print attempt.


Tiny Printer may stop accepting Bluetooth connections while asleep even if its
light is on. A connection failure before a print request is now marked failed
with “No print data sent”; wake/power-cycle it near its owner before requesting a
new job. Existing failed jobs never resume automatically. Fortune commands wait
briefly for background results, and the Museum web print dialog refreshes status
automatically while open. An accepted job is not a delivery confirmation.

For a formatted thermal slip, use `lk print file recipe.md --printer "Tiny Printer"` and review the returned plan, or copy the Markdown and run `lk print clip`. On receipts, `# Title` centers a large heading, `## Ingredients` makes a smaller heading, and `- item` makes a bullet. Use `**bold**`, `*italic*`, or a single line wrapped in `<center>…</center>`. Formatting is local and the paper estimate includes wrapped lines.

Press **P** in either `lk player` or `lk mp` to print the currently playing track. Choose a printer, review the paper estimate and press **y**. The receipt includes the song title, artist, album and available cover art. Fortunes, Museum credits and track receipts share the Markdown typography.

### Portable printer graphics initialization

For verified column24 devices that render their first image band as text, set
`"prime_graphics": true` in that queue's printer profile. This sends a full-width
blank graphics band before the image. It adds 24 dots (3 mm) to the paper estimate
and is included in transfer-size checks. Leave it absent for other printers.
The Rongta RPP300 diagnostic was physically verified with this initialization;
a successful USB transfer alone does not establish a successful print.

Graphics priming reasserts zero extra line spacing before every image band, letting
the 24-dot bitmap height determine paper advance and preventing
white seams between image bands on the verified RPP300. Receipt Markdown type
stops scaling up at 384 dots: 576-dot printers fit more words using two-thirds
of their previous font size. This covers fortunes, lucky numbers, artwork
credits, song receipts, and Markdown text; 384-dot Tiny Printer and banners
retain their existing sizing.

### Assistant-composed receipts

LO, Signal and Albert can combine read tools with `print_text`: retrieve a
forecast, recipe or Note, compose concise Markdown, then print one copy. Live
forecast output requires a successful weather lookup in the same turn. Requests
for previews or explanations do not send paper, and uncertain sends are not retried.

A queue profile can set `preferred_receipt: true` (CLI profile option
`--preferred-receipt`, or `--no-preferred-receipt` to disable). This preference
is discovered from its owner across the Fabric. Exactly one preferred receipt
destination is required for unnamed printing; absent or conflicting preferences
produce a numbered destination list instead of guessing. Named destinations
continue to override the default. No printer name is built into the application.

Examples: “Print me a five-day forecast for Paris”, “Print a short packing list”,
or “Print this recipe on [printer name]”. Include dates, location, units and a
source in factual receipts. Existing paper limits apply.

### Pending tasks and completion

Terminal LO, Signal and Albert use the same pending-print state model. Browser
turns store it privately under `~/.local/share/look/tasks`, scoped by interface
and session ID, with a 30-minute expiry and serialized access. Separate chats
never inherit one another's authorization. Missing session IDs get no persistent
state. This is session continuity, not automatic transfer between nodes or chats.

Only operator messages and discovered printer choices update pending intent;
assistant prose cannot authorize a print. A send attempt clears and persists
pending intent before submission, including when the response is lost. A later
“yes” cannot repeat that pending send. Explicit new print requests are new work.

Completion requires the requested action's successful receipt. Printer discovery
and prepared plans do not prove a print was submitted; uncertain results do not
count as completed. A queued receipt proves spooler acceptance, not physical
printing. Weather-plus-print requests retain action tools instead of entering
the weather-only text shortcut. Missing actions get at most one bounded model
recovery step within the existing turn budget, never an automatic print retry.

The verified portable column24 profile primes with a full-width blank band and
reasserts zero extra spacing before every image band. This prevents startup glyph
garbage and horizontal seams; all receipt-image producers use this owner-side
encoder, including Markdown, Museum, fortunes, clipboard and song receipts.

Assistant `print_text` accepts an optional `illustration` (`sun`, `cloud`, `rain`,
`snow`, `storm`, `fog`). The renderer combines the monochrome symbol and Markdown
into one PNG at the selected printer's width, then uses the same owner-side spool,
paper limit, device encoder and one-copy send path. It does not download artwork.
For forecasts, the assistant retrieves weather first and chooses the symbol from
those conditions. Configured printer names are discovered before inference;
configuration does not prove the physical printer is awake.
