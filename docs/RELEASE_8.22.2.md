# 8.22.2 — Wikipedia contents navigation

Bundle/node/Albert integration **8.22.2**; LOOK **4.69.2**.

Some Wikipedia ZIM landing pages contain topic names but no usable hyperlink
attributes. Rebuild these links only when the topic has a verified entry in the
same archive. No network lookup or invented destination is used. Retains the
in-article search, exact-title results, reader readiness and owner picker from
8.22.1. Downloaded archives and reader installations are preserved.

Validation: 179 affected tests passed, including real ZIM search, verified
landing topics, article search/history, owner selection and reader readiness.
