# Living With LOOK

LOOK is easiest to understand as a way of inhabiting a terminal rather than as a collection of commands.

Future Crash is the place you can leave alive. LOOK is how you move around the computer. LO is the intelligence you bring into whatever you are doing.

## An ordinary day

You can leave Future Crash running in a terminal when you are not actively using it. It is ambient: text, Signal Field, threads, observations, small pieces of motion. When you want the machine back, leave Future Crash for the shell and work normally. LOOK is not meant to replace the shell; it makes the shell more navigable.

When you know exactly what you want, type the ordinary command. When you know roughly where something is, use LOOK's filer/find surfaces. Filter, move through directories, collect files into a working set, and act on the set as one thing.

A useful transition happens when files stop being objects and become a question. Select the files and hand them to LO. Their paths become explicit context and LO can inspect them with the permissions of the current access profile. You do not need to paste their contents into chat.

If the task begins as a thought rather than a file operation, start with `lo`. LO can converse normally, inspect the workspace when that is actually relevant, use deterministic file tools for mutations, and use information edges for facts that should come from outside the model.

Long work does not need to make the terminal feel frozen. Background work can continue as jobs; events return when something finishes or fails. Future Crash and LOOK can surface those events without requiring you to stare at a spinner.

## Files are actions, not claims

LOOK's file philosophy is simple: when LO says it copied, moved, created, or removed something, a host tool should have performed the operation. File mutations are grouped where possible and connected to the undo journal.

This is why LOOK distinguishes conversation from execution. A language model is good at understanding what you mean. Python and the operating system are better at deterministically moving bytes.

Use LO to decide. Use tools to do.

## Information has edges

LO also distinguishes knowing from retrieving.

When a question fits a canonical public information source, LOOK prefers that source to model memory or generic web search:

- WEATHER — current conditions and forecasts
- PLACE — geographic resolution
- WIKI — readable encyclopedic background
- DATA — structured Wikidata entities
- PAPERS — Crossref bibliographic and DOI metadata
- ARCHIVE — Internet Archive objects
- WEB — general search when no canonical edge fits

A canonical result carries a small receipt: source, retrieval time, source time when available, and how directly the answer follows from the source.

The vocabulary is intentionally qualitative:

- DIRECT — the canonical source returned the information.
- DERIVED — LOOK calculated or combined values from canonical data.
- SEARCHED — general web results were interpreted.
- MODEL — no external verification was performed.

This is not a claim that a database can never be wrong. It tells you what kind of evidence is underneath the sentence.

## The system remembers, but remains inspectable

Recent conversation provides continuity across sessions. Longer-lived memory is distilled separately. Skills capture useful local craft. Personalities change voice and posture without changing the underlying permissions.

All of that belongs to the LOOK profile rather than to the installed program.

`lk profile backup` preserves the evolving profile. `lk profile export` makes it portable. A new machine can receive a clean LOOK installation and then recover the accumulated identity without importing old runtime debris or secrets.

## The intended rhythm

Future Crash can remain alive when the terminal is idle.

The shell remains the fastest path when you know the command.

LOOK is the visual/file control surface when you need to find, collect, inspect, move, or hand off things.

LO is the conversational layer when intent is easier to express in language than syntax.

Canonical information edges are the route for facts where provenance matters.

Background jobs and events let slower AI work finish without owning your attention.

The result is not an AI application sitting beside the operating system. It is a small layer connecting the shell, files, local models, public information, memory, and ambient terminal space while leaving each of those pieces recognizable.
