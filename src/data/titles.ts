// The two lists: ten series and ten films, each with its room. `rank` is the personal order (1 = best);
// the lists can also be ordered by year or by IMDb rating. Ratings and other facts come from src/data/meta.json,
// written at build time by tools/meta.mjs (IMDb ratings via OMDb).
import META from './meta.json';

export type Kind = 'series' | 'film';
export type Sort = 'rank' | 'year' | 'imdb';

export interface Title {
  /** Its address, /<slug>/: unique across both lists, never one of RESERVED. */
  slug: string;
  kind: Kind;
  title: string;
  year: number;
  /** The scene in the room, shown as the label's subtitle. */
  scene: string;
  rank?: number;
  imdb: { id: string; rating?: number; votes?: number; asOf?: string };
  /** Room id in the room registry. */
  room: string;
}

const LIST: Title[] = [
  { slug: 'severance', kind: 'series', title: 'Severance', year: 2022, scene: 'Macrodata Refinement, Lumon', imdb: { id: 'tt11280740' }, room: 'severance' },
  { slug: 'lost', kind: 'series', title: 'LOST', year: 2004, scene: 'The Swan station, 108 minutes', imdb: { id: 'tt0411008' }, room: 'lost' },
  { slug: 'the-matrix', kind: 'film', title: 'The Matrix', year: 1999, scene: 'The red pill', imdb: { id: 'tt0133093' }, room: 'the-matrix' },
];

/** Addresses the club itself uses. */
export const RESERVED = ['board', 'about'];
LIST.forEach((t, i) => {
  if (RESERVED.includes(t.slug) || LIST.findIndex(u => u.slug === t.slug) !== i) throw new Error(`The address /${t.slug}/ is already taken`);
});

const facts = META.titles as Record<string, { imdb?: { rating?: number; votes?: number } }>;
export const TITLES: Title[] = LIST.map(t => ({ ...t, imdb: { ...t.imdb, ...facts[t.slug]?.imdb, asOf: META.asOf } }));

export const KIND_NAME: Record<Kind, string> = { series: 'Series', film: 'Films' };

/** The list for one kind in the chosen order: best first. */
export function sorted(kind: Kind, by: Sort = 'rank'): Title[] {
  const list = TITLES.filter(t => t.kind === kind);
  const key = (t: Title) => by === 'year' ? t.year : by === 'imdb' ? -(t.imdb.rating ?? 0) : (t.rank ?? 99);
  return list.slice().sort((a, b) => key(a) - key(b) || a.title.localeCompare(b.title));
}

export const label = (t: Title) => `${t.title} (${t.year})`;
