const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert"),
  path = require("path");
class Node {
  constructor(name) {
    this.name = name;
    this.edges = [];
    this.gain = {
      value: 1,
      setTargetAtTime(v) {
        this.value = v;
      },
    };
    this.threshold = { value: 0 };
    this.ratio = { value: 0 };
  }
  connect(node, output = 0, input = 0) {
    this.edges.push({ node, output, input });
    return node;
  }
  disconnect(node) {
    this.edges = this.edges.filter((e) => e.node !== node);
  }
}
let id = 0;
const ctx = {
  currentTime: 0,
  destination: new Node("speakers"),
  createGain: () => new Node("gain" + id++),
  createDynamicsCompressor: () => new Node("limiter"),
  createChannelMerger: () => new Node("split"),
  createMediaStreamDestination: () =>
    Object.assign(new Node("headphone stream"), {
      stream: { getTracks: () => [] },
    }),
};
class Player {
  pause() {
    this.paused = true;
  }
  async play() {
    this.paused = false;
  }
  async setSinkId(id) {
    this.sinkId = id;
  }
}
const scope = { Audio: Player, Math };
vm.createContext(scope);
vm.runInContext(
  fs.readFileSync(
    path.resolve(__dirname, "../../signal-window/mercury-mix-monitor.js"),
    "utf8",
  ),
  scope,
);
const master = new Node("master"),
  main = new Node("main"),
  recording = new Node("recording");
master.connect(main);
master.connect(recording);
main.connect(ctx.destination);
const monitor = new scope.MercuryMonitor(ctx, master, main);
function reaches(node, target, seen = new Set()) {
  if (node === target) return true;
  if (seen.has(node)) return false;
  seen.add(node);
  return node.edges.some((e) => reaches(e.node, target, seen));
}
monitor.cues = [false, true];
monitor.set(0, 0.5);
assert.equal(monitor.inputs[0].gain.value, 0);
assert.equal(monitor.inputs[1].gain.value, 1);
assert.equal(monitor.mix.gain.value, 0);
for (const mode of ["off", "preview", "split", "separate"]) {
  monitor.route(mode);
  assert.ok(reaches(master, recording));
  assert.ok(
    !reaches(monitor.inputs[1], recording),
    "cue must never enter master recording",
  );
  assert.equal(
    main.edges.some((e) => e.node === ctx.destination),
    ["off", "separate"].includes(mode),
  );
  assert.equal(
    monitor.level.edges.some((e) => e.node === ctx.destination),
    mode === "preview",
  );
  assert.equal(
    monitor.split.edges.some((e) => e.node === ctx.destination),
    mode === "split",
  );
}
monitor.cues = [true, true];
monitor.set(1, 0.7);
assert.ok(Math.abs(monitor.inputs[0].gain.value - 1 / Math.sqrt(2)) < 1e-10);
assert.equal(monitor.mix.gain.value, 1);
assert.ok(monitor.cue.gain.value < 1e-10);
monitor.route("split", true);
assert.equal(main.gain.value, 0);
(async () => {
  await monitor.separate({ deviceId: "headphones" });
  assert.equal(monitor.player.sinkId, "headphones");
  assert.equal(monitor.mode, "separate");
  assert.equal(monitor.player.paused, false);
  monitor.player.play = async () => {
    throw Error("disconnected");
  };
  await assert.rejects(() => monitor.separate({ deviceId: "missing" }));
  assert.equal(monitor.mode, "off");
  console.log(
    "Monitor routes, cue selection, blend, recording isolation and disconnected-output recovery passed",
  );
})();
