# Future Crash + LOOK 1.6.12

This release separates three kinds of continuity:

1. **Recent conversation** — literal completed exchanges, persisted immediately across LO sessions.
2. **Candidate memory** — semantic notes with importance and natural decay.
3. **Long-term memory** — a compact background consolidation of candidates that remain useful.

A candidate reaching zero is forgotten; it is not promoted. Long-term consolidation happens while candidates are still strong or reinforced.

LO also gains one deterministic multi-file creation tool (`create_text_files`, maximum 32 new text files) and the shell helpers `lcp`, `lmv`, and `lrm` accept multiple paths. LOOK's existing filer batch-selection machinery is unchanged.

LOOK is 3.10.1. Future Crash remains 1.1.7.
