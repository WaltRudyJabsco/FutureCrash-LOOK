# Fabric Theater

Open `/theater` in Signal or Albert, or send `/theater` in their chat. Choose the
media host, search its movies/music, and select **Show on channel** or **Issue
movie ticket**. Each movie ticket allows independent playback. A channel ticket
joins the current shared playback clock. The host controls pause, seek and stop.
Viewers press Watch to satisfy browser autoplay rules. The audience page offers
fullscreen and works with phone/tablet inline video.

## Terminal projection room

Run `lk theater` to open the terminal menu. It remembers your chosen media host
and starts with the configured media-library owner. Choose a movie, start a
showing, pause/resume/seek, or create a movie/channel ticket. Arrows, Page Up/Down,
Home/End and Shift-arrow navigation work in each picker. Escape returns and
Ctrl-Q exits the desk.

The ticket screen offers **Print QR on Little Printer**, another-printer selection,
copy link and open audience page. Printing uses the existing image preview,
copy/style options and explicit Print confirmation. Manage issued tickets to
return to a saved code or revoke admission. Tickets issued here are saved in a
private local file under `~/.local/share/look/theater/` for later QR printing.
Tickets issued elsewhere can be revoked here, while their original links remain
available where they were issued. `lk theater status` and `--json` retain their
command-line behavior.

## Host setup

Configure a dedicated HTTPS origin and point it at the host's loopback port 7340.
The listener starts when enabled and returns after a Fabric node restart.

```
lk theater setup --url https://HOST:8443
# On this media host, enable one of these HTTPS routes:
tailscale serve --bg --https=8443 http://127.0.0.1:7340
# For guests outside the tailnet, use Funnel on that dedicated port:
tailscale funnel --bg --https=8443 http://127.0.0.1:7340
```

Check existing Serve/Funnel settings before choosing a port. The guest service
serves only admission, viewing status and the admitted media stream. The operator
interface stays behind Signal/Albert authentication and paired Fabric node APIs.
A ticket grants its holder access. Expiry and revocation are checked for each
request and throughout streaming. Already buffered media can finish playing.
Independent playback lasts until ticket expiry, including repeat visits.

## Commands

```
lk theater --node HOST search PCU
lk theater --node HOST ticket MEDIA_ID --hours 24
lk theater --node HOST show MEDIA_ID
lk theater --node HOST ticket --channel --hours 120
lk theater --node HOST pause
lk theater --node HOST seek 300
lk theater --node HOST resume
lk theater --node HOST stop
lk theater --node HOST revoke TICKET_ID
lk theater --node HOST channel open
lk theater --node HOST channel ticketed
```

Opening a channel permits anyone with its address to join the current showing.
Each new showing starts with channel tickets required. Tickets can last up to
30 days. Codes are shown at issuance and stored as hashes on the host. Save the
issued link or QR, since the ticket list cannot recover it later.

For printed QR admission, install the small renderer once on the media host and
save a ticket image on the requesting computer. The image can go through Print's
usual preview and printer chooser.

```
lk theater qr-setup
lk theater --node HOST ticket MEDIA_ID --hours 24 --qr ticket.png
lk print file ticket.png
```

The first play of an incompatible movie may need conversion through the existing
browser-media cache. Original files retain their catalog identity. Host upload
speed and conversion capacity determine how many viewers can watch comfortably.
This first version uses one channel and individual movie tickets. Music uses the
same player. Library browsing and device control are available to operators.

LO, Signal and Albert use `theater_lookup` to discover movies and showings and
`theater_control` to act on an authorized request.
