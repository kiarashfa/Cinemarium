// Fetches facts about each title at build time and writes src/data/meta.json, which the site imports:
// the IMDb rating and vote count (via OMDb), the TMDB id and rating, runtime and genres.
// Keys come from .env (OMDB_API_KEY, TMDB_TOKEN); they are used here only and never reach the site.
// Usage: node tools/meta.mjs
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = new URL('../', import.meta.url);
const env = Object.fromEntries((existsSync(new URL('.env', root)) ? readFileSync(new URL('.env', root), 'utf8') : '')
  .split(/\r?\n/).map(l => l.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/)).filter(Boolean).map(m => [m[1], m[2].replace(/^["']|["']$/g, '')]));
const OMDB = process.env.OMDB_API_KEY ?? env.OMDB_API_KEY, TMDB = process.env.TMDB_TOKEN ?? env.TMDB_TOKEN;
if (!OMDB || !TMDB) { console.error('needs OMDB_API_KEY and TMDB_TOKEN in .env'); process.exit(1); }

// the titles, read from the source of truth
const src = readFileSync(new URL('src/data/titles.ts', root), 'utf8');
const titles = [...src.matchAll(/slug: '([^']+)', kind: '(series|film)'[^\n]*?imdb: \{ id: '(tt\d+)'/g)].map(m => ({ slug: m[1], kind: m[2], imdb: m[3] }));

async function json(url, headers = {}) {
  const r = await fetch(url, { headers: { accept: 'application/json', ...headers } });
  if (!r.ok) throw new Error(`${r.status} ${url.replace(/apikey=[^&]+/, 'apikey=…')}`);
  return r.json();
}
const num = v => (v && v !== 'N/A' ? Number(String(v).replace(/,/g, '')) : undefined);

const out = { asOf: new Date().toISOString().slice(0, 10), titles: {} };
for (const t of titles) {
  const o = await json(`https://www.omdbapi.com/?i=${t.imdb}&apikey=${OMDB}`);
  if (o.Response === 'False') throw new Error(`OMDb: ${t.imdb} ${o.Error}`);
  const find = await json(`https://api.themoviedb.org/3/find/${t.imdb}?external_source=imdb_id`, { authorization: `Bearer ${TMDB}` });
  const hit = (t.kind === 'film' ? find.movie_results : find.tv_results)?.[0];
  const d = hit ? await json(`https://api.themoviedb.org/3/${t.kind === 'film' ? 'movie' : 'tv'}/${hit.id}`, { authorization: `Bearer ${TMDB}` }) : null;
  out.titles[t.slug] = {
    imdb: { id: t.imdb, rating: num(o.imdbRating), votes: num(o.imdbVotes) },
    tmdb: d ? { id: d.id, rating: Math.round(d.vote_average * 10) / 10, votes: d.vote_count } : undefined,
    year: parseInt(o.Year) || undefined,
    runtime: o.Runtime !== 'N/A' ? o.Runtime : undefined,
    genres: o.Genre !== 'N/A' ? o.Genre.split(', ') : undefined,
    seasons: num(o.totalSeasons),
  };
  console.log(t.slug, 'IMDb', o.imdbRating, 'TMDB', d?.vote_average?.toFixed(1) ?? '–');
}
const path = fileURLToPath(new URL('src/data/meta.json', root));
writeFileSync(path, JSON.stringify(out, null, 2) + '\n');
console.log('wrote', path);
