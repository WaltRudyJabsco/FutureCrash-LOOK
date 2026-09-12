# Future Crash + LOOK 1.6.13

Tiny wrapper-hardening release.

`lmv a.txt b.txt ../dst/` and `lcp a.txt b.txt ../dst/` now explicitly treat the final argument as the destination by popping it from the source array before invoking LOOK's existing batch engine.

LOOK is 3.10.2. Future Crash remains 1.1.7.
