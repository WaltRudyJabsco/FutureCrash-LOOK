# 5.8.0 — Accountless Web Search

Generic web search is now a Fabric capability rather than an Ollama-account feature. A node with a healthy local SearXNG service advertises `web.search`; LO first asks the local Unified Node, which uses local SearXNG or routes to a peer advertising that capability. A directly reachable local SearXNG instance is the second path. The existing Ollama hosted search API remains an optional fallback when `OLLAMA_API_KEY` is configured.

The Local Labs server controller remains the explicit Linux service edge for SearXNG (`server install/normalize/configure/check/search`). Normal Future Crash + LOOK upgrades never invoke sudo or silently install a server daemon; server-class machines get a clear readiness hint instead.

The README has been rewritten around the current architecture and daily-use surfaces rather than accumulating release notes. Existing screenshots are reused. Dash also protects narrow terminal geometry explicitly so medium-layout minimum widths do not wrap on unusual laptop panes.

No Fabric identity/trust protocol is introduced here. That is intentionally the next architectural step; 5.8.0 only makes search independent of mandatory third-party accounts and establishes `web.search` as a normal discoverable capability.
