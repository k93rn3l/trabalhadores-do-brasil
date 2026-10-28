import type { APIRoute } from 'astro';
import { carregarCatalogo } from '../lib/catalogo-server';

/**
 * sitemap.xml gerado no build: páginas fixas + perfis, categorias, estados e
 * municípios existentes no catálogo (nunca páginas vazias). Quando não há
 * URL pública configurada, devolvemos um urlset vazio e válido em vez de
 * inventar domínios.
 */
function escaparXML(texto: string): string {
  return texto
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

export const GET: APIRoute = ({ site }) => {
  const rotasEstaticas = [
    '/',
    '/buscar/',
    '/cadastrar/',
    '/solicitar-alteracao/',
    '/denunciar/',
    '/privacidade/',
    '/termos/',
  ];

  const { catalogo } = carregarCatalogo();
  const categorias = new Set<string>();
  const ufs = new Set<string>();
  const municipios = new Set<string>();
  for (const profissional of catalogo.profissionais) {
    categorias.add(profissional.categoriaSlug);
    ufs.add(profissional.uf.toLowerCase());
    municipios.add(`${profissional.uf.toLowerCase()}/${profissional.municipioSlug}`);
  }

  const rotas = [
    ...rotasEstaticas,
    ...catalogo.profissionais.map((p) => `/profissional/${p.id}/`),
    ...[...categorias].map((slug) => `/categoria/${slug}/`),
    ...[...ufs].map((uf) => `/estado/${uf}/`),
    ...[...municipios].map((caminho) => `/municipio/${caminho}/`),
  ];

  const base = site?.href;
  const agora = catalogo.geradoEm;

  if (!base) {
    return new Response(
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
        '<!-- Configure PUBLIC_SITE_URL para gerar o sitemap com URLs absolutas. -->\n' +
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>\n',
      { headers: { 'Content-Type': 'application/xml; charset=utf-8' } },
    );
  }

  const urls = rotas
    .map((rota) => {
      const url = escaparXML(new URL(rota, base).href);
      const dinamica = !rotasEstaticas.includes(rota);
      const lastmod = dinamica && agora ? `<lastmod>${agora.slice(0, 10)}</lastmod>` : '';
      return `  <url><loc>${url}</loc>${lastmod}</url>`;
    })
    .join('\n');

  return new Response(
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
      `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
    { headers: { 'Content-Type': 'application/xml; charset=utf-8' } },
  );
};
