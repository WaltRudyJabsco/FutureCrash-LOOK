# Resource Context

LOOK/LO treats files and folders as explicit resources rather than prose.

Sources, strongest first: terminal/Finder drop or explicit path; LOOK marked selection; conversational referent; locator/search candidate.

`L` in LOOK already hands marked paths directly to LO. LO now also recognizes path arguments at launch and quoted/escaped path-shaped input pasted into an active session. Directories remain directory resources; their contents are not injected into model context.

Examples:

    lo summarize ~/Desktop/report.pdf
    lo compare ~/Desktop/a.pdf ~/Desktop/b.pdf
    lo organize ~/Desktop/photos/

Finder/macOS and common Linux terminal drag-and-drop normally insert a quoted or escaped path, so the same mechanism acts as terminal attachments without terminal-specific GUI code.

The future desktop GUI should produce the same resource list instead of inventing a separate attachment architecture.


## Vision and context governance (3.3.2)

Image ResourceRefs are attached through Ollama's native `images` field when the selected model advertises vision. The same path works for CLI/Finder drops and LOOK selections.

ResourceRefs are handles, not prompt contents. A single small text file may receive a cheap preview; multiple or large documents remain lazy. `read_file` accepts `offset` and `max_chars` so LO can gather bounded evidence across documents while retaining compact conclusions.
