/* Cover bytes stay on Fabric; presentation belongs to this endpoint. */
class SignalArtwork {
  constructor(documentObject, storage) {
    this.document = documentObject; this.storage = storage; this.cache = new Map();
    try { this.mode = storage.getItem('signal.artwork') || 'ascii'; } catch { this.mode = 'ascii'; }
    if (!['ascii', 'image', 'off'].includes(this.mode)) this.mode = 'ascii';
  }
  setMode(mode) {
    if (!['ascii', 'image', 'off'].includes(mode)) return;
    this.mode = mode;
    try { this.storage.setItem('signal.artwork', mode); } catch {}
  }
  url(entry, fallbackNode) {
    if (!entry?.id) return '';
    return '/api/media/cover?' + new URLSearchParams({node: entry.node || fallbackNode || '', id: entry.id});
  }
  static ascii(pixels, width, height) {
    const ramp = ' .:-=+*#%@'; const lines = [];
    for (let y = 0; y < height; y++) {
      let line = '';
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4;
        const brightness = (.2126 * pixels[i] + .7152 * pixels[i+1] + .0722 * pixels[i+2]) * pixels[i+3] / 255;
        line += ramp[Math.min(9, Math.floor(brightness / 256 * 10))];
      }
      lines.push(line);
    }
    return lines.join('\n');
  }
  load(url) {
    if (this.cache.has(url)) return this.cache.get(url);
    const promise = new Promise(resolve => {
      const img = this.document.createElement('img');
      const timer = setTimeout(() => { img.src = ''; resolve(null); }, 15000);
      img.onload = () => {
        clearTimeout(timer);
        try {
          const canvas = this.document.createElement('canvas'); canvas.width = 48; canvas.height = 24;
          const ctx = canvas.getContext('2d', {willReadFrequently: true});
          ctx.drawImage(img, 0, 0, 48, 24);
          resolve(SignalArtwork.ascii(ctx.getImageData(0, 0, 48, 24).data, 48, 24));
        } catch { resolve(null); }
      };
      img.onerror = () => { clearTimeout(timer); resolve(null); };
      img.src = url;
    });
    this.cache.set(url, promise);
    if (this.cache.size > 32) this.cache.delete(this.cache.keys().next().value);
    // A transient transport failure must not hide a cover for the entire session.
    promise.then(value => { if (value === null && this.cache.get(url) === promise) {
      setTimeout(() => { if (this.cache.get(url) === promise) this.cache.delete(url); }, 30000);
    }});
    return promise;
  }
  render(url) {
    if (!url || this.mode === 'off') return null;
    if (this.mode === 'image') {
      const img = this.document.createElement('img'); img.className = 'media-cover';
      img.alt = 'Album cover'; img.src = url; img.onerror = () => { img.hidden = true; }; return img;
    }
    const pre = this.document.createElement('pre'); pre.className = 'media-ascii';
    pre.setAttribute('role', 'img'); pre.setAttribute('aria-label', 'Album cover in ASCII');
    pre.textContent = 'Loading album art…';
    this.load(url).then(text => { pre.textContent = text || 'Album art unavailable'; });
    return pre;
  }
}
if (typeof module !== 'undefined') module.exports = SignalArtwork;
