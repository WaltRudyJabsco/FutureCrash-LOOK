/* Monitoring is a separate bus: cue audio never enters the master recording. */
(function (root) {
  "use strict";
  class MercuryMonitor {
    constructor(ctx, master, main) {
      this.ctx = ctx;
      this.main = main;
      this.mode = "off";
      this.cues = [false, false];
      this.inputs = [ctx.createGain(), ctx.createGain()];
      this.cue = ctx.createGain();
      this.mix = ctx.createGain();
      this.level = ctx.createGain();
      const limiter = ctx.createDynamicsCompressor();
      limiter.threshold.value = -3;
      limiter.ratio.value = 12;
      this.inputs.forEach((n) => n.connect(this.cue));
      this.cue.connect(limiter);
      master.connect(this.mix);
      this.mix.connect(limiter);
      limiter.connect(this.level);
      this.stream = ctx.createMediaStreamDestination();
      this.level.connect(this.stream);
      this.player = new Audio();
      this.player.srcObject = this.stream.stream;
      // Summing each stereo bus to mono at half gain avoids an extra 6 dB.
      this.monoMain = ctx.createGain();
      this.monoCue = ctx.createGain();
      this.monoMain.channelCount = this.monoCue.channelCount = 1;
      this.monoMain.channelCountMode = this.monoCue.channelCountMode =
        "explicit";
      this.split = ctx.createChannelMerger(2);
      main.connect(this.monoMain);
      this.level.connect(this.monoCue);
      this.monoMain.connect(this.split, 0, 0);
      this.monoCue.connect(this.split, 0, 1);
      this.set(0, 0.5);
    }
    smooth(param, value) {
      param.setTargetAtTime(value, this.ctx.currentTime, 0.015);
    }
    set(blend, level) {
      const count = this.cues.filter(Boolean).length;
      this.inputs.forEach((node, i) =>
        this.smooth(node.gain, this.cues[i] ? 1 / Math.sqrt(count) : 0),
      );
      this.smooth(this.cue.gain, Math.cos((blend * Math.PI) / 2));
      this.smooth(this.mix.gain, Math.sin((blend * Math.PI) / 2));
      this.smooth(this.level.gain, level);
    }
    route(mode, muted = false) {
      this.mode = mode;
      // Only these output edges change; neither master nor recording is rerouted.
      try {
        this.main.disconnect(this.ctx.destination);
      } catch {}
      try {
        this.level.disconnect(this.ctx.destination);
      } catch {}
      try {
        this.split.disconnect(this.ctx.destination);
      } catch {}
      this.player.pause();
      this.smooth(this.main.gain, muted ? 0 : 1);
      if (mode === "split") this.split.connect(this.ctx.destination);
      else if (mode === "preview") this.level.connect(this.ctx.destination);
      else this.main.connect(this.ctx.destination);
    }
    async separate(device, muted = false) {
      // The browser's output chooser grants access; no microphone is requested.
      await this.player.setSinkId(device.deviceId);
      this.route("separate", muted);
      try {
        await this.player.play();
      } catch (error) {
        this.route("off", muted);
        throw error;
      }
    }
    close() {
      this.player.pause();
      this.player.srcObject = null;
      this.stream.stream.getTracks().forEach((track) => track.stop());
    }
  }
  root.MercuryMonitor = MercuryMonitor;
})(globalThis);
