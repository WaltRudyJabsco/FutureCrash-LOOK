const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert"),
  path = require("path");
let Deck;
const packets = [];
const scope = {
  sampleRate: 48000,
  Math,
  Float32Array,
  AudioWorkletProcessor: class {
    constructor() {
      this.port = {
        postMessage: (data, transfer) => packets.push({ data, transfer }),
      };
    }
  },
  registerProcessor: (_, C) => (Deck = C),
};
vm.createContext(scope);
vm.runInContext(
  fs.readFileSync(
    path.resolve(__dirname, "../../signal-window/mercury-mix-worklet.js"),
    "utf8",
  ),
  scope,
);
const deck = new Deck(),
  send = (data) => deck.port.onmessage({ data }),
  render = () => {
    const out = [new Float32Array(128), new Float32Array(128)];
    deck.process([], [out]);
    return out;
  };
const pcm = Float32Array.from(
  { length: 48000 },
  (_, i) => Math.sin(i * 0.1) * 0.5,
);
send({ type: "load", left: pcm, right: pcm, rate: 48000 });
send({ type: "play", value: true });
send({ type: "loop", value: true, start: 0, end: 1 });
send({ type: "capture-start", token: 1 });
send({ type: "capture-stop", token: 1 });
let first = render();
for (let i = 0; i < 44; i++) render();
let packet = packets.find((p) => p.data.type === "capture-complete").data;
assert.equal(
  packet.frames,
  5760,
  "a quick tap captures exactly the minimum slice",
);
assert.equal(packet.rate, 48000);
assert.ok(packet.peak > 0.4);
assert.equal(packet.left[5], first[0][5]);
assert.equal(deck.capture, null);
send({ type: "capture-start", token: 2 });
for (let i = 0; i < 3010; i++) render();
packet = packets.find(
  (p) => p.data.type === "capture-complete" && p.data.token === 2,
).data;
assert.equal(packet.frames, 8 * 48000, "capture must stop at eight seconds");
assert.equal(deck.capture, null);
send({ type: "capture-start", token: 3 });
render();
send({ type: "capture-cancel" });
for (let i = 0; i < 50; i++) render();
assert.ok(
  !packets.some(
    (p) => p.data.token === 3 && p.data.type === "capture-complete",
  ),
);
send({ type: "play", value: false });
send({ type: "capture-start", token: 4 });
send({ type: "capture-stop", token: 4 });
for (let i = 0; i < 45; i++) render();
packet = packets.find(
  (p) => p.data.token === 4 && p.data.type === "capture-complete",
).data;
assert.equal(
  packet.peak,
  0,
  "silent captures are reported honestly for UI rejection",
);
assert.ok(
  packets
    .filter((p) => p.data.type === "capture-complete")
    .every((p) => p.transfer.length === 2),
  "transfer PCM ownership instead of copying on the audio thread",
);
console.log(
  "Sample capture: actual stereo PCM, quick tap, release, 8s bound, cancel, silence and buffer transfer passed",
);
