# 5.4.9 — Stable Safari Output Picker

Signal no longer rebuilds the media card while a native output picker is open. On iPhone/iPad Safari, touching or focusing OUT freezes only that control's render lifecycle while normal media state continues to be observed. Change commits the selected endpoint; blur reconciles once. This preserves the exact DOM `<select>` element owned by the native iOS picker and prevents the popup from disappearing during the one-second media poll.
