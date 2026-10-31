# LK Latin

`lk latin` is an offline classroom around the complete Benjamin L. D'Ooge,
*Latin for Beginners* (1911) course. It bundles pronunciation, all 79 numbered
lessons, connected readings, three appendices, the index, lesson vocabularies
and Latin–English/English–Latin dictionaries. There is no speech, model download,
account, inference, or online lookup in this feature.

## Start

```
lk latin
lk latin list
lk latin lesson 18
lk latin practice --lesson 18
lk latin review
lk latin words puella
lk latin grammar "ablative absolute"
lk latin progress --json
lk latin progress --strict-macrons on
lk latin export "/path/latin-progress.json"
```

The classroom offers Continue, Course, Practice, Review, Words, Grammar, Readings,
Progress and About. All lessons are open; there are no artificial unlocks or
mandatory streaks. Start with pronunciation (unit 0), then lessons 1–79. The source
is a historical textbook, including period narratives and assumptions; LOOK does
not silently modernize it. Grammar extends through noun declensions, verb tenses
and voices, pronouns, comparison, numerals, participles, gerunds/gerundives,
subjunctive constructions and indirect discourse.

## Controls

| Context | Key | Action |
| --- | --- | --- |
| Lists | Up/Down | Move selection |
| Lists and text | Shift-Up/Down | Page up/down |
| Lists and text | Shift-Left/Right | Beginning/end |
| Lists | Enter | Open |
| Lists | `/` | Filter |
| Text | Left/Right | Previous/next numbered lesson |
| Text | `/`, then `n` | Find, then next occurrence |
| Lesson | `p` | Practice this lesson |
| Lesson | `v` | Browse its supplied vocabulary |
| Lesson | `m` | Toggle studied mark |
| Vocabulary review | Enter, then 1 or 2 | Reveal; review again or recalled |
| Any view | Esc | Return; from Home, exit |

Text reflows to terminal width while retaining indented paradigms. Controls use
LOOK's existing terminal palette, row selection and Unicode answer editor. No
Kitty-only functionality is required. The existing key decoder handles arrows,
Shift-arrows and bracketed paste. Escape in an answer cancels without grading.

## Practice and honest assessment

LOOK adds 80 original concept checks, 474 typed morphology cards, and 481 source
lesson-vocabulary cards. Concept choices and typed forms are checked; open-ended
translations in the textbook are **self-assessed**, not machine-graded. There is
no fabricated answer key. Vocabulary meanings are revealed before the learner
chooses a self-rating. Review totals therefore combine checked and self-reported
recall and should not be treated as an examination score.

Typed drills request standard uncontracted textbook forms. Listed alternatives,
including second-person passive -re and third-person perfect -ēre, are accepted.
Macrons/breves are optional by default; strict mode checks vowel marks. Case,
normal spacing, ligatures, j/i and consonantal v/u variants are normalized. A
studied mark records the learner's reading choice, not mastery.

Practice draws from the chosen/current unit and earlier material. Review selects
previously attempted cards that are due, without quietly introducing later
material. Correct recalls are scheduled at 1, 3, 7, 14, 30 and 60 days; a miss
returns after ten minutes. A session is bounded to twelve cards. The main lesson's
concept check and relevant form/vocabulary cards remain accessible with `p`.

## Local state

Progress and reading position are saved in
`~/.local/share/look/latin/progress.sqlite3`, separate from installed code and
updates. SQLite serializes review writes from multiple classroom sessions.
Opening grammar/dictionary references does not replace the last numbered lesson.
Exports are explicit, private and refuse to replace an existing file. There is
no automatic Fabric synchronization or clipboard capture added by Latin.
Read-only list/lesson/dictionary text commands do not create learner state.

## Source and attribution

Complete source: https://www.gutenberg.org/ebooks/18251
Downloaded text: https://www.gutenberg.org/cache/epub/18251/pg18251.txt
Author: Benjamin L. D'Ooge. Source credits: Louise Hope, Dave Maddock and the
Online Distributed Proofreading Team. The edition was last updated June 12, 2022.
Project Gutenberg identifies the book as public domain in the USA. The bundled
edition retains the full Project Gutenberg licence, credits and original notices;
see About or the source/licence reference in the classroom.

`look/latin_course.py` is a data-only wrapper around the supplied UTF-8 text, with
line endings normalized to LF. Its TEXT value has SHA-256:

`09697d0ee38ef370b3e6eff6e1a4313438e2a62e98a92c4862b5ca723a5fd0a3`

LOOK's concept checks and morphology generation are separate in `latin_data.py`
and `latin_core.py`. The source textbook's spelling, inflectional alternatives,
footnotes and historical exercises are kept visible rather than silently replaced.
