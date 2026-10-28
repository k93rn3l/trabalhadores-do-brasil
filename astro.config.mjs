import { defineConfig } from 'astro/config';

// A URL canônica do site é configurável (PUBLIC_SITE_URL). No Cloudflare Pages,
// quando não definida, usamos a URL gratuita gerada automaticamente (CF_PAGES_URL).
// Nunca fixamos um domínio inventado no código.
const site = process.env.PUBLIC_SITE_URL || process.env.CF_PAGES_URL || undefined;

export default defineConfig({
  site,
  trailingSlash: 'ignore',
  compressHTML: true,
  build: {
    format: 'directory',
  },
});
