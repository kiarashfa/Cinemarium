// The two lists, twenty series and twenty films in personal order (rank 1 = best). The top ten of each are in the
// club, each with its room (once built); the ten after them are honourable mentions, named on the board but without
// a room or an address. The club can also order either ten by year or by IMDb rating. Ratings and other facts come
// from src/data/meta.json, written at build time by tools/meta.mjs (IMDb ratings via OMDb).
import META from './meta.json';

export type Kind = 'series' | 'film';
export type Sort = 'rank' | 'year' | 'imdb';

export interface Title {
  /** Its address, /<slug>/: unique across both lists, never one of RESERVED. */
  slug: string;
  kind: Kind;
  /** The personal order within its list: 1 is the favourite; above TOP, an honourable mention (11 to 20). */
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
  // series: the ten in the club (ranks 1-10), then ten honourable mentions
  { slug: 'breaking-bad', kind: 'series', rank: 1, title: 'Breaking Bad', year: 2008, imdb: { id: 'tt0903747' }, scene: "Saul Goodman's office", room: 'breaking-bad' },
  { slug: 'the-sopranos', kind: 'series', rank: 2, title: 'The Sopranos', year: 1999, imdb: { id: 'tt0141842' }, scene: "Dr. Melfi's office", room: 'the-sopranos' },
  { slug: 'twin-peaks', kind: 'series', rank: 3, title: 'Twin Peaks', year: 1990, imdb: { id: 'tt0098936' } },
  { slug: 'lost', kind: 'series', rank: 4, title: 'LOST', year: 2004, imdb: { id: 'tt0411008' }, scene: 'The Swan station', room: 'lost' },
  { slug: 'seinfeld', kind: 'series', rank: 5, title: 'Seinfeld', year: 1989, imdb: { id: 'tt0098904' }, scene: "Jerry's apartment, 5A", room: 'seinfeld' },
  { slug: 'house-md', kind: 'series', rank: 6, title: 'House M.D.', year: 2004, imdb: { id: 'tt0412142' } },
  { slug: 'mr-robot', kind: 'series', rank: 7, title: 'Mr. Robot', year: 2015, imdb: { id: 'tt4158110' } },
  { slug: 'succession', kind: 'series', rank: 8, title: 'Succession', year: 2018, imdb: { id: 'tt7660850' }, scene: 'Boar on the floor', room: 'succession' },
  { slug: 'severance', kind: 'series', rank: 9, title: 'Severance', year: 2022, imdb: { id: 'tt11280740' }, scene: 'Macrodata Refinement, Lumon', room: 'severance' },
  { slug: 'game-of-thrones', kind: 'series', rank: 10, title: 'Game of Thrones', year: 2011, imdb: { id: 'tt0944947' }, scene: 'The throne room', room: 'game-of-thrones' },
  { slug: 'the-leftovers', kind: 'series', rank: 11, title: 'The Leftovers', year: 2014, imdb: { id: 'tt2699128' } },
  { slug: 'the-americans', kind: 'series', rank: 12, title: 'The Americans', year: 2013, imdb: { id: 'tt2149175' } },
  { slug: 'better-call-saul', kind: 'series', rank: 13, title: 'Better Call Saul', year: 2015, imdb: { id: 'tt3032476' } },
  { slug: 'the-office', kind: 'series', rank: 14, title: 'The Office', year: 2005, imdb: { id: 'tt0386676' } },
  { slug: 'the-shield', kind: 'series', rank: 15, title: 'The Shield', year: 2002, imdb: { id: 'tt0286486' } },
  { slug: 'suits', kind: 'series', rank: 16, title: 'Suits', year: 2011, imdb: { id: 'tt1632701' } },
  { slug: 'black-mirror', kind: 'series', rank: 17, title: 'Black Mirror', year: 2011, imdb: { id: 'tt2085059' } },
  { slug: 'sons-of-anarchy', kind: 'series', rank: 18, title: 'Sons of Anarchy', year: 2008, imdb: { id: 'tt1124373' } },
  { slug: 'master-of-none', kind: 'series', rank: 19, title: 'Master of None', year: 2015, imdb: { id: 'tt4635276' } },
  { slug: 'silo', kind: 'series', rank: 20, title: 'Silo', year: 2023, imdb: { id: 'tt14688458' } },
  // films: the ten in the club (ranks 1-10), then ten honourable mentions
  { slug: 'the-matrix', kind: 'film', rank: 1, title: 'The Matrix', year: 1999, imdb: { id: 'tt0133093' }, scene: 'The red pill', room: 'the-matrix' },
  { slug: 'the-godfather', kind: 'film', rank: 2, title: 'The Godfather', year: 1972, imdb: { id: 'tt0068646' }, scene: "Don Corleone's study", room: 'the-godfather' },
  { slug: 'interstellar', kind: 'film', rank: 3, title: 'Interstellar', year: 2014, imdb: { id: 'tt0816692' }, scene: "Murph's room", room: 'interstellar' },
  { slug: '2001-a-space-odyssey', kind: 'film', rank: 4, title: '2001: A Space Odyssey', year: 1968, imdb: { id: 'tt0062622' } },
  { slug: 'rear-window', kind: 'film', rank: 5, title: 'Rear Window', year: 1954, imdb: { id: 'tt0047396' }, scene: "Jeff's apartment", room: 'rear-window' },
  { slug: 'pulp-fiction', kind: 'film', rank: 6, title: 'Pulp Fiction', year: 1994, imdb: { id: 'tt0110912' }, scene: "Brett's apartment", room: 'pulp-fiction' },
  { slug: 'the-green-mile', kind: 'film', rank: 7, title: 'The Green Mile', year: 1999, imdb: { id: 'tt0120689' }, scene: 'E Block', room: 'the-green-mile' },
  { slug: 'shutter-island', kind: 'film', rank: 8, title: 'Shutter Island', year: 2010, imdb: { id: 'tt1130884' } },
  { slug: 'the-big-lebowski', kind: 'film', rank: 9, title: 'The Big Lebowski', year: 1998, imdb: { id: 'tt0118715' }, scene: 'Hollywood Star Lanes', room: 'the-big-lebowski' },
  { slug: 'uncut-gems', kind: 'film', rank: 10, title: 'Uncut Gems', year: 2019, imdb: { id: 'tt5727208' } },
  { slug: 'mulholland-drive', kind: 'film', rank: 11, title: 'Mulholland Drive', year: 2001, imdb: { id: 'tt0166924' } },
  { slug: 'vertigo', kind: 'film', rank: 12, title: 'Vertigo', year: 1958, imdb: { id: 'tt0052357' } },
  { slug: 'la-la-land', kind: 'film', rank: 13, title: 'La La Land', year: 2016, imdb: { id: 'tt3783958' } },
  { slug: 'ai-artificial-intelligence', kind: 'film', rank: 14, title: 'A.I. Artificial Intelligence', year: 2001, imdb: { id: 'tt0212720' } },
  { slug: 'the-intouchables', kind: 'film', rank: 15, title: 'The Intouchables', year: 2011, imdb: { id: 'tt1675434' } },
  { slug: 'terminator-2', kind: 'film', rank: 16, title: 'Terminator 2: Judgment Day', year: 1991, imdb: { id: 'tt0103064' } },
  { slug: 'about-time', kind: 'film', rank: 17, title: 'About Time', year: 2013, imdb: { id: 'tt2194499' } },
  { slug: 'the-florida-project', kind: 'film', rank: 18, title: 'The Florida Project', year: 2017, imdb: { id: 'tt5649144' } },
  { slug: 'birdman', kind: 'film', rank: 19, title: 'Birdman', year: 2014, imdb: { id: 'tt2562232' } },
  { slug: 'the-great-beauty', kind: 'film', rank: 20, title: 'The Great Beauty', year: 2013, imdb: { id: 'tt2358891' } },
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

function order(list: Title[], by: Sort): Title[] {
  const key = (t: Title) => by === 'year' ? t.year : by === 'imdb' ? -(t.imdb.rating ?? 0) : t.rank;
  return list.slice().sort((a, b) => key(a) - key(b) || a.title.localeCompare(b.title));
}

/** A list's ten in the chosen order: best first. */
export const sorted = (kind: Kind, by: Sort = 'rank'): Title[] => order(CLUB.filter(t => t.kind === kind), by);

/** A list's ten honourable mentions in the chosen order (named on the board, with no room and no address). */
export const honourable = (kind: Kind, by: Sort = 'rank'): Title[] => order(TITLES.filter(t => t.kind === kind && !inClub(t)), by);

export const label = (t: Title) => `${t.title} (${t.year})`;
/** The label's subtitle: the room's scene, or that the room is still being built. */
export const subtitle = (t: Title) => t.scene ?? 'A room still being built.';
