/* Mercury Mix: the Fabric supplies records; this device performs the mix. */
"use strict";
const D = MercuryDSP,
  $ = (id) => document.getElementById(id),
  MAX_FILE_BYTES = 48 * 1024 * 1024,
  MAX_TRACK_SECONDS = 480,
  SOURCE_RATE = 32000,
  MAX_RECORD_SECONDS = 1800;
const defaults = {
  hand: "left",
  curve: "smooth",
  release: "latch",
  hamster: false,
  theme: "night",
  keyboard: "moves",
};
let prefs = readPrefs(),
  selected = 0,
  crossfade = 0.5,
  library = [],
  libraryLimit = 80,
  masterVolume = 0.8,
  muted = false,
  held = new Set(),
  tHeld = false,
  recording = null,
  recordStarted = 0,
  libraryTotal = 0,
  libraryRequest = 0,
  libraryAbort = null,
  searchTimer = null,
  activeMove = null,
  moveSerial = 0;
const decks = [0, 1].map((index) => ({
  index,
  track: null,
  position: 0,
  duration: 0,
  bpm: 120,
  grid: 0,
  pitch: 0,
  bend: 1,
  playing: false,
  reverse: false,
  slip: false,
  dub: false,
  cues: [null, null, null, null],
  cue: 0,
  loop: null,
  peaks: null,
  nodes: null,
  serial: 0,
  abort: null,
  taps: [],
  grabbed: false,
}));
function readPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem("mercury.mix.prefs.v1") || "{}");
    return {
      hand: p.hand === "right" ? "right" : "left",
      curve: p.curve === "cut" ? "cut" : "smooth",
      release: ["cut", "return-a", "return-b"].includes(p.release)
        ? p.release
        : "latch",
      hamster: !!p.hamster,
      theme: p.theme === "paper" ? "paper" : "night",
      keyboard: p.keyboard === "fader" ? "fader" : "moves",
    };
  } catch {
    return { ...defaults };
  }
}
function persist() {
  try {
    localStorage.setItem("mercury.mix.prefs.v1", JSON.stringify(prefs));
  } catch {
    /* Private browsing can disable persistence; the instrument still works. */
  }
}
function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}
function safeText(value, fallback = "") {
  return typeof value === "string" ? value.slice(0, 500) : fallback;
}
function setValue(el, value) {
  if (el.textContent !== String(value)) el.textContent = String(value);
}
const audio = {
  ctx: null,
  ready: null,
  master: null,
  monitor: null,
  analyzer: null,
  stream: null,
  async ensure() {
    if (!this.ready)
      this.ready = this.init().catch(async (error) => {
        await this.ctx?.close().catch(() => {});
        this.ctx = null;
        decks.forEach((d) => (d.nodes = null));
        this.ready = null;
        throw error;
      });
    await this.ready;
    if (this.ctx.state !== "running") await this.ctx.resume();
    $("audio").classList.toggle("active", this.ctx.state === "running");
    $("audio").textContent =
      this.ctx.state === "running" ? "Audio enabled" : "Resume audio";
    if (this.ctx.state !== "running")
      throw new Error("Tap Enable audio to resume sound on this device.");
    return this.ctx;
  },
  async init() {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context || !window.isSecureContext)
      throw new Error(
        "Open Mercury Mix using your trusted Fabric HTTPS address, or localhost, to enable audio.",
      );
    const ctx = new Context({ latencyHint: "interactive" });
    this.ctx = ctx;
    if (!ctx.audioWorklet) {
      await ctx.close();
      throw new Error(
        "This browser does not support the audio engine. Try a current Safari, Chrome or Firefox.",
      );
    }
    await ctx.audioWorklet.addModule("/mix/assets/mercury-mix-worklet.js");
    this.master = ctx.createGain();
    this.master.gain.value = masterVolume;
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -3;
    limiter.knee.value = 3;
    limiter.ratio.value = 12;
    limiter.attack.value = 0.002;
    limiter.release.value = 0.12;
    this.monitor = ctx.createGain();
    this.monitor.gain.value = muted ? 0 : 1;
    this.analyzer = ctx.createAnalyser();
    this.analyzer.fftSize = 512;
    this.stream = ctx.createMediaStreamDestination();
    this.master.connect(limiter);
    limiter.connect(this.monitor);
    this.monitor.connect(ctx.destination);
    limiter.connect(this.analyzer);
    limiter.connect(this.stream);
    this.headphones = new MercuryMonitor(ctx, limiter, this.monitor);
    const impulse = D.reverbImpulse(ctx.sampleRate);
    this.impulse = ctx.createBuffer(2, impulse[0].length, ctx.sampleRate);
    impulse.forEach((channel, i) => this.impulse.copyToChannel(channel, i));
    for (const deck of decks) this.deck(deck);
    this.headphones.route($("cue-route").value, muted);
    updateHeadphones();
    ctx.onstatechange = () => {
      const running = ctx.state === "running";
      $("audio").classList.toggle("active", running);
      $("audio").textContent = running ? "Audio enabled" : "Resume audio";
    };
  },
  deck(deck) {
    const ctx = this.ctx,
      source = new AudioWorkletNode(ctx, "mercury-deck", {
        numberOfInputs: 0,
        numberOfOutputs: 1,
        outputChannelCount: [2],
      });
    const low = ctx.createBiquadFilter(),
      mid = ctx.createBiquadFilter(),
      high = ctx.createBiquadFilter(),
      lp = ctx.createBiquadFilter(),
      hp = ctx.createBiquadFilter();
    low.type = "lowshelf";
    low.frequency.value = 250;
    mid.type = "peaking";
    mid.frequency.value = 1000;
    mid.Q.value = 0.8;
    high.type = "highshelf";
    high.frequency.value = 4000;
    lp.type = "lowpass";
    lp.frequency.value = 20000;
    hp.type = "highpass";
    hp.frequency.value = 20;
    const delay = ctx.createDelay(2),
      feedback = ctx.createGain(),
      feedbackFilter = ctx.createBiquadFilter(),
      reverb = ctx.createConvolver(),
      reverbWet = ctx.createGain(),
      wet = ctx.createGain(),
      sum = ctx.createGain(),
      gain = ctx.createGain(),
      meter = ctx.createAnalyser();
    feedback.gain.value = 0.35;
    feedbackFilter.type = "lowpass";
    feedbackFilter.frequency.value = 2400;
    reverb.buffer = this.impulse;
    reverbWet.gain.value = 0;
    wet.gain.value = 0;
    delay.delayTime.value = 0.25;
    meter.fftSize = 256;
    source.connect(low);
    low.connect(mid);
    mid.connect(high);
    high.connect(lp);
    lp.connect(hp);
    hp.connect(sum);
    hp.connect(delay);
    delay.connect(feedback);
    feedback.connect(feedbackFilter);
    feedbackFilter.connect(delay);
    hp.connect(reverb);
    reverb.connect(reverbWet);
    reverbWet.connect(sum);
    delay.connect(wet);
    wet.connect(sum);
    sum.connect(gain);
    sum.connect(this.headphones.inputs[deck.index]);
    gain.connect(meter);
    meter.connect(this.master);
    deck.nodes = {
      source,
      low,
      mid,
      high,
      lp,
      hp,
      delay,
      feedback,
      reverb,
      reverbWet,
      wet,
      gain,
      meter,
      meterData: new Float32Array(256),
    };
    source.port.onmessage = ({ data }) => {
      if (data.type === "gesture-start" && activeMove?.token === data.token) {
        deck.performing = true;
        updateGain();
      }
      if (data.type === "gesture-end" && activeMove?.token === data.token) {
        activeMove = null;
        deck.performing = false;
        updateGain();
        renderMoves();
        $("move-status").textContent =
          "Phrase finished. Fader restored; ready for your next move.";
      }
      if (data.type === "position") {
        deck.position = data.seconds;
        if (data.ended) deck.playing = false;
      }
    };
    updateGain();
    applyFX(deck);
  },
  send(deck, type, value = {}) {
    deck.nodes?.source.port.postMessage({ type, ...value });
  },
  smooth(param, value) {
    if (param && this.ctx)
      param.setTargetAtTime(value, this.ctx.currentTime, 0.008);
  },
};
function selectDeck(index) {
  if (index !== selected) stopMove();
  selected = index;
  $("move-target").textContent =
    "Target: deck " +
    (index ? "B" : "A") +
    " · " +
    (decks[index].track?.title || "load a record");
  for (const deck of decks) {
    deck.ui.classList.toggle("selected", deck.index === selected);
    deck.ui
      .querySelector(".deck-select")
      .setAttribute("aria-pressed", String(deck.index === selected));
  }
  document
    .querySelectorAll("[data-select]")
    .forEach((b) =>
      b.classList.toggle("active", Number(b.dataset.select) === index),
    );
}
function updateGain() {
  const gains = D.fader(crossfade, prefs.curve, prefs.hamster);
  decks.forEach((deck, i) => {
    audio.smooth(
      deck.nodes?.gain.gain,
      (deck.performing ? 1 : gains[i]) *
        Number(deck.ui?.querySelector(".volume").value || 1),
    );
  });
  $("crossfader").value = crossfade;
  setValue($("gain-a"), Math.round(gains[0] * 100) + "%");
  setValue($("gain-b"), Math.round(gains[1] * 100) + "%");
}
function applyPrefs() {
  if (!held.size) {
    const resting = D.releasePosition(prefs.release, selected, prefs.hamster);
    if (resting !== null) crossfade = resting;
  }
  for (const key of ["hand", "curve", "release"]) $(key).value = prefs[key];
  $("keyboard-mode").value = prefs.keyboard;
  $("move-pads").classList.toggle("keys-off", prefs.keyboard !== "moves");
  $("hamster").checked = prefs.hamster;
  document.body.dataset.theme = prefs.theme;
  $("key-hint").textContent =
    prefs.keyboard === "moves"
      ? "SCRATCH MOVES · A–; / Q W"
      : prefs.hand === "left"
        ? "A · S · D · F"
        : "J · K · L · ;";
  $("theme").textContent =
    prefs.theme === "paper"
      ? "Switch to night finish"
      : "Switch to paper finish";
  updateGain();
}
function rate(deck) {
  return (1 + deck.pitch / 100) * deck.bend;
}
function applyRate(deck) {
  audio.send(deck, "rate", { value: rate(deck) });
  audio.smooth(
    deck.nodes?.delay.delayTime,
    Math.min(1.5, 30 / (deck.bpm * rate(deck))),
  );
  deck.ui.querySelector(".pitch").value = deck.pitch;
  setValue(
    deck.ui.querySelector(".pitch-value"),
    (deck.pitch >= 0 ? "+" : "") + deck.pitch.toFixed(1) + "%",
  );
}
function applyFX(deck) {
  if (!deck.nodes) return;
  const q = (s) => deck.ui.querySelector(s),
    nodes = deck.nodes;
  for (const band of ["low", "mid", "high"])
    audio.smooth(nodes[band].gain, Number(q(".eq-" + band).value));
  const f = Number(q(".filter").value);
  audio.smooth(nodes.lp.frequency, f < 0 ? 20000 * Math.pow(0.012, -f) : 20000);
  audio.smooth(nodes.hp.frequency, f > 0 ? 20 * Math.pow(450, f) : 20);
  audio.smooth(
    nodes.wet.gain,
    Math.max(Number(q(".echo").value), deck.dub ? 0.45 : 0),
  );
  audio.smooth(nodes.feedback.gain, deck.dub ? 0.68 : 0.35);
  audio.smooth(nodes.reverbWet.gain, deck.dub ? 0.28 : 0);
  applyRate(deck);
  updateGain();
}
async function play(deck) {
  if (!deck.track) {
    status("Load a record or choose Demo set first.");
    return;
  }
  await audio.ensure();
  selectDeck(deck.index);
  deck.playing = !deck.playing;
  audio.send(deck, "play", { value: deck.playing });
}
function seek(deck, seconds) {
  if (!deck.track) return;
  deck.position = D.clamp(seconds, 0, Math.max(0, deck.duration - 0.001));
  audio.send(deck, "seek", { seconds: deck.position });
}
function cue(deck) {
  selectDeck(deck.index);
  if (!deck.track) return;
  deck.playing = false;
  audio.send(deck, "play", { value: false });
  seek(deck, deck.cue);
}
function reverse(deck) {
  deck.reverse = !deck.reverse;
  if (deck.reverse && deck.position < 0.02) seek(deck, deck.duration - 0.02);
  audio.send(deck, "reverse", { value: deck.reverse });
  deck.ui
    .querySelector(".reverse")
    .setAttribute("aria-pressed", String(deck.reverse));
}
function slip(deck) {
  deck.slip = !deck.slip;
  audio.send(deck, "slip", { value: deck.slip });
  deck.ui
    .querySelector(".slip")
    .setAttribute("aria-pressed", String(deck.slip));
}
function bend(deck, value) {
  deck.bend = value;
  applyRate(deck);
}
function sync(deck) {
  const other = decks[1 - deck.index];
  if (!deck.track || !other.track) {
    status("Load both decks to match tempo.");
    return;
  }
  const percentage = ((other.bpm * rate(other)) / deck.bpm - 1) * 100;
  if (Math.abs(percentage) > 25) {
    status(
      "These tempos are outside the ±25% vinyl range. Check or tap the BPM first.",
      true,
    );
    return;
  }
  deck.pitch = percentage;
  applyRate(deck);
  const beat = 60 / deck.bpm,
    phase = D.wrap((other.position - other.grid) / (60 / other.bpm), 0, 1),
    nearest = Math.round((deck.position - deck.grid) / beat);
  seek(deck, deck.grid + (nearest + phase) * beat);
  status(
    "Deck " +
      (deck.index ? "B" : "A") +
      " matched to " +
      (other.bpm * rate(other)).toFixed(1) +
      " BPM. Vinyl speed changes pitch.",
  );
}
function loop(deck, beats) {
  if (!deck.track) return;
  const step = 60 / deck.bpm,
    start = Math.max(
      0,
      deck.grid + Math.floor((deck.position - deck.grid) / step) * step,
    ),
    end = Math.min(deck.duration, start + step * beats);
  if (end - start < 0.02) return;
  deck.loop = { start, end, beats };
  audio.send(deck, "loop", { value: true, start, end });
  deck.ui
    .querySelectorAll("[data-loop]")
    .forEach((b) =>
      b.classList.toggle("active", Number(b.dataset.loop) === beats),
    );
}
function exitLoop(deck) {
  deck.loop = null;
  audio.send(deck, "loop", { value: false });
  deck.ui
    .querySelectorAll("[data-loop]")
    .forEach((b) => b.classList.remove("active"));
}
function grab(deck, on) {
  if (on) stopMove();
  if (!deck.track) return;
  selectDeck(deck.index);
  deck.grabbed = on;
  deck.ui.querySelector(".platter").classList.toggle("grabbed", on);
  audio.send(deck, "scratch", { active: on });
}
function move(deck, seconds) {
  if (deck.track) audio.send(deck, "move", { seconds });
}
function tap(deck) {
  const now = performance.now();
  if (now - (deck.taps.at(-1) || 0) > 2000) deck.taps = [];
  deck.taps.push(now);
  deck.taps = deck.taps.slice(-7);
  if (deck.taps.length > 2) {
    deck.bpm = D.clamp(
      60000 / ((now - deck.taps[0]) / (deck.taps.length - 1)),
      40,
      240,
    );
    deck.ui.querySelector(".bpm").value = deck.bpm.toFixed(1);
    deck.ui.querySelector(".grid-status").textContent =
      "TAPPED TEMPO · SET BEAT 1";
    applyRate(deck);
  }
}
function hotcue(deck, index, clear = false) {
  if (!deck.track) return;
  if (clear) deck.cues[index] = null;
  else if (deck.cues[index] === null) deck.cues[index] = deck.position;
  else {
    seek(deck, deck.cues[index]);
    deck.playing = true;
    audio
      .ensure()
      .then(() => audio.send(deck, "play", { value: true }))
      .catch(fail);
  }
  renderCues(deck);
}
function renderCues(deck) {
  deck.ui.querySelectorAll("[data-cue]").forEach((b) => {
    const point = deck.cues[Number(b.dataset.cue)];
    b.classList.toggle("filled", point !== null);
    b.title =
      point === null
        ? "Set hot cue at current position"
        : "Jump to " + D.time(point) + " · Shift-click to clear";
  });
}
function fail(error) {
  status(error?.message || String(error), true);
}
function stopDeck(deck) {
  if (activeMove?.deck === deck) stopMove();
  deck.playing = false;
  deck.grabbed = false;
  deck.position = 0;
  deck.track = null;
  deck.peaks = null;
  deck.duration = 0;
  deck.cue = 0;
  deck.grid = 0;
  deck.pitch = 0;
  deck.cues = [null, null, null, null];
  deck.loop = null;
  audio.send(deck, "clear");
  deck.ui.querySelector(".platter").classList.remove("grabbed");
  renderCues(deck);
  exitLoop(deck);
}
function metadata(deck) {
  if (deck.index === selected)
    $("move-target").textContent =
      "Target: deck " +
      (selected ? "B" : "A") +
      " · " +
      (deck.track?.title || "load a record");
  const q = (s) => deck.ui.querySelector(s),
    track = deck.track;
  q(".track-title").textContent = track?.title || "Find your next record.";
  q(".track-artist").textContent =
    track?.artist || "Fabric library · local files · original demos";
  q(".source").textContent = track
    ? track.kind === "demo"
      ? "MERCURY ORIGINAL"
      : track.kind === "local"
        ? "ON THIS DEVICE"
        : "FABRIC / " + track.node
    : "EMPTY DECK";
  q(".bpm").value = deck.bpm.toFixed(1);
  q(".duration").textContent = track ? D.time(deck.duration) : "—";
  q(".grid-status").textContent = track
    ? track.kind === "demo"
      ? "ORIGINAL LOOP · SET GRID"
      : "ESTIMATED BPM · ADJUST / TAP"
    : "BEAT GRID · READY WHEN YOU ARE";
  const img = q(".record-cover");
  img.hidden = true;
  img.removeAttribute("src");
  if (track?.cover_url) {
    img.onload = () => {
      img.hidden = false;
    };
    img.onerror = () => {
      img.hidden = true;
    };
    img.src = track.cover_url;
  }
  q(".label-title").textContent =
    track?.kind === "demo" ? track.title.toUpperCase() : "MERCURY SESSIONS";
}
async function boundedFetch(url, signal) {
  const response = await fetch(url, { signal, credentials: "same-origin" });
  if (!response.ok)
    throw new Error(
      response.status === 425
        ? "The Fabric is preparing this audio. Try loading it again shortly."
        : "Could not load this track (HTTP " + response.status + ").",
    );
  if (Number(response.headers.get("content-length") || 0) > MAX_FILE_BYTES)
    throw new Error("Choose an audio file smaller than 48 MB.");
  const reader = response.body?.getReader();
  if (!reader) {
    const blob = await response.blob();
    if (blob.size > MAX_FILE_BYTES)
      throw new Error("Choose an audio file smaller than 48 MB.");
    return blob;
  }
  const chunks = [];
  let bytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_FILE_BYTES) {
        await reader.cancel();
        throw new Error("Choose an audio file smaller than 48 MB.");
      }
      chunks.push(value);
    }
    return new Blob(chunks, {
      type: response.headers.get("content-type") || "audio/mpeg",
    });
  } finally {
    reader.releaseLock();
  }
}
async function durationOf(blob) {
  const url = URL.createObjectURL(blob),
    element = new Audio();
  try {
    return await new Promise((resolve, reject) => {
      const timer = setTimeout(
        () =>
          reject(
            new Error("Could not read this audio format. Try MP3, M4A or WAV."),
          ),
        10000,
      );
      element.preload = "metadata";
      // MediaRecorder WebM has no duration header. Seeking a local Blob to its
      // end makes the browser discover that duration without decoding unbounded PCM.
      element.onloadedmetadata = () => {
        if (Number.isFinite(element.duration)) {
          clearTimeout(timer);
          resolve(element.duration);
        } else {
          element.ontimeupdate = element.ondurationchange = () => {
            if (Number.isFinite(element.duration)) {
              clearTimeout(timer);
              resolve(element.duration);
            }
          };
          element.currentTime = 1e10;
        }
      };
      element.onerror = () => {
        clearTimeout(timer);
        reject(
          new Error(
            "This browser cannot read the audio file. Try MP3, M4A or WAV.",
          ),
        );
      };
      element.src = url;
    });
  } finally {
    element.removeAttribute("src");
    element.load();
    URL.revokeObjectURL(url);
  }
}
function resample(buffer) {
  if (buffer.sampleRate === SOURCE_RATE) {
    if (buffer.length * 2 > 32e6)
      throw new Error("This track is too long to buffer on this device.");
    return {
      left: buffer.getChannelData(0).slice(),
      right: buffer
        .getChannelData(Math.min(1, buffer.numberOfChannels - 1))
        .slice(),
      rate: SOURCE_RATE,
      duration: buffer.duration,
    };
  }
  const length = Math.ceil(buffer.duration * SOURCE_RATE);
  if (length * 2 > 32e6)
    throw new Error(
      "This track is too long to buffer on this device. Choose a shorter recording.",
    );
  const left = new Float32Array(length),
    right = new Float32Array(length),
    a = buffer.getChannelData(0),
    b = buffer.getChannelData(Math.min(1, buffer.numberOfChannels - 1)),
    ratio = buffer.sampleRate / SOURCE_RATE;
  for (let i = 0; i < length; i++) {
    const exact = i * ratio,
      at = Math.min(a.length - 1, Math.floor(exact)),
      next = Math.min(a.length - 1, at + 1),
      fraction = exact - at;
    left[i] = a[at] + (a[next] - a[at]) * fraction;
    right[i] = b[at] + (b[next] - b[at]) * fraction;
  }
  return { left, right, rate: SOURCE_RATE, duration: buffer.duration };
}
async function load(deck, track, file = null) {
  const serial = ++deck.serial;
  deck.abort?.abort();
  const controller = new AbortController();
  deck.abort = controller;
  const timer = setTimeout(() => controller.abort(), 90000);
  deck.ui.classList.add("loading");
  status(
    "Loading " + track.title + " into deck " + (deck.index ? "B" : "A") + "…",
  );
  try {
    await audio.ensure();
    if (serial !== deck.serial) return;
    stopDeck(deck);
    let pcm;
    if (track.kind === "demo") pcm = D.demo(track.demo);
    else {
      if (file && file.size > MAX_FILE_BYTES)
        throw new Error("Choose an audio file smaller than 48 MB.");
      const blob =
        file || (await boundedFetch(track.audio_url, controller.signal));
      if (serial !== deck.serial) return;
      const duration = await durationOf(blob);
      if (serial !== deck.serial) return;
      if (!Number.isFinite(duration) || duration > MAX_TRACK_SECONDS)
        throw new Error(
          "For live mixing, choose a track under eight minutes. Long recordings remain available in the regular player.",
        );
      const Decoder =
        window.OfflineAudioContext || window.webkitOfflineAudioContext;
      const decoder = Decoder ? new Decoder(2, 1, SOURCE_RATE) : audio.ctx;
      const buffer = await decoder.decodeAudioData(await blob.arrayBuffer());
      if (serial !== deck.serial) return;
      pcm = resample(buffer);
    }
    if (serial !== deck.serial) return false;
    const estimate =
      track.kind === "demo"
        ? { bpm: pcm.bpm, offset: 0 }
        : D.analyze(pcm.left, pcm.rate);
    deck.track = track;
    deck.duration = pcm.duration;
    deck.bpm = estimate.bpm;
    deck.grid = estimate.offset;
    deck.pitch = 0;
    deck.reverse = false;
    deck.slip = false;
    deck.peaks = D.peaks(pcm.left, pcm.right);
    // Transfer ownership so the real-time deck is the only retained PCM copy.
    deck.nodes.source.port.postMessage(
      { type: "load", left: pcm.left, right: pcm.right, rate: pcm.rate },
      [pcm.left.buffer, pcm.right.buffer],
    );
    deck.ui.querySelector(".reverse").setAttribute("aria-pressed", "false");
    deck.ui.querySelector(".slip").setAttribute("aria-pressed", "false");
    metadata(deck);
    applyRate(deck);
    renderCues(deck);
    if (track.kind === "demo") loop(deck, 16);
    status(
      track.title +
        " is ready on deck " +
        (deck.index ? "B" : "A") +
        ". " +
        (track.kind === "demo"
          ? "Original demo loop."
          : "BPM is estimated; tap or edit it to refine the grid."),
    );
    return true;
  } catch (error) {
    if (serial === deck.serial) {
      metadata(deck);
      if (error.name === "AbortError")
        status("Loading stopped. Choose the track again to retry.", true);
      else fail(error);
    }
    return false;
  } finally {
    clearTimeout(timer);
    if (serial === deck.serial) deck.ui.classList.remove("loading");
  }
}
function localTrack(file) {
  return {
    kind: "local",
    title: file.name.replace(/\.[^.]+$/, ""),
    artist: "Local audio · not uploaded",
    localName: file.name,
  };
}
function libraryTrack(row) {
  return {
    ...row,
    kind: "fabric",
    audio_url:
      "/api/media/browser?" +
      new URLSearchParams({ node: row.node, id: row.id }),
    cover_url:
      "/api/media/cover?" + new URLSearchParams({ node: row.node, id: row.id }),
  };
}
async function demoSet() {
  await audio.ensure();
  await Promise.all(
    decks.map((deck, i) =>
      load(deck, {
        kind: "demo",
        demo: i,
        title: i ? "Glass Transit" : "Neon Relay",
        artist: "Mercury sessions · original demo",
      }),
    ),
  );
  status(
    "Demo set ready. Play both decks, sync, then roll the fader. These loops were made for Mercury Mix.",
  );
}
function draw(deck) {
  const color = getComputedStyle(deck.ui).getPropertyValue("--accent").trim(),
    muted = getComputedStyle(document.body).getPropertyValue("--line").trim();
  for (const [selector, overview] of [
    [".overview", true],
    [".waveform", false],
  ]) {
    const canvas = deck.ui.querySelector(selector),
      rect = canvas.getBoundingClientRect(),
      scale = Math.min(devicePixelRatio || 1, 2),
      w = Math.round(rect.width * scale),
      h = Math.round(rect.height * scale);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    if (!w || !h) continue;
    const c = canvas.getContext("2d");
    c.clearRect(0, 0, w, h);
    c.strokeStyle = muted;
    c.beginPath();
    c.moveTo(0, h / 2);
    c.lineTo(w, h / 2);
    c.stroke();
    if (!deck.peaks) continue;
    const span = overview
        ? deck.duration
        : Math.min(deck.duration, (8 * 60) / deck.bpm),
      start = overview ? 0 : deck.position - span / 2;
    const step = 60 / deck.bpm;
    if (!overview) {
      for (
        let beat = Math.ceil((start - deck.grid) / step);
        beat * step + deck.grid < start + span;
        beat++
      ) {
        const x = ((beat * step + deck.grid - start) / span) * w;
        c.fillStyle = beat % 4 === 0 ? color : muted;
        c.globalAlpha = beat % 4 === 0 ? 0.35 : 0.3;
        c.fillRect(x, 0, scale, h);
      }
    }
    c.globalAlpha = overview ? 0.65 : 0.85;
    c.fillStyle = color;
    for (let x = 0; x < w; x += Math.max(1, scale * 2)) {
      const seconds = start + (x / w) * span;
      if (seconds < 0 || seconds >= deck.duration) continue;
      const peak =
        deck.peaks[
          Math.min(
            deck.peaks.length - 1,
            Math.floor((seconds / deck.duration) * deck.peaks.length),
          )
        ] || 0;
      c.fillRect(
        x,
        h / 2 - peak * h * 0.45,
        Math.max(1, scale),
        Math.max(1, peak * h * 0.9),
      );
    }
    c.globalAlpha = 1;
    if (deck.loop) {
      c.fillStyle = color;
      c.globalAlpha = 0.15;
      c.fillRect(
        ((deck.loop.start - start) / span) * w,
        0,
        ((deck.loop.end - deck.loop.start) / span) * w,
        h,
      );
      c.globalAlpha = 1;
    }
    c.fillStyle = getComputedStyle(document.body)
      .getPropertyValue("--ink")
      .trim();
    const x = overview ? (deck.position / deck.duration) * w : w / 2;
    c.fillRect(x, 0, 2 * scale, h);
    if (overview)
      for (const cue of deck.cues) {
        if (cue === null) continue;
        c.fillStyle = color;
        c.fillRect((cue / deck.duration) * w, 0, 2 * scale, h * 0.3);
      }
  }
}
let frame = 0,
  lastDraw = 0;
const masterData = new Float32Array(512);
function animate(now) {
  frame = requestAnimationFrame(animate);
  if (document.hidden || now - lastDraw < 40) return;
  lastDraw = now;
  for (const deck of decks) {
    setValue(deck.ui.querySelector(".position"), D.time(deck.position));
    setValue(deck.ui.querySelector(".play"), deck.playing ? "Pause" : "Play");
    deck.ui.querySelector(".play").classList.toggle("active", deck.playing);
    const platter = deck.ui.querySelector(".platter");
    platter.setAttribute(
      "aria-valuetext",
      deck.track
        ? D.time(deck.position) + " of " + D.time(deck.duration)
        : "No track loaded",
    );
    deck.ui.querySelector(".vinyl").style.transform =
      "rotate(" + (deck.position / 1.8) * 360 + "deg)";
    const overview = deck.ui.querySelector(".overview");
    overview.setAttribute(
      "aria-valuenow",
      String(
        Math.round(deck.duration ? (deck.position / deck.duration) * 100 : 0),
      ),
    );
    if (deck.nodes) {
      deck.nodes.meter.getFloatTimeDomainData(deck.nodes.meterData);
      let peak = 0;
      for (const v of deck.nodes.meterData) peak = Math.max(peak, Math.abs(v));
      deck.ui.querySelector(".channel-meter i").style.width =
        Math.min(100, peak * 100) + "%";
    }
    draw(deck);
  }
  if (audio.analyzer) {
    audio.analyzer.getFloatTimeDomainData(masterData);
    let sum = 0;
    for (const v of masterData) sum += v * v;
    const rms = Math.sqrt(sum / masterData.length),
      db = rms > 0.00001 ? Math.max(-90, 20 * Math.log10(rms)) : null;
    setValue($("master-db"), db === null ? "−∞" : db.toFixed(1));
    const canvas = $("master-meter"),
      c = canvas.getContext("2d"),
      w = canvas.width,
      h = canvas.height;
    c.clearRect(0, 0, w, h);
    for (let i = 0; i < 22; i++) {
      c.fillStyle = i < 16 ? "#69c8c0" : i < 20 ? "#d5ae70" : "#f58e7f";
      c.globalAlpha = db !== null && i < ((db + 60) / 60) * 22 ? 1 : 0.12;
      c.fillRect((i * w) / 22, 0, w / 22 - 3, h);
    }
    c.globalAlpha = 1;
  }
  if (recording) {
    const seconds = (performance.now() - recordStarted) / 1000;
    setValue($("record-time"), D.time(seconds));
    if (seconds > MAX_RECORD_SECONDS) stopRecord();
  }
}
function bindDeck(deck) {
  const ui = (deck.ui = $(deck.index ? "deck-b" : "deck-a"));
  ui.append($("deck-template").content.cloneNode(true));
  ui.querySelector(".deck-letter").textContent = deck.index ? "B" : "A";
  const q = (s) => ui.querySelector(s);
  q(".deck-select").onclick = () => selectDeck(deck.index);
  q(".load-deck").onclick = () => {
    selectDeck(deck.index);
    $("crate").scrollIntoView({ behavior: "smooth" });
    $("search").focus({ preventScroll: true });
  };
  q(".play").onclick = () => play(deck).catch(fail);
  q(".cue").onclick = () => cue(deck);
  q(".sync").onclick = () => sync(deck);
  q(".reverse").onclick = () => reverse(deck);
  q(".slip").onclick = () => slip(deck);
  q(".dub").onclick = () => {
    deck.dub = !deck.dub;
    q(".dub").setAttribute("aria-pressed", String(deck.dub));
    applyFX(deck);
    status(
      "Deck " +
        (deck.index ? "B" : "A") +
        (deck.dub ? ": dub echo and reverb on." : ": dub space off."),
    );
  };
  q(".pitch").oninput = (e) => {
    deck.pitch = Number(e.target.value);
    applyRate(deck);
  };
  q(".pitch-reset").onclick = () => {
    deck.pitch = 0;
    applyRate(deck);
  };
  q(".bpm").onchange = (e) => {
    deck.bpm = D.clamp(Number(e.target.value) || 120, 40, 240);
    e.target.value = deck.bpm.toFixed(1);
    applyRate(deck);
  };
  q(".tap").onclick = () => tap(deck);
  q(".beat-one").onclick = () => {
    deck.grid = deck.position;
    deck.cue = deck.position;
    q(".grid-status").textContent = "BEAT 1 SET AT " + D.time(deck.grid);
    status(
      "Beat grid and cue point set on deck " + (deck.index ? "B" : "A") + ".",
    );
  };
  ui.querySelectorAll("[data-cue]").forEach(
    (b) => (b.onclick = (e) => hotcue(deck, Number(b.dataset.cue), e.shiftKey)),
  );
  q(".clear-cues").onclick = () => {
    deck.cues = [null, null, null, null];
    renderCues(deck);
  };
  ui.querySelectorAll("[data-loop]").forEach(
    (b) => (b.onclick = () => loop(deck, Number(b.dataset.loop))),
  );
  q(".loop-off").onclick = () => exitLoop(deck);
  for (const selector of [
    ".eq-low",
    ".eq-mid",
    ".eq-high",
    ".filter",
    ".echo",
    ".volume",
  ])
    q(selector).oninput = () => applyFX(deck);
  q(".fx-reset").onclick = () => {
    deck.dub = false;
    q(".dub").setAttribute("aria-pressed", "false");
    for (const s of [".eq-low", ".eq-mid", ".eq-high", ".filter", ".echo"])
      q(s).value = 0;
    applyFX(deck);
  };
  const platter = q(".platter");
  let pointer = null,
    lastAngle = 0;
  platter.onpointerdown = (e) => {
    if (!deck.track || e.button > 0) return;
    audio.ensure().catch(fail);
    e.preventDefault();
    pointer = e.pointerId;
    platter.setPointerCapture(pointer);
    const r = platter.getBoundingClientRect();
    lastAngle = Math.atan2(
      e.clientY - r.top - r.height / 2,
      e.clientX - r.left - r.width / 2,
    );
    grab(deck, true);
  };
  platter.onpointermove = (e) => {
    if (pointer !== e.pointerId) return;
    const r = platter.getBoundingClientRect(),
      angle = Math.atan2(
        e.clientY - r.top - r.height / 2,
        e.clientX - r.left - r.width / 2,
      );
    let delta = angle - lastAngle;
    if (delta > Math.PI) delta -= 2 * Math.PI;
    if (delta < -Math.PI) delta += 2 * Math.PI;
    move(deck, (delta / (2 * Math.PI)) * 1.8);
    lastAngle = angle;
  };
  const release = () => {
    pointer = null;
    grab(deck, false);
  };
  platter.onpointerup = release;
  platter.onpointercancel = release;
  platter.onlostpointercapture = () => {
    if (pointer !== null) release();
  };
  let wheelTimer;
  platter.addEventListener(
    "wheel",
    (e) => {
      if (!deck.track) return;
      e.preventDefault();
      selectDeck(deck.index);
      if (tHeld) {
        grab(deck, true);
        move(deck, -e.deltaY * 0.0025);
      } else {
        bend(deck, e.deltaY > 0 ? 0.96 : 1.04);
        clearTimeout(wheelTimer);
        wheelTimer = setTimeout(() => bend(deck, 1), 160);
      }
    },
    { passive: false },
  );
  const overview = q(".overview");
  let seeking = false;
  const seekPointer = (e) => {
    const r = overview.getBoundingClientRect();
    seek(deck, ((e.clientX - r.left) / r.width) * deck.duration);
  };
  overview.onpointerdown = (e) => {
    if (!deck.track) return;
    e.preventDefault();
    selectDeck(deck.index);
    seeking = true;
    overview.setPointerCapture(e.pointerId);
    seekPointer(e);
  };
  overview.onpointermove = (e) => {
    if (seeking) seekPointer(e);
  };
  overview.onpointerup = () => {
    seeking = false;
  };
  overview.onpointercancel = () => {
    seeking = false;
  };
  overview.onkeydown = (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      e.stopPropagation();
      seek(
        deck,
        deck.position + ((e.key === "ArrowRight" ? 1 : -1) * 60) / deck.bpm,
      );
    }
  };
  platter.onkeydown = (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      e.stopPropagation();
      seek(deck, deck.position + (e.key === "ArrowRight" ? 0.1 : -0.1));
    }
  };
  for (const type of ["dragenter", "dragover"])
    ui.addEventListener(type, (e) => {
      if (e.dataTransfer?.types.includes("Files")) {
        e.preventDefault();
        ui.classList.add("drag-over");
      }
    });
  ui.addEventListener("dragleave", (e) => {
    if (!ui.contains(e.relatedTarget)) ui.classList.remove("drag-over");
  });
  ui.addEventListener("drop", (e) => {
    e.preventDefault();
    ui.classList.remove("drag-over");
    const file = e.dataTransfer?.files[0];
    if (file) {
      selectDeck(deck.index);
      load(deck, localTrack(file), file);
    }
  });
}
function renderLibrary() {
  const query = $("search").value.trim().toLowerCase(),
    matches = library.filter((row) =>
      [row.title, row.artist, row.album, row.node]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  const fragment = document.createDocumentFragment();
  matches.slice(0, libraryLimit).forEach((track, index) => {
    const row = document.createElement("div");
    row.className = "track-row";
    const number = document.createElement("span");
    number.className = "track-index";
    number.textContent = String(index + 1).padStart(2, "0");
    const main = document.createElement("div");
    main.className = "track-main";
    const title = document.createElement("strong");
    title.textContent = track.title;
    const artist = document.createElement("small");
    artist.textContent = [
      track.artist || "Unknown artist",
      track.node || "This device",
      track.format || "AUDIO",
    ].join(" · ");
    main.append(title, artist);
    const album = document.createElement("span");
    album.className = "track-album";
    album.textContent = track.album || "—";
    const duration = document.createElement("span");
    duration.className = "track-duration";
    duration.textContent = D.time(Number(track.duration) || NaN);
    const buttons = document.createElement("div");
    buttons.className = "track-load";
    for (const i of [0, 1]) {
      const button = document.createElement("button");
      button.textContent = "Load " + (i ? "B" : "A");
      button.setAttribute(
        "aria-label",
        "Load " + track.title + " on deck " + (i ? "B" : "A"),
      );
      button.onclick = () => {
        selectDeck(i);
        load(decks[i], libraryTrack(track));
      };
      buttons.append(button);
    }
    row.append(number, main, album, duration, buttons);
    fragment.append(row);
  });
  $("tracks").replaceChildren(fragment);
  $("more").hidden =
    matches.length <= libraryLimit && library.length >= libraryTotal;
  $("library-count").textContent = libraryTotal + " tracks";
  if (!matches.length)
    $("library-status").textContent = library.length
      ? "No matches. Try another artist or title."
      : "No Fabric music found. Add audio files or load the demo set.";
  else if (!$("library-status").dataset.error)
    $("library-status").textContent =
      "Load either deck. Your library files stay where they are.";
}
async function refreshLibrary(append = false) {
  const serial = ++libraryRequest;
  libraryAbort?.abort();
  const controller = new AbortController();
  libraryAbort = controller;
  const timer = setTimeout(() => controller.abort(), 15000),
    query = $("search").value.trim().slice(0, 200),
    offset = append ? library.length : 0;
  $("refresh").disabled = true;
  $("library-status").textContent = "Reading your Fabric music catalog…";
  try {
    const response = await fetch(
      "/api/mix/library?" + new URLSearchParams({ q: query, offset }),
      { signal: controller.signal },
    );
    if (!response.ok)
      throw new Error("Library unavailable (HTTP " + response.status + ").");
    const value = await response.json();
    if (serial !== libraryRequest) return;
    libraryTotal = Number(value.total) || 0;
    const rows = Array.isArray(value.entries) ? value.entries : [];
    library = append ? library.concat(rows) : rows;
    delete $("library-status").dataset.error;
    renderLibrary();
    if (value.errors?.length || value.refreshing)
      $("library-status").textContent =
        "Showing available music. Some nodes may be asleep or refreshing; use Refresh library to check again.";
  } catch (error) {
    if (serial !== libraryRequest) return;
    $("library-status").dataset.error = "true";
    $("library-status").textContent =
      (error.name === "AbortError"
        ? "The Fabric did not respond in time."
        : error.message) + " Local files and Demo set still work.";
  } finally {
    clearTimeout(timer);
    if (serial === libraryRequest) $("refresh").disabled = false;
  }
}
function download(blob, name) {
  const url = URL.createObjectURL(blob),
    link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
async function toggleRecord() {
  if (recording) {
    stopRecord();
    return;
  }
  await audio.ensure();
  if (!window.MediaRecorder)
    throw new Error("Recording is not supported by this browser.");
  const type = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"].find((t) =>
    MediaRecorder.isTypeSupported(t),
  );
  const chunks = [],
    rec = new MediaRecorder(
      audio.stream.stream,
      type ? { mimeType: type } : undefined,
    );
  recording = rec;
  recordStarted = performance.now();
  rec.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data);
  };
  rec.onstop = () => {
    const extension = rec.mimeType.includes("mp4")
      ? "m4a"
      : rec.mimeType.includes("ogg")
        ? "ogg"
        : "webm";
    if (chunks.length)
      download(
        new Blob(chunks, { type: rec.mimeType }),
        "Mercury Mix " +
          new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-") +
          "." +
          extension,
      );
    status(
      chunks.length
        ? "Your mix recording was exported to this device."
        : "No audio data was captured. Try recording again.",
      !chunks.length,
    );
  };
  rec.onerror = (e) => {
    fail(e.error || "Recording failed.");
    stopRecord();
  };
  rec.start(1000);
  $("record").classList.add("recording");
  $("record").lastChild.textContent = "Stop & export";
  $("record-time").hidden = false;
  status("Recording the master mix. Stop & export saves it to this device.");
}
function stopRecord() {
  if (!recording) return;
  const rec = recording;
  recording = null;
  if (rec.state !== "inactive") rec.stop();
  $("record").classList.remove("recording");
  $("record").lastChild.textContent = "Record mix";
  $("record-time").hidden = true;
}
function saveSet() {
  const value = {
    format: "mercury-mix-set",
    version: 1,
    prefs,
    crossfade,
    master: masterVolume,
    decks: decks.map((deck) => ({
      track: deck.track
        ? {
            kind: deck.track.kind,
            id: deck.track.id,
            node: deck.track.node,
            title: deck.track.title,
            artist: deck.track.artist,
            localName: deck.track.localName,
            demo: deck.track.demo,
          }
        : null,
      bpm: deck.bpm,
      grid: deck.grid,
      pitch: deck.pitch,
      cues: deck.cues,
      cue: deck.cue,
      position: deck.position,
      reverse: deck.reverse,
      slip: deck.slip,
      dub: deck.dub,
      loop: deck.loop,
      controls: Object.fromEntries(
        ["eq-low", "eq-mid", "eq-high", "filter", "echo", "volume"].map((k) => [
          k,
          Number(deck.ui.querySelector("." + k).value),
        ]),
      ),
    })),
  };
  download(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    "Mercury Mix set.json",
  );
  status("Set saved. Audio files are referenced, not copied into the set.");
}
async function openSet(file) {
  if (file.size > 64000) throw new Error("This set file is too large.");
  const value = JSON.parse(await file.text());
  if (
    value.format !== "mercury-mix-set" ||
    value.version !== 1 ||
    !Array.isArray(value.decks) ||
    value.decks.length !== 2
  )
    throw new Error("Choose a Mercury Mix set file.");
  await audio.ensure();
  if (value.prefs && typeof value.prefs === "object") {
    const p = value.prefs;
    prefs = {
      hand: p.hand === "right" ? "right" : "left",
      curve: p.curve === "cut" ? "cut" : "smooth",
      release: ["cut", "return-a", "return-b"].includes(p.release)
        ? p.release
        : "latch",
      hamster: !!p.hamster,
      theme: p.theme === "paper" ? "paper" : "night",
      keyboard: p.keyboard === "fader" ? "fader" : "moves",
    };
    persist();
    applyPrefs();
  }
  let localMissing = false;
  for (let i = 0; i < 2; i++) {
    const saved = value.decks[i] || {},
      track = saved.track;
    const deck = decks[i];
    let loaded = false;
    if (track?.kind === "demo" && [0, 1].includes(track.demo))
      loaded = await load(deck, {
        kind: "demo",
        demo: track.demo,
        title: track.demo ? "Glass Transit" : "Neon Relay",
        artist: "Mercury sessions · original demo",
      });
    else if (
      track?.kind === "fabric" &&
      typeof track.id === "string" &&
      typeof track.node === "string" &&
      track.id.length < 300 &&
      track.node.length < 200
    )
      loaded = await load(
        deck,
        libraryTrack({
          id: track.id,
          node: track.node,
          title: safeText(track.title, "Saved record"),
          artist: safeText(track.artist),
        }),
      );
    else {
      stopDeck(deck);
      deck.track = null;
      deck.duration = 0;
      metadata(deck);
      localMissing = localMissing || track?.kind === "local";
      continue;
    }
    if (!loaded)
      throw new Error(
        "Could not restore this set’s audio. Check the library connection and try again.",
      );
    deck.bpm = D.clamp(Number(saved.bpm) || 120, 40, 240);
    deck.grid = D.clamp(Number(saved.grid) || 0, 0, deck.duration);
    deck.cue = D.clamp(Number(saved.cue) || 0, 0, deck.duration);
    deck.pitch = D.clamp(Number(saved.pitch) || 0, -25, 25);
    deck.cues = [0, 1, 2, 3].map((n) =>
      saved.cues?.[n] !== null && Number.isFinite(saved.cues?.[n])
        ? D.clamp(saved.cues[n], 0, deck.duration)
        : null,
    );
    for (const [key, bounds] of Object.entries({
      "eq-low": [-12, 12],
      "eq-mid": [-12, 12],
      "eq-high": [-12, 12],
      filter: [-1, 1],
      echo: [0, 0.7],
      volume: [0, 1.25],
    }))
      if (Number.isFinite(saved.controls?.[key]))
        deck.ui.querySelector("." + key).value = D.clamp(
          saved.controls[key],
          ...bounds,
        );
    deck.ui.querySelector(".bpm").value = deck.bpm.toFixed(1);
    deck.dub = !!saved.dub;
    deck.ui
      .querySelector(".dub")
      .setAttribute("aria-pressed", String(deck.dub));
    applyFX(deck);
    seek(deck, Number(saved.position) || 0);
    if (saved.reverse) reverse(deck);
    if (saved.slip) slip(deck);
    if (
      saved.loop &&
      Number.isFinite(saved.loop.start) &&
      Number.isFinite(saved.loop.end)
    ) {
      const start = D.clamp(saved.loop.start, 0, deck.duration),
        end = D.clamp(saved.loop.end, 0, deck.duration);
      if (end > start + 0.02) {
        deck.loop = { start, end, beats: Number(saved.loop.beats) || 4 };
        audio.send(deck, "loop", { value: true, start, end });
        deck.ui
          .querySelectorAll("[data-loop]")
          .forEach((b) =>
            b.classList.toggle(
              "active",
              Number(b.dataset.loop) === deck.loop.beats,
            ),
          );
      }
    }
    renderCues(deck);
  }
  crossfade = D.clamp(Number(value.crossfade) || 0, 0, 1);
  masterVolume = Number.isFinite(value.master)
    ? D.clamp(value.master, 0, 1)
    : 0.8;
  $("master").value = masterVolume;
  audio.smooth(audio.master.gain, masterVolume);
  updateGain();
  status(
    localMissing
      ? "Set opened. Select the local audio files again to restore those decks."
      : "Set opened. Decks are paused and ready.",
  );
}
function renderMoves() {
  document.querySelectorAll("[data-move]").forEach((button) => {
    const live = activeMove?.id === button.dataset.move;
    button.classList.toggle("active", live);
    button.setAttribute("aria-pressed", String(live));
  });
}
function stopMove() {
  if (!activeMove) return;
  const deck = activeMove.deck;
  audio.send(deck, "gesture-stop");
  activeMove = null;
  deck.performing = false;
  updateGain();
  renderMoves();
}
async function startMove(move, key) {
  const deck = decks[selected];
  if (!deck.track) {
    status("Load a track on the selected deck, then mark a sound to scratch.");
    return;
  }
  if (deck.duration - deck.cue < 0.01) {
    status("Mark a sound before the end of the track.", true);
    return;
  }
  stopMove();
  const current = {
    id: move.id,
    key,
    token: ++moveSerial,
    deck,
    released: false,
  };
  activeMove = current;
  renderMoves();
  try {
    await audio.ensure();
    if (activeMove !== current) return;
    const other = decks[1 - deck.index];
    const tempo = other.playing
      ? other.bpm * rate(other)
      : deck.bpm * rate(deck);
    const seconds =
      move.id === "audition"
        ? Number($("move-span").value) / rate(deck)
        : ((move.beats || 1) * 60) / tempo;
    audio.send(deck, "gesture", {
      token: current.token,
      points: move.points,
      cue: deck.cue,
      span: Number($("move-span").value),
      seconds: D.clamp(seconds, 0.1, 8),
    });
    if (current.released)
      audio.send(deck, "gesture-release", { token: current.token });
    $("move-status").textContent =
      (deck.index ? "B" : "A") +
      " · " +
      move.name +
      " · cue " +
      D.time(deck.cue) +
      " · " +
      Math.round(tempo) +
      " BPM. " +
      (current.released ? "One phrase." : "Hold to repeat; release to finish.");
  } catch (error) {
    if (activeMove === current) stopMove();
    fail(error);
  }
}
function releaseMove(key) {
  if (activeMove?.key !== key) return;
  activeMove.released = true;
  audio.send(activeMove.deck, "gesture-release", { token: activeMove.token });
}
for (const move of MercuryMoves.moves) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.move = move.id;
  const key = document.createElement("kbd"),
    name = document.createElement("strong"),
    hint = document.createElement("small");
  key.textContent = move.key.toUpperCase();
  name.textContent = move.name;
  hint.textContent = move.hint;
  button.append(key, name, hint);
  button.setAttribute("aria-pressed", "false");
  button.onpointerdown = (event) => {
    if (event.button !== 0) return;
    button.setPointerCapture(event.pointerId);
    startMove(move, move.key);
  };
  button.onpointerup = () => releaseMove(move.key);
  button.onpointercancel = stopMove;
  button.onlostpointercapture = () => releaseMove(move.key);
  button.onkeydown = (event) => {
    if (["Enter", " "].includes(event.key)) {
      event.preventDefault();
      event.stopPropagation();
      if (!event.repeat) startMove(move, move.key);
    }
  };
  button.onkeyup = (event) => {
    if (["Enter", " "].includes(event.key)) {
      event.preventDefault();
      event.stopPropagation();
      releaseMove(move.key);
    }
  };
  button.onclick = (event) => {
    if (event.detail === 0) {
      startMove(move, move.key);
      releaseMove(move.key);
    }
  };
  $("move-pads").append(button);
}
$("keyboard-mode").onchange = (event) => {
  clearGestures();
  prefs.keyboard = event.target.value;
  persist();
  applyPrefs();
};
$("moves-shortcut").onclick = () => {
  document.querySelector(".moves-panel").scrollIntoView({ behavior: "smooth" });
  $("moves-shortcut").focus({ preventScroll: true });
};
$("mark-sound").onclick = () => {
  stopMove();
  const deck = decks[selected];
  if (!deck.track) {
    status("Load a track on the selected deck first.");
    return;
  }
  deck.cue = deck.position;
  $("move-status").textContent =
    "Deck " +
    (deck.index ? "B" : "A") +
    " sound marked at " +
    D.time(deck.cue) +
    ". Tap a move to play it.";
};
$("audition-sound").onclick = () => {
  const move = {
    id: "audition",
    name: "Marked sound",
    points: [
      [0, 0, 1],
      [1, 1, 0],
    ],
    beats: 1,
  };
  startMove(move, "audition");
  releaseMove("audition");
};
$("stop-moves").onclick = () => {
  stopMove();
  $("move-status").textContent = "Moves stopped. Main mix restored.";
};
function faderKeys() {
  const value = D.keyPosition(held, prefs.hand);
  if (value !== null) {
    crossfade = value;
    updateGain();
  } else {
    const resting = D.releasePosition(prefs.release, selected, prefs.hamster);
    if (resting !== null) {
      crossfade = resting;
      updateGain();
    }
  }
}
function clearGestures() {
  stopMove();
  held.clear();
  tHeld = false;
  for (const deck of decks) {
    if (deck.grabbed) grab(deck, false);
    bend(deck, 1);
  }
  if (prefs.release !== "latch") faderKeys();
}
function typing(target) {
  return (
    target instanceof Element &&
    !!target.closest("input,textarea,select,[contenteditable=true],dialog")
  );
}
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target)) return;
  const key = e.key.toLowerCase(),
    bank = prefs.hand === "left" ? ["a", "s", "d", "f"] : ["j", "k", "l", ";"];
  if (key === "escape") {
    stopMove();
    return;
  }
  const move = prefs.keyboard === "moves" && MercuryMoves.byKey(key);
  if (move) {
    e.preventDefault();
    if (!e.repeat) startMove(move, key);
    return;
  }
  if (prefs.keyboard === "fader" && bank.includes(key)) {
    e.preventDefault();
    held.add(key);
    faderKeys();
    return;
  }
  if (e.repeat) return;
  const deck = decks[selected];
  if (key === "1" || key === "2") {
    e.preventDefault();
    selectDeck(Number(key) - 1);
  } else if (key === " " && !e.target.closest("button")) {
    e.preventDefault();
    play(deck).catch(fail);
  } else if (key === "c") {
    e.preventDefault();
    cue(deck);
  } else if (key === "r") reverse(deck);
  else if (key === "v") slip(deck);
  else if (key === "z" || key === "x") {
    e.preventDefault();
    bend(deck, key === "z" ? 0.96 : 1.04);
  } else if (key === "t") {
    e.preventDefault();
    tHeld = true;
    grab(deck, true);
  }
});
document.addEventListener("keyup", (e) => {
  const key = e.key.toLowerCase();
  releaseMove(key);
  if (held.delete(key)) faderKeys();
  if (key === "t") {
    tHeld = false;
    decks.forEach((d) => {
      if (d.grabbed) grab(d, false);
    });
  }
  if (key === "z" || key === "x") decks.forEach((d) => bend(d, 1));
});
window.addEventListener("blur", clearGestures);
document.querySelectorAll(".file-button").forEach((label) =>
  label.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      event.stopPropagation();
      label.querySelector("input").click();
    }
  }),
);
for (const deck of decks) bindDeck(deck);
selectDeck(0);
applyPrefs();
$("audio").onclick = () =>
  audio
    .ensure()
    .then(() => status("Audio is ready on this device."))
    .catch(fail);
$("demo").onclick = () => demoSet().catch(fail);
$("controls").onclick = () => {
  $("help").showModal();
  clearGestures();
};
$("fullscreen").onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {
    status("Full screen is not available in this browser.", true);
  }
};
function updateHeadphones() {
  if (!audio.headphones) return;
  audio.headphones.cues = [
    $("listen-a").getAttribute("aria-pressed") === "true",
    $("listen-b").getAttribute("aria-pressed") === "true",
  ];
  audio.headphones.set(
    Number($("cue-blend").value),
    Number($("cue-level").value),
  );
}
for (const id of ["listen-a", "listen-b"])
  $(id).onclick = async () => {
    try {
      await audio.ensure();
      $(id).setAttribute(
        "aria-pressed",
        String($(id).getAttribute("aria-pressed") !== "true"),
      );
      updateHeadphones();
    } catch (error) {
      fail(error);
    }
  };
$("cue-blend").oninput = $("cue-level").oninput = updateHeadphones;
$("cue-route").onchange = async () => {
  try {
    await audio.ensure();
    const mode = $("cue-route").value;
    audio.headphones.route(mode, muted);
    if (mode === "separate") await audio.headphones.player.play();
    $("cue-status").textContent =
      mode === "preview"
        ? "Preview replaces what you hear here. The stereo main recording is unchanged."
        : mode === "split"
          ? "Split-cable mode: mono main on LEFT, mono cue on RIGHT. Use a DJ splitter to separate them."
          : mode === "separate"
            ? "Cue uses your chosen output; main stays on the system output. Choose different physical devices for private monitoring."
            : "Main output only. Cue monitoring is off.";
  } catch (error) {
    audio.headphones?.route("off", muted);
    $("cue-route").value = "off";
    fail(error);
  }
};
$("choose-headphones").onclick = async () => {
  try {
    // Open directly from the click so the browser retains transient activation.
    const device = await navigator.mediaDevices.selectAudioOutput();
    await audio.ensure();
    await audio.headphones.separate(device, muted);
    $("cue-route").querySelector('[value="separate"]').disabled = false;
    $("cue-route").value = "separate";
    $("cue-status").textContent =
      "Cue output: " +
      (device.label || "Selected device") +
      ". Main stays on the system output; choose a different physical device for private cueing.";
  } catch (error) {
    $("cue-status").textContent =
      "Output selection was not completed. Use Preview here or a split cable, or try a browser with output selection.";
  }
};
if (
  !navigator.mediaDevices?.selectAudioOutput ||
  !("setSinkId" in HTMLMediaElement.prototype)
) {
  $("choose-headphones").disabled = true;
  $("choose-headphones").textContent = "Separate output unavailable here";
}
$("sync-all").onclick = () => sync(decks[1]);
$("swap").onclick = () => {
  $("console").classList.toggle("swapped");
};
document
  .querySelectorAll("[data-select]")
  .forEach((b) => (b.onclick = () => selectDeck(Number(b.dataset.select))));
for (const key of ["hand", "curve", "release"])
  $(key).onchange = (e) => {
    clearGestures();
    prefs[key] = e.target.value;
    persist();
    applyPrefs();
  };
$("hamster").onchange = (e) => {
  prefs.hamster = e.target.checked;
  persist();
  applyPrefs();
};
$("theme").onclick = () => {
  prefs.theme = prefs.theme === "paper" ? "night" : "paper";
  persist();
  applyPrefs();
};
$("crossfader").oninput = (e) => {
  crossfade = Number(e.target.value);
  updateGain();
};
$("master").oninput = (e) => {
  masterVolume = Number(e.target.value);
  audio.smooth(audio.master?.gain, masterVolume);
};
$("mute").onclick = () => {
  muted = !muted;
  if (audio.headphones) audio.headphones.route(audio.headphones.mode, muted);
  if (audio.headphones?.mode === "separate")
    audio.headphones.player.play().catch(fail);
  $("mute").textContent = muted ? "Unmute output" : "Mute output";
  $("mute").setAttribute("aria-pressed", String(muted));
};
$("files").onchange = (e) => {
  const files = [...e.target.files];
  files
    .slice(0, 2)
    .forEach((file, i) =>
      load(decks[(selected + i) % 2], localTrack(file), file),
    );
  e.target.value = "";
};
$("refresh").onclick = () => refreshLibrary();
$("search").maxLength = 200;
$("search").oninput = () => {
  libraryLimit = 80;
  renderLibrary();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => refreshLibrary(), 350);
};
$("more").onclick = () => {
  libraryLimit += 80;
  if (libraryLimit > library.length && library.length < libraryTotal)
    refreshLibrary(true);
  else renderLibrary();
};
$("save").onclick = saveSet;
$("open-set").onchange = (e) => {
  const file = e.target.files[0];
  if (file) openSet(file).catch(fail);
  e.target.value = "";
};
$("record").onclick = () => toggleRecord().catch(fail);
window.addEventListener("pagehide", (event) => {
  if (event.persisted) {
    clearGestures();
    return;
  }
  cancelAnimationFrame(frame);
  decks.forEach((d) => d.abort?.abort());
  if (recording && recording.state !== "inactive") recording.stop();
  stopMove();
  audio.headphones?.close();
  audio.ctx?.close();
});
refreshLibrary();
requestAnimationFrame(animate);
