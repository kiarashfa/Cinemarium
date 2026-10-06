// Room tone, made on the fly (nothing recorded, nothing licensed): off until the visitor turns it on.
// MDR: the hum of fluorescent ballasts, air in the ducts, now and then a soft key.
export interface Tone { start(): void; stop(): void; playing: boolean }

export function roomTone(kind: 'office' | 'quiet' = 'office'): Tone {
  let ctx: AudioContext | null = null, master: GainNode | null = null, timer = 0;
  const tone: Tone = {
    playing: false,
    start() {
      ctx ??= new AudioContext();
      master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination);
      master.gain.linearRampToValueAtTime(0.5, ctx.currentTime + 1.5);
      // ballast hum: 120 Hz and a few harmonics, very low
      for (const [f, g] of [[120, 0.010], [240, 0.006], [360, 0.002]]) {
        const o = ctx.createOscillator(), a = ctx.createGain(); o.frequency.value = f; a.gain.value = g; o.connect(a).connect(master); o.start();
      }
      // air: brown-ish noise through a low-pass
      const n = ctx.createBufferSource(), buf = ctx.createBuffer(1, ctx.sampleRate * 4, ctx.sampleRate), d = buf.getChannelData(0);
      let last = 0; for (let i = 0; i < d.length; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = last * 3.2; }
      n.buffer = buf; n.loop = true;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 520;
      const ag = ctx.createGain(); ag.gain.value = kind === 'office' ? 0.05 : 0.03; n.connect(lp).connect(ag).connect(master); n.start();
      if (kind === 'office') {
        const key = () => {
          if (!ctx || !master) return;
          const t = ctx.currentTime, src = ctx.createBufferSource(), b = ctx.createBuffer(1, 800, ctx.sampleRate), c = b.getChannelData(0);
          for (let i = 0; i < c.length; i++) c[i] = (Math.random() * 2 - 1) * Math.exp(-i / 90);
          const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2400 + Math.random() * 1200; bp.Q.value = 1.4;
          const g = ctx.createGain(); g.gain.value = 0.018 + Math.random() * 0.012;
          src.buffer = b; src.connect(bp).connect(g).connect(master); src.start(t);
          timer = window.setTimeout(key, Math.random() < 0.15 ? 900 + Math.random() * 2200 : 90 + Math.random() * 180);
        };
        key();
      }
      tone.playing = true;
    },
    stop() {
      if (!ctx || !master) return;
      clearTimeout(timer); master.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.6);
      const c = ctx; setTimeout(() => c.close(), 800); ctx = null; master = null; tone.playing = false;
    },
  };
  return tone;
}
