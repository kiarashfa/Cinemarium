// Cinemarium is served from GitHub Pages at https://kiarashfa.github.io/Cinemarium/
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://kiarashfa.github.io',
  base: '/Cinemarium',
  trailingSlash: 'always',
  devToolbar: { enabled: false },
  integrations: [sitemap()],
  vite: {
    build: { target: 'es2022', assetsInlineLimit: 0 },
  },
});
