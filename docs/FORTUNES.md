# Fortune aphorisms

The standard `fortune` art card and compact `fortune-cookie` slip both draw
from the same offline collection of **293 selected sayings**. Default wording
is not generated or rephrased by an AI. Explicit custom wording remains available.
The art card still includes a saved Museum image and credit; the cookie has only
the aphorism and lucky numbers.

The selection uses these public-domain historical English texts:

- W. Scarborough, *A Collection of Chinese Proverbs* (1875),
  [Cornell copy at Internet Archive](https://archive.org/details/cu31924023892981),
  [transcribed text](https://archive.org/download/cu31924023892981/cu31924023892981_djvu.txt).
- *The Analects of Confucius*, translated by James Legge,
  [Project Gutenberg ebook 3330](https://www.gutenberg.org/ebooks/3330),
  [Gutenberg mirror text](https://gutenberg.pglaf.org/cache/epub/3330/pg3330.txt).

These are traditional proverbs and Analects excerpts, not 293 quotations all
attributed to Confucius. The selected wording was checked against those texts.
The collection favors short, self-contained sayings and excludes the draft's
obvious OCR errors, isolated dialogue fragments and context-dependent remarks.
Historical translations retain their period vocabulary.

## Rotation and printing

Every prepared fortune with a named printer draws the next saying from its
owner's persisted SQLite sequence. Fortune and fortune-cookie share the cursor,
including when requested through LO, Signal, Albert or another Fabric node.
Printers on the same owner share that sequence. Separate owners have separate
cursors; this does not require global coordination or Internet access.

The first draw on a fresh owner starts at a random point. All 293 entries are
visited before repeating. Concurrent draws are serialized; restarts preserve
the cursor. Updating the collection preserves a valid position modulo its size.
Preparation consumes a draw even if the user later discards the print plan.
Custom wording does not consume a draw. A preview without a printer samples the
same collection locally and does not advance an owner's print sequence.

```sh
lk print fortune --printer "Little Printer"
lk print fortune-cookie --printer "Little Printer"
lk print fortune-cookie "Your own words here." --printer "Tiny Printer"
```

These commands prepare a job for review and show the explicit send command.
An explicit assistant request such as “print a fortune cookie on Little Printer”
uses the existing one-attempt print workflow.
