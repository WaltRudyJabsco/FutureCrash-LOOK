/* Eight browser-local pads. Capture comes from deck PCM, never a microphone.
 * IndexedDB keeps samples out of the set JSON and avoids reloading the library. */
(function (root) {
  "use strict";
  const PAD_COUNT = 8,
    MAX_SECONDS = 8;
  class MercurySampler {
    constructor({ ensure, selected, decks, output, status }) {
      Object.assign(this, { ensure, selected, decks, output, status });
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
      this.ready = this.restore();
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
    render() {
      this.buttons.forEach((button, i) => {
        const slot = this.slots[i],
          recording = this.capture?.index === i;
        button.replaceChildren();
        for (const [tag, text] of [
          ["b", String(i + 1)],
          ["span", recording ? "Recording…" : slot?.title || "Hold to sample"],
          [
            "small",
            recording
              ? "Release to keep"
              : slot
                ? (
                    slot.buffer?.duration || slot.left.length / slot.rate
                  ).toFixed(1) + "s"
                : "Empty",
          ],
        ]) {
          const element = document.createElement(tag);
          element.textContent = text;
          button.append(element);
        }
        button.classList.toggle("loaded", !!slot);
        button.classList.toggle("capturing", recording);
        button.classList.toggle("playing", !!slot?.voice);
        button.setAttribute(
          "aria-label",
          "Sample pad " +
            (i + 1) +
            ": " +
            (recording ? "recording" : slot?.title || "empty; hold to sample"),
        );
      });
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
      this.render();
      document.getElementById("sample-status").textContent =
        "Pad " +
        (current.index + 1) +
        " ready · " +
        (data.frames / data.rate).toFixed(1) +
        "s · Shift-click to clear";
      try {
        await this.store(current.index, row);
      } catch {
        document.getElementById("sample-status").textContent =
          "Sample ready for this session; local saving failed.";
      }
    }
    async play(index) {
      const ctx = await this.ensure(),
        slot = this.slots[index];
      if (!slot) return;
      if (!this.bus) {
        this.bus = ctx.createGain();
        this.bus.gain.value = Number(
          document.getElementById("sample-level").value,
        );
        this.bus.connect(this.output());
      }
      if (!slot.buffer) {
        slot.buffer = ctx.createBuffer(2, slot.left.length, slot.rate);
        slot.buffer.copyToChannel(slot.left, 0);
        slot.buffer.copyToChannel(slot.right, 1);
        delete slot.left;
        delete slot.right;
      }
      slot.voice?.stop();
      const voice = ctx.createBufferSource();
      voice.buffer = slot.buffer;
      voice.connect(this.bus);
      slot.voice = voice;
      voice.onended = () => {
        voice.disconnect();
        if (slot.voice === voice) {
          slot.voice = null;
          this.render();
        }
      };
      voice.start();
      this.render();
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
  root.MercurySampler = MercurySampler;
})(globalThis);
