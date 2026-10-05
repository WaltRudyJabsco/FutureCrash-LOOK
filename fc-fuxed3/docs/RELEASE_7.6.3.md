# 7.6.3 — STILL FRAME

LOOK's preview is now an edge job rather than a timer-driven pager state. The pager blocks on real keyboard input or one actual preview-completion event. Selection/query changes supersede older background preview generations; stale workers never write terminal graphics. A completed current preview replaces the right-side portal once without rebuilding the filtered frame. Idle means idle.
