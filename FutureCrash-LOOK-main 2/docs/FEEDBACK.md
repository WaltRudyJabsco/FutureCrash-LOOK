# LOOK Feedback

Feedback is semantic, finite, and optional.

Events:

- accept
- complete
- notify
- error

Configuration:

```text
lk feedback
lk feedback sound on|off
lk feedback motion off|subtle|normal
lk sound
lk feedback demo
```

Design rules:

- Sound defaults off.
- Motion defaults subtle.
- Animations stop after a few frames.
- Piped/non-TTY output is always static and silent.
- Callers emit semantic events; the feedback engine owns presentation.
- Audio tones are generated locally and cached as disposable runtime state.
