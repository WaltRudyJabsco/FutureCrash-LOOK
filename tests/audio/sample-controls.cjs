const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert");
const elements = new Map();
const scope = {
  document: {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, { value: ".7", textContent: "" });
      return elements.get(id);
    },
  },
  requestAnimationFrame() {},
};
vm.createContext(scope);
vm.runInContext(
  fs.readFileSync("signal-window/mercury-mix-sampler.js", "utf8"),
  scope,
);
const Sampler = scope.MercurySampler;
for (const [i, key] of [..."ertyuiop"].entries()) {
  assert.equal(Sampler.keyIndex(key), i);
  assert.equal(Sampler.keyIndex(key.toUpperCase()), i);
}
assert.equal(Sampler.keyIndex("r", true), -1);
assert.equal(Sampler.keyIndex("t", true), -1);
for (const key of "asdfghjkl;qwzxcvm,./")
  assert.equal(Sampler.keyIndex(key), -1);
assert.equal(
  JSON.stringify(Sampler.bounds(2, -1, 7)),
  JSON.stringify({ start: 0, end: 2 }),
);
assert.equal(
  JSON.stringify(Sampler.bounds(2, 1.5, 0.5)),
  JSON.stringify({ start: 1.5, end: 1.51 }),
);
const starts = [],
  order = [];
const ctx = {
  state: "running",
  createGain: () => ({ gain: {}, connect() {} }),
  createBufferSource: () => ({
    connect() {},
    start(...args) {
      starts.push(args);
      order.push("sound");
    },
    stop() {},
  }),
};
const sampler = Object.assign(Object.create(Sampler.prototype), {
  restored: true,
  slots: [{ buffer: { duration: 2 }, start: 0.3, end: 1.2 }],
  context: () => ctx,
  ensure() {
    throw Error("running instrument must not wait for audio setup");
  },
  output() {},
  paintSoon() {
    order.push("paint");
  },
});
const played = sampler.trigger(0);
assert.equal(
  starts.length,
  1,
  "key starts audio synchronously before returning",
);
assert.equal(starts[0][0], 0);
assert.equal(starts[0][1], 0.3);
assert.ok(Math.abs(starts[0][2] - 0.9) < 1e-9);
assert.deepEqual(order, ["sound", "paint"]);
sampler
  .trigger(1)
  .then(() => assert.match(elements.get("sample-status").textContent, /empty/));
played.then(() =>
  console.log(
    "Sample controls: eight keys, collision-free banks, bounded trim, synchronous sound before paint, empty-pad feedback passed",
  ),
);
