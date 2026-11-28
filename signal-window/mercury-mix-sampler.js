/* Eight browser-local pads. Capture comes from deck PCM, never a microphone.
 * IndexedDB keeps samples out of the set JSON and avoids reloading the library. */
(function (root) {
  "use strict";
  const PAD_KEYS = Object.freeze(["e", "r", "t", "y", "u", "i", "o", "p"]);
  const PAD_COUNT = 8,
    MAX_SECONDS = 8;
  class MercurySampler {
    constructor({ ensure, context, selected, decks, output, status }) {
      Object.assign(this, { ensure, context, selected, decks, output, status });
      this.slots = Array.from({ length: PAD_COUNT }, () => null);
      this.buttons = [];
      this.down = new Set();
      this.capture = null;
      this.erase = false;
      this.serial = 0;
      this.bus = null;
      for (let i = 0; i < PAD_COUNT; i++) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.sample = String(i);
        button.onpointerdown = (event) => {
          if (event.button !== 0) return;
          button.setPointerCapture(event.pointerId);
          this.press(i, event.shiftKey);
        };
        button.onpointerup = () => this.release(i);
        button.onpointercancel = () => this.release(i);
        button.onlostpointercapture = () => this.release(i);
        button.onkeydown = (event) => {
          if (["Enter", " "].includes(event.key)) {
            event.preventDefault();
            event.stopPropagation();
            if (!event.repeat) this.press(i, event.shiftKey);
          }
        };
        button.onkeyup = (event) => {
          if (["Enter", " "].includes(event.key)) {
            event.preventDefault();
            event.stopPropagation();
            this.release(i);
          }
        };
        button.onclick = (event) => {
          if (event.detail === 0) {
            this.press(i, event.shiftKey);
            this.release(i);
          }
        };
        document.getElementById("sample-pads").append(button);
        this.buttons.push(button);
      }
      document.getElementById("sample-level").oninput = () => {
        if (this.bus)
          this.bus.gain.setTargetAtTime(
            Number(document.getElementById("sample-level").value),
            this.bus.context.currentTime,
            0.01,
          );
      };
      document.getElementById("erase-sample").onclick = () => {
        this.erase = !this.erase;
        document
          .getElementById("erase-sample")
          .setAttribute("aria-pressed", String(this.erase));
      };
      document.getElementById("stop-samples").onclick = () => this.stop();
      this.render();
      this.ready = this.restore().then(() => {
        this.restored = true;
      });
      const picker = document.getElementById("sample-trim-pad");
      picker.onchange = () => this.renderTrim();
      for (const edge of ["start", "end"]) {
        document.getElementById("sample-trim-" + edge).oninput = (event) => {
          const slot = this.slots[Number(picker.value)];
          if (!slot) return;
          const duration = this.duration(slot);
          const bounds = MercurySampler.bounds(duration, slot.start, slot.end);
          const value = Number(event.target.value);
          slot.start =
            edge === "start"
              ? Math.min(value, bounds.end - 0.01)
              : bounds.start;
          slot.end =
            edge === "end" ? Math.max(value, slot.start + 0.01) : bounds.end;
          this.renderTrim();
          this.render();
        };
        document.getElementById("sample-trim-" + edge).onchange = () => {
          const index = Number(picker.value),
            slot = this.slots[index];
          if (slot)
            this.store(index, this.row(index)).catch(() =>
              this.status(
                "Trim changed for this session; local saving failed.",
                true,
              ),
            );
        };
      }
      document.getElementById("sample-audition").onclick = () =>
        this.trigger(Number(picker.value)).catch((error) =>
          this.status(error.message, true),
        );
    }
    async database() {
      if (!this.dbPromise)
        this.dbPromise = new Promise((resolve, reject) => {
          if (!root.indexedDB)
            return reject(Error("Local sample storage unavailable"));
          const request = indexedDB.open("mercury-mix-pads", 1);
          request.onupgradeneeded = () =>
            request.result.createObjectStore("pads");
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
      return this.dbPromise;
    }
    async store(index, value) {
      const db = await this.database();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction("pads", "readwrite");
        if (value) transaction.objectStore("pads").put(value, index);
        else transaction.objectStore("pads").delete(index);
        transaction.oncomplete = resolve;
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error);
      });
    }
    async restore() {
      try {
        const db = await this.database();
        const rows = await new Promise((resolve, reject) => {
          const request = db.transaction("pads").objectStore("pads").getAll();
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
        for (const row of rows) {
          if (
            Number.isInteger(row.index) &&
            row.index >= 0 &&
            row.index < PAD_COUNT &&
            row.left instanceof Float32Array &&
            row.right instanceof Float32Array &&
            row.rate >= 8000 &&
            row.rate <= 192000 &&
            row.left.length === row.right.length &&
            row.left.length > 0 &&
            row.left.length <= row.rate * MAX_SECONDS &&
            row.left.every(Number.isFinite) &&
            row.right.every(Number.isFinite)
          )
            this.slots[row.index] = {
              ...row,
              title: String(row.title || "Sample").slice(0, 200),
            };
        }
        this.render();
      } catch {
        document.getElementById("sample-status").textContent =
          "Local storage unavailable; pads will last for this session.";
      }
    }
    duration(slot) {
      return slot.buffer?.duration || slot.left.length / slot.rate;
    }
    prepare(slot, ctx) {
      if (!slot.buffer) {
        slot.buffer = ctx.createBuffer(2, slot.left.length, slot.rate);
        slot.buffer.copyToChannel(slot.left, 0);
        slot.buffer.copyToChannel(slot.right, 1);
        delete slot.left;
        delete slot.right;
      }
    }
    row(index) {
      const slot = this.slots[index];
      return {
        index,
        title: slot.title,
        rate: slot.rate,
        start: slot.start,
        end: slot.end,
        left: slot.buffer ? slot.buffer.getChannelData(0) : slot.left,
        right: slot.buffer ? slot.buffer.getChannelData(1) : slot.right,
      };
    }
    renderTrim() {
      const slot =
        this.slots[Number(document.getElementById("sample-trim-pad").value)];
      const duration = slot ? this.duration(slot) : 0;
      const bounds = MercurySampler.bounds(duration, slot?.start, slot?.end);
      for (const edge of ["start", "end"]) {
        const input = document.getElementById("sample-trim-" + edge);
        input.disabled = !slot;
        input.max = duration;
        input.value = bounds[edge];
        document.getElementById("sample-trim-" + edge + "-value").textContent =
          bounds[edge].toFixed(2) + "s";
      }
      document.getElementById("sample-audition").disabled = !slot;
    }
    paintSoon() {
      if (this.paintPending) return;
      this.paintPending = true;
      requestAnimationFrame(() => {
        this.paintPending = false;
        this.render();
      });
    }
    render() {
      this.buttons.forEach((button, i) => {
        const slot = this.slots[i],
          recording = this.capture?.index === i;
        button.replaceChildren();
        for (const [tag, text] of [
          ["b", String(i + 1) + " · " + PAD_KEYS[i].toUpperCase()],
          ["span", recording ? "Recording…" : slot?.title || "Hold to sample"],
          [
            "small",
            recording
              ? "Release to keep"
              : slot
                ? (
                    MercurySampler.bounds(
                      this.duration(slot),
                      slot.start,
                      slot.end,
                    ).end -
                    MercurySampler.bounds(
                      this.duration(slot),
                      slot.start,
                      slot.end,
                    ).start
                  ).toFixed(1) + "s"
                : "Empty",
          ],
        ]) {
          const element = document.createElement(tag);
          element.textContent = text;
          button.append(element);
        }
        button.setAttribute("aria-keyshortcuts", PAD_KEYS[i].toUpperCase());
        button.title =
          PAD_KEYS[i].toUpperCase() + " · trigger sample " + (i + 1);
        button.classList.toggle("loaded", !!slot);
        button.classList.toggle("capturing", recording);
        button.classList.toggle("playing", !!slot?.voice);
        button.setAttribute(
          "aria-label",
          "Sample pad " +
            (i + 1) +
            " (" +
            PAD_KEYS[i].toUpperCase() +
            ")" +
            ": " +
            (recording ? "recording" : slot?.title || "empty; hold to sample"),
        );
      });
      this.renderTrim();
    }
    async trigger(index) {
      if (!this.restored) await this.ready;
      if (!Number.isInteger(index) || index < 0 || index >= PAD_COUNT) return;
      if (!this.slots[index]) {
        document.getElementById("sample-status").textContent =
          "Pad " +
          (index + 1) +
          " is empty. Hold it with the pointer while a deck plays to capture a sample.";
        return;
      }
      await this.play(index);
    }
    async press(index, clear = false) {
      this.down.add(index);
      await this.ready;
      if (clear || this.erase) {
        this.erase = false;
        document
          .getElementById("erase-sample")
          .setAttribute("aria-pressed", "false");
        await this.clear(index);
        return;
      }
      if (this.slots[index]) {
        try {
          await this.play(index);
        } catch (error) {
          this.status(error.message, true);
        }
        return;
      }
      if (this.capture) {
        this.status("Finish the current sample first.");
        return;
      }
      const deck = this.decks[this.selected()];
      if (!deck.track) {
        this.status("Load and play the selected deck before sampling.");
        return;
      }
      const current = {
        index,
        token: ++this.serial,
        deck,
        released: !this.down.has(index),
        title: deck.track.title,
      };
      this.capture = current;
      this.render();
      try {
        await this.ensure();
        if (this.capture !== current) return;
        deck.nodes.source.port.postMessage({
          type: "capture-start",
          token: current.token,
        });
        if (current.released)
          deck.nodes.source.port.postMessage({
            type: "capture-stop",
            token: current.token,
          });
        document.getElementById("sample-status").textContent =
          "Recording deck " +
          (deck.index ? "B" : "A") +
          " to pad " +
          (index + 1) +
          " · release to keep · 8s maximum";
      } catch (error) {
        this.capture = null;
        this.render();
        this.status(error.message, true);
      }
    }
    release(index) {
      this.down.delete(index);
      if (this.capture?.index !== index) return;
      this.capture.released = true;
      this.capture.deck.nodes?.source.port.postMessage({
        type: "capture-stop",
        token: this.capture.token,
      });
    }
    async receive(deck, data) {
      if (
        data.type !== "capture-complete" ||
        this.capture?.token !== data.token ||
        this.capture.deck !== deck
      )
        return;
      const current = this.capture;
      this.capture = null;
      if (data.frames < 1 || data.peak < 0.0001) {
        this.render();
        document.getElementById("sample-status").textContent =
          "No sound captured. Play or scratch the selected deck, then hold an empty pad.";
        return;
      }
      const row = {
        index: current.index,
        title: current.title,
        rate: data.rate,
        left: data.left.slice(0, data.frames),
        right: data.right.slice(0, data.frames),
      };
      this.slots[current.index] = row;
      const ctx = this.context?.();
      if (ctx) this.prepare(row, ctx);
      document.getElementById("sample-trim-pad").value = String(current.index);
      this.render();
      document.getElementById("sample-status").textContent =
        "Pad " +
        (current.index + 1) +
        " ready · " +
        (data.frames / data.rate).toFixed(1) +
        "s · Shift-click to clear";
      try {
        await this.store(current.index, this.row(current.index));
      } catch {
        document.getElementById("sample-status").textContent =
          "Sample ready for this session; local saving failed.";
      }
    }
    async play(index) {
      // An active instrument starts sound before any UI work or promise wait.
      let ctx = this.context?.();
      if (!ctx || ctx.state !== "running") ctx = await this.ensure();
      const slot = this.slots[index];
      if (!slot) return;
      if (!this.bus) {
        this.bus = ctx.createGain();
        this.bus.gain.value = Number(
          document.getElementById("sample-level").value,
        );
        this.bus.connect(this.output());
      }
      this.prepare(slot, ctx);
      slot.voice?.stop();
      const voice = ctx.createBufferSource();
      voice.buffer = slot.buffer;
      voice.connect(this.bus);
      slot.voice = voice;
      voice.onended = () => {
        voice.disconnect();
        if (slot.voice === voice) {
          slot.voice = null;
          this.paintSoon();
        }
      };
      const bounds = MercurySampler.bounds(
        this.duration(slot),
        slot.start,
        slot.end,
      );
      voice.start(0, bounds.start, bounds.end - bounds.start);
      this.paintSoon();
    }
    async clear(index) {
      if (this.capture?.index === index) {
        this.capture.deck.nodes?.source.port.postMessage({
          type: "capture-cancel",
        });
        this.capture = null;
      }
      this.slots[index]?.voice?.stop();
      this.slots[index] = null;
      this.render();
      try {
        await this.store(index, null);
      } catch {
        this.status(
          "Pad cleared for this session; local storage could not be updated.",
          true,
        );
      }
    }
    stop() {
      this.down.clear();
      if (this.capture) this.release(this.capture.index);
      this.slots.forEach((slot) => slot?.voice?.stop());
    }
  }
  MercurySampler.bounds = (duration, start, end) => {
    const limit = Math.max(0, Number.isFinite(duration) ? duration : 0);
    const minimum = Math.min(0.01, limit);
    start = Math.max(
      0,
      Math.min(Number.isFinite(start) ? start : 0, limit - minimum),
    );
    end = Math.max(
      start + minimum,
      Math.min(Number.isFinite(end) ? end : limit, limit),
    );
    return { start, end };
  };
  MercurySampler.keys = PAD_KEYS;
  MercurySampler.keyIndex = (key, shift = false) => {
    key = String(key).toLowerCase();
    return shift && (key === "r" || key === "t") ? -1 : PAD_KEYS.indexOf(key);
  };
  root.MercurySampler = MercurySampler;
})(globalThis);
