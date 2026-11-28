const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert");
const source = fs.readFileSync("signal-window/mercury-mix.js", "utf8");
const scope = {};
vm.createContext(scope);
vm.runInContext(
  source.slice(
    source.indexOf("class CrateAudition"),
    source.indexOf("const crateAudition ="),
  ) + "\nglobalThis.Audition = CrateAudition;",
  scope,
);
class Media {
  constructor() {
    this.paused = true;
    this.listeners = {};
    this.pending = [];
    this.loads = 0;
  }
  addEventListener(name, fn) {
    this.listeners[name] = fn;
  }
  pause() {
    this.paused = true;
    this.listeners.pause?.();
  }
  removeAttribute(name) {
    delete this[name];
  }
  load() {
    this.loads++;
  }
  play() {
    this.paused = false;
    return new Promise((resolve, reject) =>
      this.pending.push({ resolve, reject }),
    );
  }
}
(async () => {
  const media = new Media(),
    errors = [];
  let updates = 0;
  const preview = new scope.Audition(
    media,
    () => updates++,
    (message) => errors.push(message),
  );
  const a = { node: "one", id: "a", title: "A", audio_url: "/audio/a" },
    b = { node: "two", id: "b", title: "B", audio_url: "/audio/b" };
  const first = preview.toggle(a);
  assert.equal(media.src, "/audio/a");
  assert.ok(preview.active(a));
  const second = preview.toggle(b);
  assert.equal(media.src, "/audio/b");
  assert.ok(preview.active(b));
  assert.ok(!preview.active(a));
  media.pending[0].reject(Error("old play was aborted"));
  await first;
  assert.equal(
    errors.length,
    0,
    "switching tracks must not report a stale failure",
  );
  media.pending[1].resolve();
  await second;
  assert.ok(!preview.loading);
  await preview.toggle(b);
  assert.equal(media.src, undefined);
  assert.equal(preview.track, null);
  assert.ok(media.paused);
  const cancelled = preview.toggle(a);
  preview.stop();
  media.pending[2].resolve();
  await cancelled;
  assert.equal(
    preview.track,
    null,
    "late play resolution must not revive a closed preview",
  );
  const bad = preview.toggle(a);
  media.pending[3].reject(Error("permission refused"));
  await bad;
  assert.match(errors.pop(), /permission refused/);
  assert.equal(preview.track, null);
  const ended = preview.toggle(a);
  media.pending[4].resolve();
  await ended;
  media.listeners.ended();
  assert.equal(preview.track, null);
  assert.equal(media.src, undefined);
  assert.equal(media.preload, "none");
  assert.ok(updates > 0);
  console.log(
    "Crate preview: one voice, switch/stop, stale promise protection, error reporting, ended cleanup and streaming passed",
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
