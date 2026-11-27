/* Stereo varispeed deck. No DOM, network, or allocations in the sample loop. */
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
    this.port.onmessage = ({ data: m }) => {
      if (m.type === "load") {
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
      if (length) {
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
          (this.direction > 0 ? this.pos >= length - 1 : this.pos <= 0),
        rms: Math.sqrt(sum / (2 * l.length)),
      });
    }
    return true;
  }
}
registerProcessor("mercury-deck", MercuryDeck);
