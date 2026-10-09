# 8.13.0 — Notebook Markdown preview

The note viewer renders common Markdown rather than showing its source marks:
headings, bold, italic, strikethrough, bullet/numbered lists, task checkboxes,
quotes, links and inline/fenced code. Links keep visible destinations; code
keeps literal text. Unicode cell widths and ANSI styles respect box geometry.

E continues to edit the original Markdown. Saving returns to the rendered
preview; V opens the same source file. Preview rendering never changes stored
text. Tables and HTML remain plain text; no images or linked content are fetched.
The new renderer uses only the Python standard library and is installed with LOOK.

Bundle/Albert 8.13.0; LOOK 4.60.0; Future Crash remains 1.2.5.

Validation: 991 tests pass, including Markdown formatting, literal code,
Unicode wrapping and preview/source separation. A real PTY preview → edit →
save → preview round trip passes. Generated help, code-health, installer
syntax and Python 3.10 parsing checks pass.
