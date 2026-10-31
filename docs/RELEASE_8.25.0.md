# 8.25.0 — Offline words and Kinetic Mobile

Bundle/node/Albert integration **8.25.0**; LOOK **4.72.0**.

`lk words` adds optional local definitions, examples, synonyms/antonyms, word
patterns, spelling checks and personal vocabulary. Explicit setup downloads about
12 MB and builds approximately 60 MB of local reference files. Open English
WordNet 2025 supplies the indexed meanings and relationships; Spylls 0.1.7 and its
bundled SCOWL US dictionary supply portable inflection-aware spelling without
native dependencies or a model.

Installed Hunspell/Aspell, matching system dictionaries, local WordNet and system
word lists remain available as named sources/fallbacks. GB spelling requires a
matching system dictionary. Vocabulary absence is not treated as proof of error.
Normal queries never use the network; fixed setup downloads are checksum-checked
and a failed setup preserves the existing reference. Sources and license metadata
are retained. See [Offline words](WORDS.md) for examples and limitations.

LO, Signal and Albert share a read-only `word_reference` tool. It cannot install
packages or alter personal vocabulary. Settings exposes setup/status; paired
nodes support explicit confirmed setup and bounded queries.

**Kinetic Mobile** joins the ambient visualizer rotation: a hanging sculpture
with connected rods and gently swaying weights. It respects pause, terminal
bounds and the existing ten-second cycle. It is ambient, not an audio analyzer.

Validation: **594 affected tests passed**. Real-data checks built 107,558 meaning
records and verified definitions, irregular forms, inflected spelling and word
patterns. The actual M3 setup and CLI were verified; no Wiki downloads changed.
Generated references, shell syntax, installer dry-run and diff checks passed.
