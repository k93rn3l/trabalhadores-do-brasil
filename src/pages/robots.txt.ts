import type { APIRoute } from 'astro';

/**
 * robots.txt gerado no build. A linha Sitemap só é incluída quando existe
 * URL pública configurada — sem domínio inventado.
 */
export const GET: APIRoute = ({ site }) => {
  const linhas = ['User-agent: *', 'Allow: /'];
  if (site) {
    linhas.push('', `Sitemap: ${new URL('sitemap.xml', site).href}`);
  }
  return new Response(`${linhas.join('\n')}\n`, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
