// The web app manifest, generated so every path in it runs through the base (the site lives under /Cinemarium/).
import type { APIRoute } from 'astro';
import { SITE, BG } from '../data/site';

export const GET: APIRoute = () => {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, '/');
  const manifest = {
    name: SITE,
    short_name: SITE,
    description: 'A circular video club of favourite series and films, each one a small living room under glass.',
    start_url: base,
    scope: base,
    display: 'standalone',
    background_color: BG,
    theme_color: BG,
    icons: [
      { src: `${base}icon-192.png`, sizes: '192x192', type: 'image/png' },
      { src: `${base}icon-512.png`, sizes: '512x512', type: 'image/png' },
    ],
  };
  return new Response(JSON.stringify(manifest, null, 2), { headers: { 'Content-Type': 'application/manifest+json; charset=utf-8' } });
};
