const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert"),
  path = require("path");
const root = path.resolve(__dirname, "../.."),
  context = { Float32Array, Math, Set, Number };
vm.createContext(context);
vm.runInContext(
  fs.readFileSync(root + "/signal-window/mercury-mix-dsp.js", "utf8"),
  context,
);
const dsp = context.MercuryDSP;
assert.deepStrictEqual(Array.from(dsp.fader(0)), [1, 0]);
assert.ok(dsp.fader(1)[0] < 1e-10);
assert.ok(
  Math.abs(dsp.fader(0.5)[0] ** 2 + dsp.fader(0.5)[1] ** 2 - 1) < 1e-10,
);
assert.equal(dsp.keyPosition(new Set(["a", "s"]), "left"), 1 / 6);
assert.equal(dsp.keyPosition(new Set(["j", "k"]), "right"), 1 / 6);
assert.equal(dsp.keyPosition(new Set(["j"]), "left"), null);
assert.ok(dsp.fader(0, "cut", true)[0] === 0);
assert.equal(dsp.wrap(-1, 0, 4), 3);
for (const index of [0, 1]) {
  const demo = dsp.demo(index);
  assert.ok(demo.left.some((v) => Math.abs(v) > 0.1));
  assert.ok(demo.left.every(Number.isFinite));
  assert.equal(demo.bpm, index ? 124 : 120);
  assert.equal(dsp.peaks(demo.left, demo.right).length, 1000);
}
let Deck;
const messages = [],
  scope = {
    sampleRate: 48000,
    Math,
    Float32Array,
    AudioWorkletProcessor: class {
      constructor() {
        this.port = { postMessage: (value) => messages.push(value) };
      }
    },
    registerProcessor: (name, klass) => {
      assert.equal(name, "mercury-deck");
      Deck = klass;
    },
  };
vm.createContext(scope);
vm.runInContext(
  fs.readFileSync(root + "/signal-window/mercury-mix-worklet.js", "utf8"),
  scope,
);
const deck = new Deck(),
  send = (data) => deck.port.onmessage({ data }),
  run = () => {
    const output = [new Float32Array(128), new Float32Array(128)];
    deck.process([], [output]);
    return output;
  };
const pcm = Float32Array.from({ length: 48000 }, (_, i) => Math.sin(i * 0.05));
send({ type: "load", left: pcm, right: pcm, rate: 48000 });
assert.ok(run()[0].every((v) => v === 0));
send({ type: "play", value: true });
assert.ok(run()[0].some((v) => v !== 0));
assert.equal(deck.pos, 128);
send({ type: "rate", value: 2 });
run();
assert.equal(deck.pos, 384);
send({ type: "reverse", value: true });
run();
assert.equal(deck.pos, 128);
send({ type: "seek", seconds: 0.5 });
send({ type: "loop", value: true, start: 0.49, end: 0.51 });
for (let i = 0; i < 30; i++) run();
assert.ok(deck.pos >= 0.49 * 48000 && deck.pos < 0.51 * 48000);
send({ type: "loop", value: false });
send({ type: "reverse", value: false });
send({ type: "rate", value: 1 });
send({ type: "seek", seconds: 0.5 });
send({ type: "slip", value: true });
send({ type: "scratch", active: true });
send({ type: "move", seconds: -0.1 });
for (let i = 0; i < 10; i++) run();
assert.ok(deck.pos < 0.5 * 48000);
send({ type: "scratch", active: false });
assert.ok(
  deck.pos > 0.5 * 48000,
  "slip must catch up to the un-scratched timeline",
);
send({ type: "reverse", value: true });
send({ type: "load", left: pcm, right: pcm, rate: 48000 });
assert.equal(
  deck.direction,
  1,
  "new track must not inherit an old reverse state",
);
assert.equal(deck.slip, false);
assert.equal(deck.playing, false);
send({ type: "play", value: true });
send({ type: "seek", seconds: 0.9999 });
run();
assert.equal(deck.playing, false);
assert.ok(messages.length > 0);
console.log(
  "Mercury Mix DSP: fader, PCM, rate, reverse, loops, slip, track reset and end boundary passed",
);
// A loop edge must not make the scratch servo chase a wrapped target forever.
send({ type: "load", left: pcm, right: pcm, rate: 48000 });
send({ type: "seek", seconds: 0.509 });
send({ type: "loop", value: true, start: 0.49, end: 0.51 });
send({ type: "scratch", active: true });
send({ type: "move", seconds: 0.015 });
for (let i = 0; i < 400; i++) run();
assert.ok(
  Math.abs(deck.target - deck.travel) < 1,
  "scratch settles after crossing the loop boundary",
);
assert.ok(deck.pos >= 0.49 * 48000 && deck.pos < 0.51 * 48000);
send({ type: "scratch", active: false });
console.log("Loop-boundary scratching regression passed");
