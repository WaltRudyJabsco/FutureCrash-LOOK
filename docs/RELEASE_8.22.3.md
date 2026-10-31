# 8.22.3 — Wiki link paging and hints

Bundle/node/Albert integration **8.22.3**; LOOK **4.69.3**.

Links and in-article search results now use a paged selector with arrows,
Shift-arrows, number-plus-Enter and immediate two-letter selection. This avoids
long prompts scrolling the beginning of the list off screen.

Press f in an article to show inline two-letter hints. Type the code to follow;
Escape cancels without leaving the article. Normal reading retains clean text,
and back history preserves the previous position. Matching archive source links
and verified linkless landing-page topics use the same stable codes.

Validation: 182 affected tests passed, including real ZIM hinted extraction,
paging across 119 links, numeric/two-letter selection, cancellation and follow/back.
Generated references, shell syntax and installer dry-run checks passed.
