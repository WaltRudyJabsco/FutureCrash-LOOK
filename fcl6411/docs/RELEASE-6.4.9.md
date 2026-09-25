# 6.4.9 · BROWSER VOICE

Browser sessions are now first-class Fabric effect endpoints.

- Authorized Albert and Signal sessions heartbeat their live capabilities into the Unified Node.
- Active browser endpoints advertise display.output, audio.output, audio.speak, media.play, and input.text.
- Fabric can route audio.speak to an active browser endpoint; Safari executes speech locally with the Web Speech API.
- Browser presence expires automatically when the page stops heartbeating.
- `lk fabric endpoints` shows active endpoints and their endpoint IDs.
- `lk fabric speak @ipad "Dinner is ready"` resolves a live browser endpoint when no full Fabric node matches.
- Albert now uses the shared accountless browser authorization gate instead of treating reachability as trust.
