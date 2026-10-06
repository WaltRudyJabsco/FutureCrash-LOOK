# 7.5.3 — LOOK FEEL

A focused personalization pass over 7.5.2.

## LOOK presentation

- Nerd Font glyphs are now the default; `lk settings` can restore Classic markers.
- Image preview: `Auto`, `Graphics`, `ASCII`, `Off`. Auto uses a clearly advertised Kitty, iTerm2, or Sixel terminal protocol through Chafa and otherwise falls back to symbol rendering.

## Feedback

- Sound modes are `Off`, `Subtle`, and `Expressive`.
- Feedback is attached to semantic operation receipts; ordinary navigation is silent.
- Existing boolean sound preferences migrate: `true` becomes `subtle`.

## Speech

- Shared preference: `~/.config/look/speech.json`.
- Presets: Albert, Warm, Crisp, Deep, Max, Philosopher, Pirate, WOPR.
- Personality voice overrides can be disabled globally.
- `lk voice preview` uses the canonical Fabric `audio.speak` primitive.

## Navigation

No interaction changes from 7.5.2: paging does not select; Up/Down creates a browse selection; neutral Enter starts filter; selected Enter opens.
