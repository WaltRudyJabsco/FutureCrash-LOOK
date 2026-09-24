# Future Crash + LOOK 6.1.6 — Fabric Client Authorization

6.1.6 closes an authorization hole exposed by Signal/LO after node authorization became mandatory. The application-side `fabric_client` could discover a remote worker but then opened `/v1/jobs`, `/v1/infer/stream`, and artifact staging requests without the paired node credential. Remote ingress correctly rejected those requests with HTTP 401.

The shared client now owns the edge: remote requests receive `X-Fabric-Node` plus the paired bearer credential, Tailcat requests use the certificate pin learned during pairing, and worker URLs follow the Unified Node's active transport selection rather than assuming Tailscale DNS. Loopback remains credential-free.

Signal also instructs LO to include the exact saved path returned by successful image generation in the answer, preserving enough artifact context for later browser turns such as “where is it?” or “show it.”
