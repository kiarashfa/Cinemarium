// The club's places and their addresses. Every address is a static page that opens the club at that place; inside
// the club, moving between places changes the address without a reload.
//   /            home: just inside the entrance, the whole room
//   /<slug>/     a title's case
//   /board/      the board of the lists
//   /about/      the exit
import { TITLES, label, type Title } from './titles';

export type Route = { view: 'home' } | { view: 'case'; slug: string } | { view: 'board' } | { view: 'about' };
export type View = Route['view'];

const BASE = import.meta.env.BASE_URL.replace(/\/?$/, '/');

export const titleOf = (slug: string) => TITLES.find(t => t.slug === slug);

/** The route an address points to (anything unknown is home). */
export function parse(pathname: string): Route {
  const rest = pathname.startsWith(BASE) ? pathname.slice(BASE.length) : pathname.replace(/^\//, '');
  const seg = rest.split('/').filter(Boolean)[0] ?? '';
  if (seg === 'board' || seg === 'about') return { view: seg };
  return titleOf(seg) ? { view: 'case', slug: seg } : { view: 'home' };
}

export function path(r: Route) {
  return BASE + (r.view === 'home' ? '' : r.view === 'case' ? `${r.slug}/` : `${r.view}/`);
}

const SITE = 'Cinemarium';
const caseHead = (t: Title) => ({ title: `${label(t)} · ${SITE}`, description: `${label(t)}: ${t.scene}, a small living room under glass in a circular video club.` });

/** The page's title and description. */
export function head(r: Route): { title: string; description: string } {
  if (r.view === 'case') { const t = titleOf(r.slug); if (t) return caseHead(t); }
  if (r.view === 'board') return { title: `The Board · ${SITE}`, description: 'Ten series and ten films, in order: by personal rank, by year or by IMDb rating.' };
  if (r.view === 'about') return { title: `About · ${SITE}`, description: 'What Cinemarium is, and where its pieces come from.' };
  return { title: SITE, description: 'A circular video club of favourite series and films, each one a small living room under glass.' };
}
