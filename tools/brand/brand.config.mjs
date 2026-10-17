/**
 * Cinemarium's brand assets: what `build.mjs` draws. Everything site-specific lives here; the layout it is poured
 * into is `build.mjs`.
 *
 * Colours are the tokens of `src/styles/tokens.css`, the translucent ones flattened onto the ground, copied as hex
 * because the card is rendered outside the browser. Re-run `npm run brand` after changing any of them.
 */
const fontsource = (pkg, file) => `node_modules/@fontsource/${pkg}/files/${file}`;

export default {
  name: 'Cinemarium',
  url: 'kiarashfa.github.io/Cinemarium',
  tagline: 'A circular video club of favourite series and films, each one a small living room under glass.',

  wordmark: [
    { text: 'Cinem', weight: 400 },
    { text: 'arium', family: 'Cormorant Garamond', weight: 300, italic: true },
  ],

  cardTheme: 'dark',
  colors: {
    background: '#070707',
    ink: '#efe8dc',
    inkSoft: '#bcb6ad',
    muted: '#89857e',
    line: '#2c2b29',
    accent: '#d2ae6c',
  },

  fonts: {
    display: {
      family: 'Bodoni Moda',
      weight: 400,
      tracking: -1,
      files: [{ path: fontsource('bodoni-moda', 'bodoni-moda-latin-400-normal.woff'), weight: 400 }],
    },
    italic: {
      family: 'Cormorant Garamond',
      files: [{ path: fontsource('cormorant-garamond', 'cormorant-garamond-latin-300-italic.woff'), weight: 300, style: 'italic' }],
    },
    body: {
      family: 'Manrope',
      files: [
        { path: fontsource('manrope', 'manrope-latin-400-normal.woff'), weight: 400 },
        { path: fontsource('manrope', 'manrope-latin-500-normal.woff'), weight: 500 },
      ],
    },
  },

  /** The favicon is drawn in fixed colours: nothing to resolve. */
  mark(svg) {
    return svg;
  },
};
