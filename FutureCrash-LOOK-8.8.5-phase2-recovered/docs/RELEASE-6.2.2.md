# Future Crash + LOOK 6.2.2 — Stay Attached

Signal Window 1.10.2 fixes Chromium browser video playback by preserving the active `<video>` DOM node across player-card rerenders. The player previously rebuilt the card with `innerHTML=''`; Chrome correctly treated removal of the playing media element as an implicit pause and rejected the outstanding `play()` promise. Safari tolerated the lifecycle mistake, masking it during earlier testing.

Invariant: once a browser media element owns playback, presentation/UI refreshes may update controls around it but must not detach that element.
