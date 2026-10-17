// robots.txt: crawl everything; the sitemap sits under the base path, not at the origin's root.
import type { APIRoute } from 'astro';

export const GET: APIRoute = ({ site }) => {
  const sitemap = new URL(`${import.meta.env.BASE_URL.replace(/\/?$/, '/')}sitemap-index.xml`, site);
  return new Response(['User-agent: *', 'Allow: /', '', `Sitemap: ${sitemap}`, ''].join('\n'), { headers: { 'Content-Type': 'text/plain' } });
};
