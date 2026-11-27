/* Playable interpretations of named scratch techniques, not recorded effects.
 * Each point is [fraction of phrase, fraction of selected sound, open gate].
 * Motion and cuts are sent together to the audio thread, never browser timers. */
(function (root) {
  "use strict";
  const stroke = (t) => (t <= 0.5 ? t * 2 : (1 - t) * 2);
  const base = [
    [0, 0, 1],
    [0.12, 0.1, 1],
    [0.35, 0.8, 1],
    [0.5, 1, 1],
    [0.65, 0.8, 1],
    [0.88, 0.1, 1],
    [1, 0, 1],
  ];
  const pulse = (cuts) =>
    [0, ...cuts, 1].map((t, i) => [t, stroke(t), i % 2 ? 0 : 1]);
  const moves = [
    {
      id: "baby",
      key: "a",
      name: "Baby",
      hint: "Open forward and back",
      points: base,
    },
    {
      id: "forward",
      key: "s",
      name: "Forward",
      hint: "Hear the push; silent return",
      points: [
        [0, 0, 1],
        [0.5, 1, 0],
        [1, 0, 0],
      ],
    },
    {
      id: "reverse",
      key: "d",
      name: "Reverse cut",
      hint: "Silent push; hear the pull",
      points: [
        [0, 0, 0],
        [0.5, 1, 1],
        [1, 0, 0],
      ],
    },
    {
      id: "stab",
      key: "f",
      name: "Stab",
      hint: "Sharp push; closed quick return",
      points: [
        [0, 0, 0],
        [0.08, 0, 1],
        [0.32, 0.9, 0],
        [0.43, 0, 0],
        [0.58, 0, 1],
        [0.82, 0.9, 0],
        [1, 0, 0],
      ],
    },
    {
      id: "chirp",
      key: "g",
      name: "Chirp",
      hint: "Close around the turn, open on the pull",
      points: [
        [0, 0, 1],
        [0.38, 0.9, 0],
        [0.5, 1, 0],
        [0.62, 0.9, 1],
        [0.96, 0.03, 0],
        [1, 0, 0],
      ],
    },
    {
      id: "transformer",
      key: "h",
      name: "Transformer",
      hint: "Rhythmic cuts through both strokes",
      points: pulse([
        0.06, 0.12, 0.19, 0.25, 0.32, 0.38, 0.56, 0.62, 0.69, 0.75, 0.82, 0.88,
      ]),
    },
    {
      id: "flare",
      key: "j",
      name: "1-click flare",
      hint: "One closed cut inside each stroke",
      points: pulse([0.24, 0.27, 0.74, 0.77]),
    },
    {
      id: "two-flare",
      key: "k",
      name: "2-click flare",
      hint: "Two closed cuts per stroke",
      points: pulse([0.16, 0.19, 0.32, 0.35, 0.66, 0.69, 0.82, 0.85]),
    },
    {
      id: "tear",
      key: "l",
      name: "Tear",
      hint: "Break the pull into stepped motions",
      points: [
        [0, 0, 1],
        [0.38, 1, 1],
        [0.53, 0.6, 1],
        [0.63, 0.6, 1],
        [0.77, 0.25, 1],
        [0.86, 0.25, 1],
        [1, 0, 1],
      ],
    },
    {
      id: "scribble",
      key: ";",
      name: "Scribble",
      hint: "Short rapid forward/back movements",
      points: Array.from({ length: 17 }, (_, i) => [
        i / 16,
        i % 2 ? 0.4 : 0,
        1,
      ]),
    },
    {
      id: "crab",
      key: "q",
      name: "Crab-style",
      hint: "A rapid cluster of fader cuts",
      points: pulse([
        0.1, 0.13, 0.16, 0.19, 0.22, 0.25, 0.28, 0.31, 0.6, 0.63, 0.66, 0.69,
        0.72, 0.75, 0.78, 0.81,
      ]),
    },
    {
      id: "echo",
      key: "w",
      name: "Echo scratch",
      hint: "Repeated pushes, each softer",
      beats: 2,
      points: [
        [0, 0, 1],
        [0.16, 1, 0],
        [0.25, 0, 0.7],
        [0.41, 1, 0],
        [0.5, 0, 0.45],
        [0.66, 1, 0],
        [0.75, 0, 0.22],
        [0.91, 1, 0],
        [1, 0, 0],
      ],
    },
  ];
  root.MercuryMoves = {
    moves,
    byKey: (key) => moves.find((move) => move.key === key),
    byId: (id) => moves.find((move) => move.id === id),
  };
})(globalThis);
