/* Stereo varispeed deck. No DOM, network, or allocations in the sample loop. */
const MAX_GESTURE_SECONDS = 30;
class MercuryDeck extends AudioWorkletProcessor {
  constructor() {
    super();
    this.left = null;
    this.right = null;
    this.pos = 0;
    this.rate = 1;
    this.direction = 1;
    this.playing = false;
    this.scratching = false;
    this.target = 0;
    this.travel = 0;
    this.slip = false;
    this.slipPos = 0;
    this.loop = null;
    this.elapsed = 0;
    this.rms = 0;
    this.gesture = null;
    this.gestureGate = 0;
    this.port.onmessage = ({ data: m }) => {
      if (m.type === "gesture") this.startGesture(m);
      if (m.type === "gesture-release" && this.gesture?.token === m.token)
        this.gesture.release = true;
      if (m.type === "gesture-stop") this.finishGesture();
      if (m.type === "load") {
        this.finishGesture();
        this.left = m.left;
        this.right = m.right;
        this.sourceRate = m.rate;
        this.pos = 0;
        this.target = 0;
        this.travel = 0;
        this.playing = false;
        this.loop = null;
        this.scratching = false;
        this.direction = 1;
        this.rate = 1;
        this.slip = false;
        this.slipPos = 0;
      }
      if (m.type === "clear") {
        this.finishGesture();
        this.left = null;
        this.right = null;
        this.playing = false;
        this.scratching = false;
        this.loop = null;
        this.pos = 0;
      }
      if (m.type === "play") {
        this.playing = !!m.value;
        if (this.left && this.pos >= this.left.length - 1) this.pos = 0;
      }
      if (m.type === "rate")
        this.rate = Math.max(0.25, Math.min(4, Number(m.value) || 1));
      if (m.type === "reverse") this.direction = m.value ? -1 : 1;
      if (m.type === "seek" && this.left) {
        this.pos = Math.max(
          0,
          Math.min(this.left.length - 1, m.seconds * this.sourceRate),
        );
        this.target = this.pos;
        this.travel = this.pos;
      }
      if (m.type === "slip") this.slip = !!m.value;
      if (m.type === "loop")
        this.loop = m.value
          ? {
              start: Math.max(0, m.start * this.sourceRate),
              end: Math.min(this.left?.length || 0, m.end * this.sourceRate),
            }
          : null;
      if (m.type === "scratch") {
        if (m.active && !this.scratching) {
          this.slipPos = this.pos;
          this.target = this.pos;
          this.travel = this.pos;
        }
        if (!m.active && this.scratching && this.slip && this.playing)
          this.pos = this.slipPos;
        this.scratching = !!m.active;
      }
      if (m.type === "move" && this.left && Number.isFinite(m.seconds)) {
        const target = this.target + m.seconds * this.sourceRate;
        this.target = this.loop
          ? target
          : Math.max(0, Math.min(this.left.length - 1, target));
      }
    };
  }
  startGesture(m) {
    if (
      !this.left ||
      this.left.length < 2 ||
      !Array.isArray(m.points) ||
      m.points.length < 2 ||
      m.points.length > 80 ||
      !Number.isFinite(m.cue) ||
      !Number.isFinite(m.span) ||
      !Number.isFinite(m.seconds) ||
      m.seconds < 0.1 ||
      m.seconds > MAX_GESTURE_SECONDS ||
      m.span <= 0 ||
      m.span > 2
    )
      return;
    if (
      m.points.some(
        (p, i) =>
          !Array.isArray(p) ||
          ![3, 4].includes(p.length) ||
          p.some((v) => !Number.isFinite(v)) ||
          p[0] < 0 ||
          p[0] > 1 ||
          p[1] < 0 ||
          p[1] > 1 ||
          p[2] < 0 ||
          p[2] > 1 ||
          (p.length === 4 && Math.abs(p[3]) > 1000) ||
          (i && p[0] <= m.points[i - 1][0]),
      )
    )
      return;
    if (m.points[0][0] !== 0 || m.points[m.points.length - 1][0] !== 1) return;
    // Finish a previous phrase before taking the new timeline snapshot.
    this.finishGesture();
    const cue = Math.max(
      0,
      Math.min(this.left.length - 2, m.cue * this.sourceRate),
    );
    this.gesture = {
      token: m.token,
      points: m.points,
      cue,
      span: Math.min(m.span * this.sourceRate, this.left.length - 2 - cue),
      samples: Math.round(m.seconds * sampleRate),
      age: 0,
      segment: 0,
      original: this.pos,
      release: false,
    };
    this.gestureGate = 0;
    this.port.postMessage({ type: "gesture-start", token: m.token });
  }
  finishGesture() {
    const g = this.gesture;
    if (!g) return;
    this.pos = this.playing
      ? this.wrap(
          g.original +
            ((g.age * this.sourceRate) / sampleRate) *
              this.rate *
              this.direction,
        )
      : g.cue;
    this.pos = Math.max(0, Math.min((this.left?.length || 1) - 1, this.pos));
    this.gesture = null;
    this.port.postMessage({ type: "gesture-end", token: g.token });
  }
  wrap(p) {
    const loop = this.loop;
    if (loop && loop.end > loop.start && (p >= loop.end || p < loop.start)) {
      const size = loop.end - loop.start;
      return loop.start + ((((p - loop.start) % size) + size) % size);
    }
    return p;
  }
  process(inputs, outputs) {
    const out = outputs[0],
      l = out[0],
      r = out[1] || l,
      length = this.left?.length || 0;
    let sum = 0;
    for (let i = 0; i < l.length; i++) {
      let a = 0,
        b = 0;
      if (length && this.gesture) {
        const g = this.gesture,
          phase = (g.age % g.samples) / g.samples;
        while (
          g.segment < g.points.length - 2 &&
          phase >= g.points[g.segment + 1][0]
        )
          g.segment++;
        const from = g.points[g.segment],
          to = g.points[g.segment + 1];
        const fraction = (phase - from[0]) / (to[0] - from[0]);
        let position = from[1] + (to[1] - from[1]) * fraction;
        if (from.length === 4 && to.length === 4) {
          const u = fraction,
            u2 = u * u,
            u3 = u2 * u,
            h = to[0] - from[0];
          position =
            (2 * u3 - 3 * u2 + 1) * from[1] +
            (u3 - 2 * u2 + u) * h * from[3] +
            (-2 * u3 + 3 * u2) * to[1] +
            (u3 - u2) * h * to[3];
        }
        this.pos = g.cue + g.span * Math.max(0, Math.min(1, position));
        // A stationary record is silent; a short gate ramp avoids digital clicks.
        const gate = from[1] === to[1] ? 0 : from[2];
        this.gestureGate +=
          (gate - this.gestureGate) * Math.min(1, 1 / (sampleRate * 0.001));
        const at = Math.floor(this.pos),
          sub = this.pos - at;
        a =
          (this.left[at] + (this.left[at + 1] - this.left[at]) * sub) *
          this.gestureGate;
        b =
          (this.right[at] + (this.right[at + 1] - this.right[at]) * sub) *
          this.gestureGate;
        g.age++;
        if (g.age % g.samples === 0) {
          if (g.release) this.finishGesture();
          else g.segment = 0;
        }
      } else if (length) {
        let speed = this.scratching
          ? Math.max(
              -8,
              Math.min(
                8,
                (this.target - this.travel) / (this.sourceRate * 0.014),
              ),
            )
          : this.playing
            ? this.rate * this.direction
            : 0;
        if (
          Math.abs(speed) > 0.0001 &&
          this.pos >= 0 &&
          this.pos < length - 1
        ) {
          const at = Math.floor(this.pos),
            fraction = this.pos - at;
          a = this.left[at] + (this.left[at + 1] - this.left[at]) * fraction;
          b = this.right[at] + (this.right[at + 1] - this.right[at]) * fraction;
        }
        if (this.scratching) {
          this.travel += (speed * this.sourceRate) / sampleRate;
          this.pos = this.wrap(this.travel);
        } else
          this.pos = this.wrap(
            this.pos + (speed * this.sourceRate) / sampleRate,
          );
        if (this.scratching && this.playing)
          this.slipPos = this.wrap(
            this.slipPos +
              (this.rate * this.direction * this.sourceRate) / sampleRate,
          );
        if (
          !this.scratching &&
          !this.loop &&
          (this.pos >= length - 1 || this.pos < 0)
        ) {
          this.playing = false;
          this.pos = Math.max(0, Math.min(length - 1, this.pos));
        }
      }
      l[i] = a;
      r[i] = b;
      sum += a * a + b * b;
    }
    this.elapsed += l.length;
    if (this.elapsed >= sampleRate / 20) {
      this.elapsed = 0;
      this.port.postMessage({
        type: "position",
        seconds: length ? this.pos / this.sourceRate : 0,
        playing: this.playing,
        ended:
          !!length &&
          !this.playing &&
          !this.scratching &&
          !this.gesture &&
          (this.direction > 0 ? this.pos >= length - 1 : this.pos <= 0),
        rms: Math.sqrt(sum / (2 * l.length)),
      });
    }
    return true;
  }
}
registerProcessor("mercury-deck", MercuryDeck);
