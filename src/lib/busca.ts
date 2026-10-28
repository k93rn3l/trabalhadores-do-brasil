/**
 * Motor de busca e filtros (isomórfico — build e navegador).
 * A busca ignora maiúsculas, minúsculas e acentos, e combina filtros.
 */
import { normalizarTexto, slug } from './normalizar';
import type { Profissional } from './catalogo-parse';

export interface FiltrosBusca {
  /** Texto livre: nome, profissão, categoria, descrição, regiões. */
  texto?: string;
  /** Sigla da UF. */
  uf?: string;
  /** Slug do município. */
  municipio?: string;
  /** Slug da categoria. */
  categoria?: string;
}

interface FiltrosNormalizados {
  termos: string[];
  uf: string;
  municipio: string;
  categoria: string;
}

export function normalizarFiltros(filtros: FiltrosBusca): FiltrosNormalizados {
  return {
    termos: normalizarTexto(filtros.texto ?? '').split(' ').filter(Boolean),
    uf: normalizarTexto(filtros.uf ?? '').toUpperCase().slice(0, 2),
    municipio: slug(filtros.municipio ?? ''),
    categoria: slug(filtros.categoria ?? ''),
  };
}

/** Aplica todos os filtros combinados (todos precisam passar). */
export function combinarFiltros(
  lista: Profissional[],
  filtros: FiltrosBusca,
): Profissional[] {
  const f = normalizarFiltros(filtros);
  return lista.filter((p) => {
    if (f.uf && p.uf !== f.uf) return false;
    if (f.municipio && p.municipioSlug !== f.municipio) return false;
    if (f.categoria && p.categoriaSlug !== f.categoria) return false;
    if (f.termos.length === 0) return true;
    const alvo = normalizarTexto(
      [p.nome, p.profissao, p.categoria, p.descricao, p.municipio, ...p.bairros, ...p.outros_municipios].join(' '),
    );
    return f.termos.every((termo) => alvo.includes(termo));
  });
}

/** Municípios disponíveis em uma lista, ordenados e sem duplicatas. */
export function municipiosDisponiveis(
  lista: Profissional[],
): { slug: string; nome: string }[] {
  const mapa = new Map<string, string>();
  for (const p of lista) {
    if (!mapa.has(p.municipioSlug)) mapa.set(p.municipioSlug, p.municipio);
  }
  return [...mapa.entries()]
    .map(([slugMunicipio, nome]) => ({ slug: slugMunicipio, nome }))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
}

/** Categorias presentes em uma lista, com contagem, ordenadas por nome. */
export function categoriasDisponiveis(
  lista: Profissional[],
): { slug: string; nome: string; total: number }[] {
  const mapa = new Map<string, { nome: string; total: number }>();
  for (const p of lista) {
    const atual = mapa.get(p.categoriaSlug);
    if (atual) atual.total += 1;
    else mapa.set(p.categoriaSlug, { nome: p.categoria, total: 1 });
  }
  return [...mapa.entries()]
    .map(([slugCategoria, info]) => ({ slug: slugCategoria, ...info }))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
}

/** Monta a querystring de busca preservando apenas filtros preenchidos. */
export function montarURLBusca(filtros: FiltrosBusca): string {
  const parametros = new URLSearchParams();
  if (filtros.texto?.trim()) parametros.set('q', filtros.texto.trim());
  if (filtros.uf) parametros.set('uf', filtros.uf);
  if (filtros.municipio) parametros.set('municipio', filtros.municipio);
  if (filtros.categoria) parametros.set('categoria', filtros.categoria);
  const consulta = parametros.toString();
  return consulta ? `/buscar/?${consulta}` : '/buscar/';
}
