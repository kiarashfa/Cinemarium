// The two lists. Kia's full top tens are still to come; the proof of concept uses three titles that are
// certainly on them. `rank` is Kia's own order (1 = best) and stays undefined until Kia sets it;
// the tower can also sort by year or by IMDb rating.
export type Kind = 'series' | 'film';
export type Sort = 'rank' | 'year' | 'imdb';

export interface Title {
  slug: string;
  kind: Kind;
  title: string;
  year: number;
  /** The scene in the room, shown as the label's subtitle. */
  scene: string;
  rank?: number;
  imdb: { id: string; rating?: number; asOf?: string };
  /** Room id in the room registry. */
  room: string;
}

export const TITLES: Title[] = [
  { slug: 'severance', kind: 'series', title: 'Severance', year: 2022, scene: 'Macrodata Refinement, Lumon', imdb: { id: 'tt11280740' }, room: 'severance' },
  { slug: 'lost', kind: 'series', title: 'LOST', year: 2004, scene: 'The Swan station, 108 minutes', imdb: { id: 'tt0411008' }, room: 'lost' },
  { slug: 'the-matrix', kind: 'film', title: 'The Matrix', year: 1999, scene: 'The red pill', imdb: { id: 'tt0133093' }, room: 'the-matrix' },
];

export const KIND_PATH: Record<Kind, string> = { series: 'series', film: 'films' };
export const KIND_NAME: Record<Kind, string> = { series: 'Series', film: 'Films' };

/** The list for one kind in the chosen order: best first. */
export function sorted(kind: Kind, by: Sort = 'rank'): Title[] {
  const list = TITLES.filter(t => t.kind === kind);
  const key = (t: Title) => by === 'year' ? t.year : by === 'imdb' ? -(t.imdb.rating ?? 0) : (t.rank ?? 99);
  return list.slice().sort((a, b) => key(a) - key(b) || a.title.localeCompare(b.title));
}

export const label = (t: Title) => `${t.title} (${t.year})`;
