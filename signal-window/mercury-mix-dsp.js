/* Small pure building blocks shared by the instrument and its offline tests. */
(function (root) {
  "use strict";
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  function fader(position, curve = "smooth", reverse = false) {
    const x = reverse ? 1 - clamp(position, 0, 1) : clamp(position, 0, 1);
    return curve === "cut"
      ? [clamp((1 - x) / 0.09, 0, 1), clamp(x / 0.09, 0, 1)]
      : [Math.cos((x * Math.PI) / 2), Math.sin((x * Math.PI) / 2)];
  }
  function keyPosition(held, hand) {
    const keys = hand === "right" ? ["j", "k", "l", ";"] : ["a", "s", "d", "f"];
    const values = keys
      .map((key, i) => (held.has(key) ? i / 3 : null))
      .filter((v) => v !== null);
    return values.length
      ? values.reduce((a, b) => a + b, 0) / values.length
      : null;
  }
  function wrap(value, start, end) {
    const n = end - start;
    return n > 0 ? start + ((((value - start) % n) + n) % n) : start;
  }
  function time(value) {
    if (!Number.isFinite(value)) return "—";
    value = Math.max(0, Math.floor(value));
    return Math.floor(value / 60) + ":" + String(value % 60).padStart(2, "0");
  }
  function peaks(left, right, bins = 1000) {
    const out = new Float32Array(bins);
    const step = left.length / bins;
    for (let b = 0; b < bins; b++) {
      let peak = 0;
      const end = Math.min(left.length, Math.floor((b + 1) * step));
      for (
        let i = Math.floor(b * step);
        i < end;
        i += Math.max(1, Math.floor(step / 48))
      )
        peak = Math.max(peak, Math.abs(left[i]), Math.abs(right?.[i] || 0));
      out[b] = peak;
    }
    return out;
  }
  function analyze(left, rate) {
    // A bounded energy autocorrelation estimates a starting tempo, never a claim
    // that an arbitrary song has a perfectly detected beat grid.
    const hop = Math.max(1, Math.round(rate / 100)),
      frames = Math.min(9000, Math.floor(left.length / hop)),
      energy = new Float32Array(frames);
    for (let f = 0; f < frames; f++) {
      let sum = 0;
      for (let i = f * hop; i < (f + 1) * hop; i += 8) sum += left[i] * left[i];
      energy[f] = sum;
    }
    const onset = new Float32Array(frames);
    let total = 0;
    for (let f = 1; f < frames; f++) {
      onset[f] = Math.max(0, energy[f] - energy[f - 1]);
      total += onset[f];
    }
    if (total < 0.0001 || frames < 400)
      return { bpm: 120, offset: 0, confidence: 0 };
    let best = 0,
      bestBpm = 120;
    for (let bpm = 70; bpm <= 180; bpm++) {
      const lag = Math.round(6000 / bpm);
      let score = 0;
      for (let i = lag; i < frames; i++) score += onset[i] * onset[i - lag];
      // Small preference toward the middle avoids selecting an octave on ties.
      score *= 1 - Math.abs(bpm - 120) * 0.0003;
      if (score > best) {
        best = score;
        bestBpm = bpm;
      }
    }
    const period = Math.round(6000 / bestBpm);
    let phase = 0,
      strongest = 0;
    for (let p = 0; p < period; p++) {
      let sum = 0;
      for (let i = p; i < frames; i += period) sum += onset[i];
      if (sum > strongest) {
        strongest = sum;
        phase = p;
      }
    }
    return {
      bpm: bestBpm,
      offset: phase / 100,
      confidence: clamp(best / (total / frames + 0.0001), 0, 1),
    };
  }
  function demo(which, rate = 32000) {
    const bpm = which ? 124 : 120,
      duration = (16 * 60) / bpm,
      length = Math.ceil(duration * rate),
      left = new Float32Array(length),
      right = new Float32Array(length);
    let seed = which ? 991 : 73;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return (seed / 4294967296) * 2 - 1;
    };
    for (let i = 0; i < length; i++) {
      const t = i / rate,
        beat = (t * bpm) / 60,
        phase = beat % 1,
        half = (beat * 2) % 1,
        n = random();
      const kick =
        Math.sin(2 * Math.PI * (50 * t + 2.5 * (1 - Math.exp(-phase * 25)))) *
        Math.exp(-phase * 22) *
        0.52;
      const snare =
        Math.floor(beat) % 4 === 1 || Math.floor(beat) % 4 === 3
          ? n * Math.exp(-phase * 25) * 0.19
          : 0;
      const hat = n * Math.exp(-half * 65) * 0.055;
      const note =
        [55, 65.406, 73.416, 49][Math.floor(beat / 4) % 4] * (which ? 2 : 1);
      const bass =
        (Math.sin(2 * Math.PI * note * t) +
          0.22 * Math.sin(4 * Math.PI * note * t)) *
        Math.exp(-phase * 6) *
        0.18;
      const bell = which
        ? Math.sin(2 * Math.PI * note * 4 * t) *
          Math.exp(-((beat * 2) % 1) * 10) *
          0.1
        : 0;
      const v = (kick + snare + hat + bass + bell) * 0.8;
      left[i] = v;
      right[i] = v * 0.97 + Math.sin(2 * Math.PI * note * 2.002 * t) * 0.015;
    }
    return {
      left,
      right,
      rate,
      bpm,
      offset: 0,
      duration,
      title: which ? "Glass Transit" : "Neon Relay",
      artist: "Mercury sessions · original demo",
      demo: which,
    };
  }
  function releasePosition(mode, selected, hamster) {
    if (mode === "latch") return null;
    const audible =
      mode === "return-a" ? 0 : mode === "return-b" ? 1 : 1 - selected;
    return hamster ? 1 - audible : audible;
  }
  function reverbImpulse(rate) {
    const seconds = 1.8,
      size = Math.ceil(rate * seconds);
    const channels = [new Float32Array(size), new Float32Array(size)];
    let seed = 7417;
    for (let i = 0; i < size; i++) {
      const envelope = Math.pow(1 - i / size, 3);
      for (let side = 0; side < 2; side++) {
        seed = (Math.imul(seed, 1664525) + 1013904223) | 0;
        channels[side][i] = (seed / 2147483648) * envelope;
      }
    }
    return channels;
  }
  root.MercuryDSP = {
    releasePosition,
    reverbImpulse,
    clamp,
    fader,
    keyPosition,
    wrap,
    time,
    peaks,
    analyze,
    demo,
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
