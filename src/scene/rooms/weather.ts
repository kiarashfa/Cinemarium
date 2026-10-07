// Weather at a window: lightning that strikes now and then (a value the room's light, the lace and the people follow),
// and rain running down the glass over a night street, drawn live.
import * as THREE from 'three/webgpu';
import { texture, time, uniform, uv, vec2, vec3 } from 'three/tsl';
import { canvasTexture, rng } from '../materials';

/** Lightning: a strike every 7 to 20 seconds, two or three flickers each, and a faint afterglow. */
export function lightning(seed = 3) {
  const r = rng(seed); let next = 4 + r() * 6; let pulses: { at: number; k: number }[] = [];
  const flash = uniform(0);
  return {
    flash,
    update(t: number) {
      if (t >= next) {
        const n = 2 + Math.floor(r() * 2); pulses = [];
        let o = 0; for (let i = 0; i < n; i++) { pulses.push({ at: t + o, k: (i ? 0.45 + r() * 0.5 : 1) }); o += 0.07 + r() * 0.2; }
        next = t + 7 + r() * 13;
      }
      let v = 0;
      for (const p of pulses) { const d = t - p.at; if (d >= 0) v += p.k * (Math.exp(-d / 0.07) + 0.12 * Math.exp(-d / 0.6)); }
      flash.value = Math.min(1.6, v);
    },
  };
}

/** The night beyond the glass: a dark street, a few lit windows across the road, a lamp's glow, wet paving. */
function streetTexture() {
  return canvasTexture(512, 512, (c, w, h) => {
    const r = rng(81), sky = c.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#04070a'); sky.addColorStop(0.55, '#0a1210'); sky.addColorStop(1, '#141a12'); c.fillStyle = sky; c.fillRect(0, 0, w, h);
    c.filter = 'blur(7px)';
    for (let k = 0; k < 10; k++) { c.fillStyle = `rgba(255,${200 + r() * 40},${130 + r() * 50},${0.2 + r() * 0.3})`; c.fillRect(r() * w, h * (0.08 + r() * 0.42), 16 + r() * 22, 22 + r() * 30); }
    const lamp = c.createRadialGradient(w * 0.7, h * 0.32, 2, w * 0.7, h * 0.32, w * 0.42);
    lamp.addColorStop(0, 'rgba(210,235,200,.4)'); lamp.addColorStop(1, 'rgba(210,235,200,0)'); c.fillStyle = lamp; c.fillRect(0, 0, w, h);
    c.fillStyle = 'rgba(190,220,190,.08)'; c.fillRect(0, h * 0.84, w, h * 0.16);
    c.filter = 'none';
  });
}

/** Drops and rivulets on glass: red and green hold the slope of the water (0.5 = flat), blue its glint. */
function rainTexture() {
  const t = canvasTexture(512, 512, (c, w, h) => {
    const r = rng(23); c.fillStyle = 'rgb(128,128,0)'; c.fillRect(0, 0, w, h);
    const drop = (x: number, y: number, rad: number) => {
      const g = c.createRadialGradient(x - rad * 0.3, y - rad * 0.3, 0, x, y, rad);
      g.addColorStop(0, 'rgb(90,90,255)'); g.addColorStop(0.6, 'rgb(150,150,90)'); g.addColorStop(1, 'rgba(128,128,0,0)');
      c.fillStyle = g; c.beginPath(); c.ellipse(x, y, rad * 0.85, rad, 0, 0, 6.283); c.fill();
    };
    for (let k = 0; k < 26; k++) {           // rivulets: a crooked trail down the pane, a bead at its foot
      let x = r() * w, y = r() * h * 0.6; const len = 60 + r() * 220;
      c.strokeStyle = 'rgba(160,140,170,.55)'; c.lineWidth = 1.2 + r() * 1.6; c.beginPath(); c.moveTo(x, y);
      for (let s = 0; s < len; s += 8) { x += (r() - 0.5) * 3; y += 8; c.lineTo(x, y); }
      c.stroke(); drop(x, y, 3 + r() * 3);
    }
    for (let k = 0; k < 340; k++) drop(r() * w, r() * h, 1 + r() ** 3 * 5);
  }, { srgb: false });
  return t;
}

/** The glass of a window at night in the rain: the street refracted through running water, brightened by lightning. */
export function rainGlass(flash: any) {
  const street = streetTexture(), rain = rainTexture();
  street.wrapS = street.wrapT = THREE.RepeatWrapping; rain.wrapS = rain.wrapT = THREE.RepeatWrapping;
  const m = new THREE.MeshBasicNodeMaterial();
  const p = uv().mul(vec2(0.7, 0.7));                                    // the glass's UVs are in metres
  const a = texture(rain, p.mul(vec2(1.0, 0.8)).add(vec2(0.0, time.mul(0.045)))), b = texture(rain, p.mul(vec2(1.6, 1.3)).add(vec2(0.37, time.mul(0.11))));
  const slope = a.rg.add(b.rg).sub(1.0);
  const view = texture(street, p.mul(vec2(0.55, 0.45)).add(slope.mul(0.035))).rgb;
  const glint = a.b.add(b.b).mul(0.12);
  m.colorNode = view.mul(1.3).add(vec3(0.6, 0.7, 0.68).mul(glint)).add(vec3(0.75, 0.85, 1.0).mul(flash).mul(0.9));
  return m;
}
