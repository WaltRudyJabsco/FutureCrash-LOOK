const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert"),
  path = require("path"),
  crypto = require("crypto");
const root = path.resolve(__dirname, "../..");
const bank = {};
vm.createContext(bank);
vm.runInContext(
  fs.readFileSync(root + "/signal-window/mercury-mix-moves.js", "utf8"),
  bank,
);
const moves = bank.MercuryMoves.moves;
assert.equal(moves.length, 12);
assert.equal(new Set(moves.map((m) => m.key)).size, 12);
let Deck;
const messages = [];
const scope = {
  sampleRate: 48000,
  Math,
  Float32Array,
  AudioWorkletProcessor: class {
    constructor() {
      this.port = { postMessage: (m) => messages.push(m) };
    }
  },
  registerProcessor: (_, C) => (Deck = C),
};
vm.createContext(scope);
vm.runInContext(
  fs.readFileSync(root + "/signal-window/mercury-mix-worklet.js", "utf8"),
  scope,
);
const pcm = Float32Array.from(
  { length: 48000 },
  (_, i) => Math.sin(i * 0.052) + 0.1 * Math.sin(i * 0.15),
);
const hashes = new Set();
for (const move of moves) {
  const deck = new Deck(),
    send = (data) => deck.port.onmessage({ data }),
    run = () => {
      const out = [new Float32Array(128), new Float32Array(128)];
      deck.process([], [out]);
      return out[0];
    };
  send({ type: "load", left: pcm, right: pcm, rate: 48000 });
  send({
    type: "gesture",
    token: move.id,
    points: move.points,
    cue: 0.2,
    span: 0.25,
    seconds: 0.5,
  });
  assert.equal(deck.gesture.token, move.id);
  send({ type: "gesture-release", token: move.id });
  const out = [];
  for (let i = 0; i < 188; i++) {
    out.push(...run());
    assert.ok(deck.pos >= 0.2 * 48000 - 0.1 && deck.pos <= 0.45 * 48000 + 0.1);
  }
  assert.equal(deck.gesture, null, move.name + " must finish after one phrase");
  assert.equal(deck.playing, false);
  assert.equal(deck.pos, 0.2 * 48000);
  assert.ok(
    out.some((v) => Math.abs(v) > 0.1),
    move.name + " must use actual PCM even when deck is paused",
  );
  assert.ok(out.every(Number.isFinite));
  hashes.add(
    crypto
      .createHash("sha256")
      .update(Buffer.from(new Float32Array(out).buffer))
      .digest("hex"),
  );
}
assert.equal(hashes.size, 12, "all twelve phrases must produce distinct PCM");
const deck = new Deck(),
  send = (data) => deck.port.onmessage({ data }),
  run = () =>
    deck.process([], [[new Float32Array(128), new Float32Array(128)]]);
const longPcm = Float32Array.from({ length: 96000 }, (_, i) =>
  Math.sin(i * 0.052),
);
send({ type: "load", left: longPcm, right: longPcm, rate: 48000 });
send({ type: "seek", seconds: 0.1 });
send({ type: "play", value: true });
send({
  type: "gesture",
  token: 1,
  points: moves[0].points,
  cue: 0.2,
  span: 0.25,
  seconds: 0.5,
});
for (let i = 0; i < 400; i++) run();
assert.ok(deck.gesture, "held move repeats beyond two cycles");
send({ type: "gesture-release", token: 0 });
assert.equal(
  deck.gesture.release,
  false,
  "old key-up cannot cancel a new move",
);
send({ type: "gesture-stop" });
assert.equal(deck.gesture, null);
assert.ok(Math.abs(deck.pos / 48000 - (0.1 + (400 * 128) / 48000)) < 1e-8);
assert.ok(messages.some((m) => m.type === "gesture-end"));
send({
  type: "gesture",
  token: 2,
  points: [
    [0, 0, 1],
    [0, 1, 1],
  ],
  cue: 0,
  span: 0.2,
  seconds: 0.5,
});
assert.equal(deck.gesture, null, "reject invalid segment times");
send({
  type: "gesture",
  token: 3,
  points: moves[0].points,
  cue: 0.999,
  span: 1,
  seconds: 0.5,
});
for (let i = 0; i < 20; i++) run();
assert.ok(Number.isFinite(deck.pos));
send({ type: "clear" });
assert.equal(deck.gesture, null);
console.log(
  "12 distinct cue-based PCM moves; timed finish, hold/release, stale keys, timeline restoration, validation and track-end bounds passed",
);
for (const move of moves) {
  const plan = bank.MercuryMoves.plan(move, 0.25, 120, 1),
    long = bank.MercuryMoves.plan(move, 1, 120, 1);
  assert.equal(plan.points[0][3], 0, "round the repeat boundary reversal");
  assert.equal(plan.points.at(-1)[3], 0);
  assert.ok(
    Math.abs(long.seconds / plan.seconds - 4) < 1e-8,
    "longer selection must stretch time, not raise pitch: " + move.name,
  );
  assert.ok(
    (bank.MercuryMoves.peakRate(plan.points) * plan.span) / plan.seconds <=
      1.25 + 1e-8,
  );
  assert.ok(
    bank.MercuryMoves.plan(move, 0.25, 120, 0.5).seconds > plan.seconds,
  );
  assert.ok(
    bank.MercuryMoves.plan(move, 0.25, 120, 1.5).seconds < plan.seconds,
  );
  const slow = new Deck();
  slow.port.onmessage({
    data: { type: "load", left: pcm, right: pcm, rate: 48000 },
  });
  slow.port.onmessage({
    data: { type: "gesture", token: 100, cue: 0.2, ...plan },
  });
  assert.ok(slow.gesture, "worklet accepts smooth motion plan");
  slow.port.onmessage({ data: { type: "gesture-release", token: 100 } });
  let previous = null,
    maxSpeed = 0;
  for (let frame = 0; frame < Math.ceil(plan.seconds * 48000); frame++) {
    const out = [[new Float32Array(1), new Float32Array(1)]];
    slow.process([], out);
    if (
      slow.gesture &&
      previous !== null &&
      slow.gesture.points[slow.gesture.segment][2] > 0
    )
      maxSpeed = Math.max(maxSpeed, Math.abs(slow.pos - previous));
    previous = slow.pos;
    assert.ok(Number.isFinite(out[0][0][0]));
  }
  assert.ok(slow.gesture === null || slow.gesture.age <= 1);
  assert.ok(maxSpeed <= 1.26, "audible physical scratch speed stays bounded");
}
console.log(
  "All 12 smooth plans preserve speed across selection lengths and respect independent pace",
);
