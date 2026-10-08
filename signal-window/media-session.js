/* OS media controls belong only to playback on this browser endpoint. */
class SignalMediaSession {
  constructor(navigatorObject, metadataClass, snapshot, control) {
    this.session = navigatorObject?.mediaSession;
    this.Metadata = metadataClass;
    this.snapshot = snapshot;
    this.control = control;
    this.key = '';
    this.registered = false;
    this.actions = {
      play: () => control('play'), pause: () => control('pause'), stop: () => control('stop'),
      nexttrack: () => control('next'), previoustrack: () => control('prev'),
      seekto: d => control('seek', d.seekTime),
      seekforward: d => control('seek', snapshot().position + (d.seekOffset || 10)),
      seekbackward: d => control('seek', snapshot().position - (d.seekOffset || 10)),
    };
  }
  update(ownsPlayback) {
    if (!this.session) return;
    const state = this.snapshot();
    const owned = ownsPlayback && state.count > 0 && ['playing', 'paused'].includes(state.state);
    if (owned !== this.registered) {
      for (const [name, action] of Object.entries(this.actions)) {
        try {
          this.session.setActionHandler(name, owned ? details => {
            const current = this.snapshot();
            if (!this.registered || !['playing', 'paused'].includes(current.state)) return;
            Promise.resolve(action(details || {})).catch(() => {});
          } : null);
        } catch {} // Some browsers support only a subset of actions.
      }
      this.registered = owned;
    }
    if (!owned) {
      this.key = '';
      try { this.session.playbackState = 'none'; this.session.metadata = null; this.session.setPositionState?.(); } catch {}
      return;
    }
    const entry = state.entry || {};
    const art = entry.artwork_url || entry.cover_url;
    const key = JSON.stringify([state.index, entry.title, entry.artist, entry.album, art]);
    if (key !== this.key && this.Metadata) {
      try {
        this.session.metadata = new this.Metadata({title: entry.title || 'Media', artist: entry.artist || '',
          album: entry.album || '', artwork: (/^(https?:\/\/|\/api\/media\/cover\?)/i.test(art || '')) ? [{src: art}] : []});
        this.key = key;
      } catch {}
    }
    try { this.session.playbackState = state.state; } catch {}
    try {
      if (Number.isFinite(state.duration) && state.duration > 0 && Number.isFinite(state.position)) {
        this.session.setPositionState?.({duration: state.duration, playbackRate: 1,
          position: Math.max(0, Math.min(state.position, state.duration))});
      } else this.session.setPositionState?.();
    } catch {}
  }
}
if (typeof module !== 'undefined') module.exports = SignalMediaSession;
