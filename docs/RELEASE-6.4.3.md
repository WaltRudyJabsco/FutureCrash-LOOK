# 6.4.3 · Searchlight

- Repairs Albert current-information turns that were incorrectly collapsing a web-search failure into “shared cognition unavailable.”
- LOOK web search now tries Fabric SearXNG first, direct local SearXNG second, and optional hosted Ollama search last.
- One-shot LO emits a structured search-stage error instead of falling through to stdin after a failed forced-search preflight.
- Albert distinguishes search, inference, engine, and generic request failures; it no longer calls the whole brain offline when one edge failed.
- SearXNG requests respect `FCL_SEARXNG_URL` and send explicit JSON/User-Agent headers.
- `qrencode` remains in the normal Homebrew/Linuxbrew utility dependency set.
