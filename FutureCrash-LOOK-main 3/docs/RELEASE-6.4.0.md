# Future Crash + LOOK 6.4.0 — Open Door

Albert becomes a real remote browser surface without becoming a network-facing daemon.

- Albert stays bound to `127.0.0.1:7330`.
- The unified installer publishes Albert through Tailscale Serve on HTTPS port 7330 when Tailscale is available.
- A tailnet browser can open `https://<node>.ts.net:7330`; all Albert API calls remain same-origin through that edge.
- `lk albert url` prints the best reachable Albert URL.
- `lk albert qr` renders a terminal QR when `qrencode` is available and always prints the URL.
- `lk albert ipad` / `lk albert remote` opens the tailnet surface from the current node when available.
- Unified Node capability advertisement now includes Albert local/tailnet URLs.

Security invariant: remote convenience does not change Albert's bind address. Tailscale remains the authenticated reachability layer for 6.4.0; later public Fabric/Tailcat browser pairing can replace it without changing Albert itself.
