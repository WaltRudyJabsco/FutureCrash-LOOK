# Future Crash + LOOK 2.2.3

Versions:

- Future Crash + LOOK: 2.2.3
- LOOK: 4.2.3
- Future Crash: 1.1.10

## Receipts are reality

Successful filesystem receipts now carry canonical absolute paths.

```text
CREATE FILES OK · 1 files
  /Users/name/Downloads/test-boilerplate.html
  undo available · lk undo
```

and:

```text
WRITE OK · /Users/name/Downloads/file.html · 123 bytes
```

The model is instructed that these receipts are authoritative. Prior conversation, recent memory, or assumptions about the current directory must never override them.

## Mutation-request classification

The host's anti-hallucination guard now distinguishes:

```text
make a file in Downloads        → execution request
could you move this file        → execution request

did you make the file?          → discussion/question
where did you make it?          → discussion/question
you did make it correctly       → retrospective
good job making that file       → feedback
```

This prevents successful earlier work from being contradicted on the next conversational turn.

## Terminal ownership

Terminal/tab state now distinguishes all four situations:

```text
● LOOK
● LO
● FUTURE CRASH
◌ FUTURE CRASH · SHELL · <folder>
```

The last state means Future Crash is still running as the parent, but you are temporarily using its child shell. Exiting that shell restores `● FUTURE CRASH`.
