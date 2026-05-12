import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://alexfrison.net',
  output: 'static',
  trailingSlash: 'ignore',
  integrations: [mdx()],
});
