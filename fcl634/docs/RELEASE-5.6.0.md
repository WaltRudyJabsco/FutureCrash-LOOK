# 5.6.0 — Fabric File Catalog

LOOK now maintains a lightweight SQLite metadata catalog for ordinary files, extending the media-catalog lesson to the rest of the filesystem. `lk scan [ROOT]` records paths, names, extensions, sizes and modification times without reading or hashing file contents; a bare `lk scan` uses the home directory with conservative cache/build/hidden-directory exclusions. `lk catalog` reports local coverage and `lk find QUERY` accepts useful plain-language metadata terms such as `pdf`, `recent`, `yesterday`, and `largest`.

Each Unified Node publishes its local catalog through `/v1/files/catalog`; `/v1/files/fabric` unions currently reachable node catalogs. `lk find` prefers that Fabric union when the node is available and falls back to the local SQLite catalog in Island Mode. Paths remain node-owned metadata: cataloging never grants new filesystem access and never transfers file bytes.

Fresh installs seed the first home metadata scan in the background. Expensive identity, content extraction, FTS and semantic understanding remain deliberately deferred layers rather than costs paid during discovery.

