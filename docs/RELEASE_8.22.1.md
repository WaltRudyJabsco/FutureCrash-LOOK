# 8.22.1 — Wiki archive navigation

Bundle/node/Albert integration **8.22.1**; LOOK **4.69.1**.

The full Wikipedia archive is verified and readable, but its landing view could
leave users with no usable links or in-view search. Wiki now supports archive
search directly inside any article, retains back history, and resolves source
Wikipedia links locally for matching English archives. Exact article paths lead
search results.

The misleading OFFLINE heading becomes SAVED ARCHIVE with an explicit owner.
The shelf displays reader readiness, skips redundant setup and offers o to choose
a Fabric owner. Reader setup remains node-local; no archive copy or download is
triggered by navigation.

Validation: 178 affected tests passed, including real ZIM search, landing-page
link normalization, in-article search/history, reader readiness and owner choice.
Generated references, shell syntax and installer dry-run checks passed.
