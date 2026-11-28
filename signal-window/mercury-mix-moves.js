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
  const pulse = (cuts) => {
    let gate = 1;
    // Fader cuts must not erase the record's halfway turnaround.
    return [...new Set([0, 0.5, ...cuts, 1])]
      .sort((a, b) => a - b)
      .map((t) => {
        if (cuts.includes(t)) gate = 1 - gate;
        return [t, stroke(t), gate];
      });
  };
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
  const REFERENCE_SPAN = 0.25;
  const NATURAL_PEAK_RATE = 1.25;
  // Monotone Hermite tangents round a hand's acceleration and reversal without
  // overshooting the marked sound. Gate points along one stroke stay smooth.
  function smoothPoints(points) {
    const cyclic = points[0][1] === points[points.length - 1][1];
    const slopes = points
      .slice(0, -1)
      .map((p, i) => (points[i + 1][1] - p[1]) / (points[i + 1][0] - p[0]));
    return points.map((p, i) => {
      let tangent = 0;
      if (i === 0) tangent = cyclic ? 0 : slopes[0];
      else if (i === points.length - 1) tangent = cyclic ? 0 : slopes[i - 1];
      else if (slopes[i - 1] * slopes[i] > 0)
        tangent = 2 / (1 / slopes[i - 1] + 1 / slopes[i]);
      return [...p, tangent];
    });
  }
  function peakRate(points) {
    let peak = 0;
    for (let i = 0; i < points.length - 1; i++) {
      const p = points[i],
        q = points[i + 1];
      if (!p[2]) continue;
      const h = q[0] - p[0],
        a = 6 * p[1] + 3 * h * p[3] - 6 * q[1] + 3 * h * q[3],
        b = -6 * p[1] - 4 * h * p[3] + 6 * q[1] - 2 * h * q[3],
        c = h * p[3];
      const at = (u) => Math.abs((a * u * u + b * u + c) / h);
      peak = Math.max(peak, at(0), at(1));
      const vertex = Math.abs(a) > 1e-10 ? -b / (2 * a) : -1;
      if (vertex > 0 && vertex < 1) peak = Math.max(peak, at(vertex));
    }
    return peak;
  }
  function plan(move, span, tempo, pace = 1) {
    span = Math.max(0.001, Math.min(1, Number(span) || REFERENCE_SPAN));
    tempo = Math.max(40, Math.min(400, Number(tempo) || 120));
    pace = Math.max(0.5, Math.min(1.5, Number(pace) || 1));
    const points = smoothPoints(move.points);
    // Selection length buys time, not pitch. Intricate moves get enough time
    // to keep their audible strokes near normal vinyl speed at Natural pace.
    const beatSeconds =
      (((move.beats || 1) * 60) / tempo) * (span / REFERENCE_SPAN);
    const motionSeconds = (peakRate(points) * span) / NATURAL_PEAK_RATE;
    return {
      points,
      span,
      seconds: Math.max(0.1, Math.max(beatSeconds, motionSeconds) / pace),
    };
  }
  root.MercuryMoves = {
    moves,
    plan,
    peakRate,
    smoothPoints,
    byKey: (key) => moves.find((move) => move.key === key),
    byId: (id) => moves.find((move) => move.id === id),
  };
})(globalThis);
