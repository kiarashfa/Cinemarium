// The two lists, fifteen series and fifteen films in personal order (rank 1 = best). The top ten of each are in the
// club, each with its room (once built); the five after them are honourable mentions, named but without a room. The
// club can also order its ten by year or by IMDb rating. Ratings and other facts come from src/data/meta.json,
// written at build time by tools/meta.mjs (IMDb ratings via OMDb).
import META from './meta.json';

export type Kind = 'series' | 'film';
export type Sort = 'rank' | 'year' | 'imdb';

export interface Title {
  /** Its address, /<slug>/: unique across both lists, never one of RESERVED. */
  slug: string;
  kind: Kind;
  /** The personal order within its list: 1 is the favourite; above TOP, an honourable mention. */
  rank: number;
  title: string;
  year: number;
  imdb: { id: string; rating?: number; votes?: number; asOf?: string };
  /** The scene its room shows (chosen when the room is built), the label's subtitle. */
  scene?: string;
  /** Its room's id in the room registry, once the room is built. */
  room?: string;
}

/** How many of each list are in the club (with rooms); the rest are honourable mentions. */
export const TOP = 10;

const LIST: Title[] = [
  { slug: 'breaking-bad', kind: 'series', rank: 1, title: 'Breaking Bad', year: 2008, imdb: { id: 'tt0903747' } },
  { slug: 'the-leftovers', kind: 'series', rank: 2, title: 'The Leftovers', year: 2014, imdb: { id: 'tt2699128' } },
  { slug: 'seinfeld', kind: 'series', rank: 3, title: 'Seinfeld', year: 1989, imdb: { id: 'tt0098904' } },
  { slug: 'house-md', kind: 'series', rank: 4, title: 'House M.D.', year: 2004, imdb: { id: 'tt0412142' } },
  { slug: 'the-americans', kind: 'series', rank: 5, title: 'The Americans', year: 2013, imdb: { id: 'tt2149175' } },
  { slug: 'mr-robot', kind: 'series', rank: 6, title: 'Mr. Robot', year: 2015, imdb: { id: 'tt4158110' } },
  { slug: 'lost', kind: 'series', rank: 7, title: 'LOST', year: 2004, imdb: { id: 'tt0411008' }, scene: 'The Swan station', room: 'lost' },
  { slug: 'the-sopranos', kind: 'series', rank: 8, title: 'The Sopranos', year: 1999, imdb: { id: 'tt0141842' } },
  { slug: 'succession', kind: 'series', rank: 9, title: 'Succession', year: 2018, imdb: { id: 'tt7660850' } },
  { slug: 'severance', kind: 'series', rank: 10, title: 'Severance', year: 2022, imdb: { id: 'tt11280740' }, scene: 'Macrodata Refinement, Lumon', room: 'severance' },
  { slug: 'game-of-thrones', kind: 'series', rank: 11, title: 'Game of Thrones', year: 2011, imdb: { id: 'tt0944947' } },
  { slug: 'twin-peaks', kind: 'series', rank: 12, title: 'Twin Peaks', year: 1990, imdb: { id: 'tt0098936' } },
  { slug: 'sons-of-anarchy', kind: 'series', rank: 13, title: 'Sons of Anarchy', year: 2008, imdb: { id: 'tt1124373' } },
  { slug: 'fargo', kind: 'series', rank: 14, title: 'Fargo', year: 2014, imdb: { id: 'tt2802850' } },
  { slug: 'money-heist', kind: 'series', rank: 15, title: 'Money Heist', year: 2017, imdb: { id: 'tt6468322' } },
  { slug: 'the-matrix', kind: 'film', rank: 1, title: 'The Matrix', year: 1999, imdb: { id: 'tt0133093' }, scene: 'The red pill', room: 'the-matrix' },
  { slug: 'la-la-land', kind: 'film', rank: 2, title: 'La La Land', year: 2016, imdb: { id: 'tt3783958' } },
  { slug: 'inception', kind: 'film', rank: 3, title: 'Inception', year: 2010, imdb: { id: 'tt1375666' } },
  { slug: 'the-godfather', kind: 'film', rank: 4, title: 'The Godfather', year: 1972, imdb: { id: 'tt0068646' } },
  { slug: 'mulholland-drive', kind: 'film', rank: 5, title: 'Mulholland Drive', year: 2001, imdb: { id: 'tt0166924' } },
  { slug: 'vertigo', kind: 'film', rank: 6, title: 'Vertigo', year: 1958, imdb: { id: 'tt0052357' } },
  { slug: 'the-florida-project', kind: 'film', rank: 7, title: 'The Florida Project', year: 2017, imdb: { id: 'tt5649144' } },
  { slug: 'shutter-island', kind: 'film', rank: 8, title: 'Shutter Island', year: 2010, imdb: { id: 'tt1130884' } },
  { slug: 'about-time', kind: 'film', rank: 9, title: 'About Time', year: 2013, imdb: { id: 'tt2194499' } },
  { slug: 'the-green-mile', kind: 'film', rank: 10, title: 'The Green Mile', year: 1999, imdb: { id: 'tt0120689' } },
  { slug: 'interstellar', kind: 'film', rank: 11, title: 'Interstellar', year: 2014, imdb: { id: 'tt0816692' } },
  { slug: '2001-a-space-odyssey', kind: 'film', rank: 12, title: '2001: A Space Odyssey', year: 1968, imdb: { id: 'tt0062622' } },
  { slug: 'the-intouchables', kind: 'film', rank: 13, title: 'The Intouchables', year: 2011, imdb: { id: 'tt1675434' } },
  { slug: 'terminator-2', kind: 'film', rank: 14, title: 'Terminator 2: Judgment Day', year: 1991, imdb: { id: 'tt0103064' } },
  { slug: 'the-big-lebowski', kind: 'film', rank: 15, title: 'The Big Lebowski', year: 1998, imdb: { id: 'tt0118715' } },
];

/** Addresses the club itself uses. */
export const RESERVED = ['board', 'about'];
LIST.forEach((t, i) => {
  if (RESERVED.includes(t.slug) || LIST.findIndex(u => u.slug === t.slug) !== i) throw new Error(`The address /${t.slug}/ is already taken`);
});

const facts = META.titles as Record<string, { imdb?: { rating?: number; votes?: number } }>;
export const TITLES: Title[] = LIST.map(t => ({ ...t, imdb: { ...t.imdb, ...facts[t.slug]?.imdb, asOf: META.asOf } }));

export const KIND_NAME: Record<Kind, string> = { series: 'Series', film: 'Films' };

/** In the club: the top ten of either list (each with its own address). */
export const inClub = (t: Title) => t.rank <= TOP;
export const CLUB = TITLES.filter(inClub);

/** A list's ten in the chosen order: best first. */
export function sorted(kind: Kind, by: Sort = 'rank'): Title[] {
  const list = CLUB.filter(t => t.kind === kind);
  const key = (t: Title) => by === 'year' ? t.year : by === 'imdb' ? -(t.imdb.rating ?? 0) : t.rank;
  return list.slice().sort((a, b) => key(a) - key(b) || a.title.localeCompare(b.title));
}

/** A list's honourable mentions, in personal order. */
export const honourable = (kind: Kind) => TITLES.filter(t => t.kind === kind && !inClub(t)).sort((a, b) => a.rank - b.rank);

export const label = (t: Title) => `${t.title} (${t.year})`;
/** The label's subtitle: the room's scene, or that the room is still being built. */
export const subtitle = (t: Title) => t.scene ?? 'A room still being built.';
