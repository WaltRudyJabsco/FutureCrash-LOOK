const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert");
const source = fs.readFileSync("signal-window/mercury-mix.js", "utf8");
const start = source.indexOf("async function boundedFetch("),
  end = source.indexOf("async function durationOf(", start);
const scope = { MAX_FILE_BYTES: 48 * 1024 * 1024, Blob };
vm.createContext(scope);
vm.runInContext(source.slice(start, end), scope);
(async () => {
  for (const [status, pattern] of [
    [404, /source file or drive/],
    [401, /access was refused/],
    [403, /access was refused/],
    [425, /preparing this audio/],
    [502, /HTTP 502/],
  ]) {
    scope.fetch = async () => ({ ok: false, status });
    await assert.rejects(scope.boundedFetch("/music"), pattern);
  }
  scope.fetch = async () => {
    throw new TypeError("Load failed");
  };
  // Use errors from the same realm as a browser's own fetch.
  vm.runInContext('fetch=async()=>{throw new TypeError("Load failed")}', scope);
  await assert.rejects(
    scope.boundedFetch("/music"),
    /could not reach the music host/,
  );
  vm.runInContext(
    'fetch=async()=>({ok:true,headers:{get:()=>null},body:{getReader:()=>({read:async()=>{throw new TypeError("Load failed")},releaseLock(){}})}})',
    scope,
  );
  await assert.rejects(
    scope.boundedFetch("/music"),
    /transfer was interrupted/,
  );
  const payload = Buffer.from("actual music bytes");
  scope.fetch = async () => ({
    ok: true,
    headers: { get: () => null },
    body: {
      getReader() {
        let sent = false;
        return {
          async read() {
            if (sent) return { done: true };
            sent = true;
            return { done: false, value: payload };
          },
          releaseLock() {},
        };
      },
    },
  });
  const blob = await scope.boundedFetch("/music");
  assert.equal(await blob.text(), payload.toString());
  console.log(
    "Mixer loading: missing source, permissions, preparation, host errors, interrupted transfer and complete bytes passed",
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
