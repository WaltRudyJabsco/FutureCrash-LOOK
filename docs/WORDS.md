# Offline words

`lk words` provides an optional portable English reference for travel and local
writing. It has no AI/model dependency. Normal lookups, spelling and word finding
use local files only; nothing is sent to a dictionary website.

## Install and discover

Open **lk settings → Offline words**, or run:

```sh
lk words status
lk words setup
```

Setup downloads about **12 MB** and builds roughly **60 MB** of local files per
computer: Open English WordNet 2025 and Spylls 0.1.7 with its bundled SCOWL US
English dictionary. Fixed downloads are SHA-256 checked. A failed download/build
keeps the previous reference index. Normal LOOK installation only installs the
command; it does not silently download reference data or spelling engines.

Keep this small baseline on each traveling laptop. A reference on another
Fabric node cannot answer when that node is unreachable. You can explicitly
install or query on a paired node with `--node NAME`; node-side setup requires
a confirmed request. Existing user preferences and personal vocabulary survive
runtime upgrades. These datasets are separate from Wiki archives.

## Use

```sh
lk words lookup serendipity
lk words lookup ran
lk words spell 'The runners were running through a beautiful garden.'
lk words spell 'colour and favourite' --language en_GB
lk words find 'seren*'
lk words find '?ight'
lk words add 'Zoë'
lk words lookup serendipity --json
```

Definitions include part of speech, recorded usage examples and related senses.
Synonyms and antonyms stay attached to their meanings; broader, more specific
and similar concepts are labelled separately. Recorded irregular forms resolve
to their lemmas. This is not a complete historical, slang or names dictionary.

## Word desk

Bare `lk words` or **`lk wd`** opens its own persistent terminal interface.
The alias accepts all the same arguments, for example `lk wd lookup obtuse`.

On a blank local desk, **Word of this launch** offers a short, sourced definition
from the installed offline WordNet. A small curated learning pool is shuffled
without repeats until it cycles through, and avoids an immediate repeat at the
cycle boundary. Its progress stays local to this OS account. The card disappears
on the first typed/pasted text or submitted search and does not return after
cancelling that input. Explicit lookup/spelling/pattern queries have no card.
Missing reference data simply keeps the setup guidance; this feature never starts
a download or inference request.

 Direct `lookup`,
`spell` and `find` commands also open that desk in a terminal with the requested
query ready. Outside a terminal, the bare command prints status; explicit queries
and `--json` remain script-friendly.

- The bare desk starts with its input active: type a word and Enter.
  From results, `/` edits the current query; Ctrl-U clears it. Enter submits it.
  Queries run in the background so typing and Escape remain responsive.
- **1** Meaning, **2** Synonyms, **3** Antonyms, **4** Spelling, **5** Patterns.
  Tab cycles views. While editing, digits and uppercase letters remain text.
- Arrow keys scroll; Shift-Up/Down page and Shift-Left/Right jump to ends.
  Enter on a thesaurus/pattern word opens its meaning; `b` returns to the previous
  query. Similar related words are labelled separately from direct synonyms.
- `p` pastes the system clipboard; `Z` or editor Ctrl-Y inserts from LK Clip.
  Bracketed paste is literal text. Longer pasted text selects Spelling.
- `y` copies the selected word/entry to both the system clipboard and LK Clip.
  `c` copies the working query/text. These actions do not enable background
  clipboard capture or share clipboard history over Fabric.
- Spelling shows only flagged/unknown words and suggestions. Select a suggestion
  and Enter to replace that exact word throughout the working text; `c` copies
  the result. Source documents are never changed. `a` accepts a flagged word in
  local personal vocabulary. No suggestions are applied automatically.
- `W` opens an adjacent shell pane from results (Esc leaves input first). Existing Option/Alt-Shift-W focus and
  Ctrl-Shift-W close controls remain terminal-owned. In tmux use Ctrl-B, O for
  focus and `exit` to close the shell. Editing `W` is always literal text.
- `S` presents optional setup with its download/storage summary; `?` shows help.
  Escape cancels input back to results, then closes the desk from results.
  Narrow panes use a shorter footer; `?` shows the additional controls.

Machine-readable
`--json` output serves scripts. The word finder accepts `*` and `?`; quote the
pattern so the shell does not expand it first. Results are bounded to 40 entries.
Spelling accepts up to 4,000 characters / 50 distinct words per check.

## System fallback and spelling

- Installed **Hunspell**, then **Aspell**, take priority for spelling, using the
  requested `en_US` or `en_GB` dictionary. Checks are batched into one process.
- The portable engine also discovers matching Hunspell dictionary files in
  system directories and macOS `~/Library/Spelling` / `/Library/Spelling`.
- The included portable dictionary is **US English**. GB checking needs an
  installed matching dictionary; it never silently applies US rules to GB text.
- Without a full spelling engine/dictionary, WordNet and available system word
  lists provide vocabulary recognition and basic candidate suggestions. Unknown
  words are labelled **not in available vocabulary**, not proven misspellings.
- Installed **WordNet `wn`** provides definitions when the portable dictionary
  has no match or is not installed. This command reads local WordNet data.
- Personal vocabulary is in `~/.config/look/personal-words.txt`; `add` changes
  only that local list. Names and intentional inventions can be accepted there.

The portable reference does not import Apple's proprietary Dictionary databases.
It also does not perform grammar checking or silently rewrite your prose.

## Local AI

LO, Signal and Albert share the read-only `word_reference` tool with actions
`lookup`, `spell`, `find` and `status`. It returns the same local entries and
sources as the CLI. Setup and personal-vocabulary writes are deliberately not
model tool actions. The tool is available to small local models; actual tool
selection still depends on the model. Creative suggestions should be labelled
as suggestions, not attributed to a dictionary entry that was never retrieved.

## Sources

- [Open English WordNet 2025](https://en-word.net/downloads), developed by the
  Open English WordNet team from Princeton WordNet. CC BY 4.0 applies to OEWN
  additions; the underlying WordNet terms also apply. The index retains edition,
  source, checksum, attribution and [license reference](https://github.com/globalwordnet/english-wordnet/blob/main/LICENSE.md).
- [Spylls 0.1.7](https://pypi.org/project/spylls/), the pure-Python Hunspell
  implementation, with bundled SCOWL `en_US` data. Package license/metadata are
  retained alongside the local runtime. System dictionaries retain their own
  sources and licenses.
