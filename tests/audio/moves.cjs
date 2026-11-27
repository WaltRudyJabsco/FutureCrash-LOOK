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
