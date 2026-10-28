import { describe, expect, it } from 'vitest';
import { categoriasDisponiveis, combinarFiltros, municipiosDisponiveis } from '../src/lib/busca';
import type { Profissional } from '../src/lib/catalogo-parse';

function profissional(parcial: Partial<Profissional>): Profissional {
  return {
    id: 'id-' + Math.random().toString(36).slice(2, 10),
    nome: 'Maria da Silva',
    categoria: 'Beleza e estética',
    categoriaSlug: 'beleza-e-estetica',
    profissao: 'Cabelereira',
    descricao: 'Cortes e coloração a domicílio em Campinas.',
    uf: 'SP',
    estado: 'São Paulo',
    municipio: 'Campinas',
    municipioSlug: 'campinas',
    bairros: ['Taquaral'],
    outros_municipios: [],
    atendimento_remoto: false,
    whatsapp: '5519999998888',
    atualizadoEm: '2026-10-01',
    ...parcial,
  };
}

const lista: Profissional[] = [
  profissional({}),
  profissional({
    nome: 'João Souza',
    categoria: 'Instalações elétricas',
    categoriaSlug: 'instalacoes-eletricas',
    profissao: 'Eletricista residencial',
    descricao: 'Chuveiros, tomadas e quadros. Orçamento gratuito.',
    uf: 'MG',
    estado: 'Minas Gerais',
    municipio: 'Belo Horizonte',
    municipioSlug: 'belo-horizonte',
    bairros: ['Centro', 'Savassi'],
    outros_municipios: ['Contagem'],
    atendimento_remoto: true,
  }),
  profissional({
    nome: 'Ana Lima',
    profissao: 'Encanadora',
    categoria: 'Hidráulica',
    categoriaSlug: 'hidraulica',
    descricao: 'Desentupimento e consertos hidráulicos.',
    uf: 'SP',
    estado: 'São Paulo',
    municipio: 'Santos',
    municipioSlug: 'santos',
  }),
];

describe('busca sem diferenciação de acentos', () => {
  it('encontra por profissão digitada de qualquer forma', () => {
    expect(combinarFiltros(lista, { texto: 'eletricista' })).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'ELÉTRICISTA' })).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'Eletricista' })[0]?.nome).toBe('João Souza');
  });

  it('busca por nome, palavra da descrição e bairro/município atendido', () => {
    expect(combinarFiltros(lista, { texto: 'maria' })).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'orçamento' })).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'savassi' })).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'contagem' })).toHaveLength(1);
  });

  it('exige que todos os termos estejam presentes (busca E)', () => {
    expect(combinarFiltros(lista, { texto: 'eletricista orçamento' })).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'eletricista manicure' })).toHaveLength(0);
  });
});

describe('combinação de filtros', () => {
  it('filtra por UF', () => {
    const resultado = combinarFiltros(lista, { uf: 'sp' });
    expect(resultado).toHaveLength(2);
    expect(resultado.every((p) => p.uf === 'SP')).toBe(true);
  });

  it('filtra por município e categoria (slugs)', () => {
    expect(combinarFiltros(lista, { municipio: 'belo-horizonte' })[0]?.nome).toBe('João Souza');
    expect(combinarFiltros(lista, { categoria: 'beleza-e-estetica' })[0]?.nome).toBe('Maria da Silva');
  });

  it('combina texto + UF + município + categoria', () => {
    expect(
      combinarFiltros(lista, { texto: 'eletricista', uf: 'MG', municipio: 'belo-horizonte', categoria: 'instalacoes-eletricas' }),
    ).toHaveLength(1);
    expect(combinarFiltros(lista, { texto: 'eletricista', uf: 'SP' })).toHaveLength(0);
  });

  it('lista inteira quando nenhum filtro', () => {
    expect(combinarFiltros(lista, {})).toHaveLength(3);
    expect(combinarFiltros(lista, { texto: '   ' })).toHaveLength(3);
  });
});

describe('listagens derivadas', () => {
  it('municípios ordenados e sem duplicatas', () => {
    const municipios = municipiosDisponiveis([...lista, profissional({ municipio: 'Campinas', municipioSlug: 'campinas' })]);
    expect(municipios.map((m) => m.slug)).toEqual(['belo-horizonte', 'campinas', 'santos']);
  });

  it('categorias com contagem', () => {
    const beleza = categoriasDisponiveis(lista).find((c) => c.slug === 'beleza-e-estetica');
    expect(beleza?.total).toBe(1);
  });
});
