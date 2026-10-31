import { describe, expect, it } from 'vitest';
import { analisarCatalogo, type Profissional } from '../src/lib/catalogo-parse';

export const profissionalExemplo: Profissional = {
  id: 'abcd1234efgh5678',
  nome: 'Maria da Silva',
  categoria: 'Beleza e estética',
  categoriaSlug: 'beleza-e-estetica',
  profissao: 'Cabelereira',
  descricao: 'Cortes e coloração a domicílio.',
  uf: 'SP',
  estado: 'São Paulo',
  municipio: 'Campinas',
  municipioSlug: 'campinas',
  bairros: ['Taquaral', 'Centro'],
  outros_municipios: ['Valinhos'],
  atendimento_remoto: false,
  whatsapp: '5519999998888',
  instagram: 'maria.silva',
  atualizadoEm: '2026-10-01',
};

const catalogoValido = {
  versao: 1,
  geradoEm: '2026-10-01T10:00:00Z',
  total: 1,
  profissionais: [profissionalExemplo],
};

describe('analisarCatalogo', () => {
  it('aceita um catálogo válido', () => {
    const resultado = analisarCatalogo(catalogoValido);
    expect(resultado.ok).toBe(true);
    if (resultado.ok) {
      expect(resultado.catalogo.total).toBe(1);
      expect(resultado.catalogo.profissionais[0]?.estado).toBe('São Paulo');
    }
  });

  it('aceita o catálogo inicial vazio (sem registros)', () => {
    const resultado = analisarCatalogo({ versao: 1, geradoEm: null, total: 0, profissionais: [] });
    expect(resultado.ok).toBe(true);
    if (resultado.ok) {
      expect(resultado.catalogo.profissionais).toHaveLength(0);
      expect(resultado.catalogo.geradoEm).toBeNull();
    }
  });

  it('rejeita versão incorreta', () => {
    expect(analisarCatalogo({ ...catalogoValido, versao: 2 }).ok).toBe(false);
  });

  it('rejeita registros com campos obrigatórios ausentes', () => {
    const incompleto = { ...profissionalExemplo };
    delete (incompleto as Record<string, unknown>).whatsapp;
    const resultado = analisarCatalogo({
      versao: 1, geradoEm: null, total: 1, profissionais: [incompleto],
    });
    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.erros.some((e) => e.includes('whatsapp'))).toBe(true);
    }
  });

  it('rejeita WhatsApp fora do formato internacional', () => {
    const invalido = { ...profissionalExemplo, whatsapp: '21999998888' };
    expect(analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [invalido] }).ok).toBe(false);
  });

  it('aceita instagram ausente ou nulo e normaliza o "@" inicial', () => {
    const semCampo = { ...profissionalExemplo } as Record<string, unknown>;
    delete semCampo.instagram;
    const comNull = { ...profissionalExemplo, instagram: null };
    const comArroba = { ...profissionalExemplo, instagram: '@maria.silva' };

    for (const registro of [semCampo, comNull]) {
      const resultado = analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [registro] });
      expect(resultado.ok).toBe(true);
      if (resultado.ok) expect(resultado.catalogo.profissionais[0]?.instagram).toBeNull();
    }
    const resultado = analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [comArroba] });
    expect(resultado.ok).toBe(true);
    if (resultado.ok) expect(resultado.catalogo.profissionais[0]?.instagram).toBe('maria.silva');
  });

  it('rejeita instagram fora do formato (links, @@, pontos, acima de 30)', () => {
    for (const ruim of ['https://instagram.com/maria', '@@maria', '.maria', 'a..b', 'a'.repeat(31)]) {
      const invalido = { ...profissionalExemplo, instagram: ruim };
      const resultado = analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [invalido] });
      expect(resultado.ok, ruim).toBe(false);
      if (!resultado.ok) expect(resultado.erros.some((e) => e.includes('instagram'))).toBe(true);
    }
  });

  it('rejeita UF inexistente e estado incoerente', () => {
    const ufErrada = { ...profissionalExemplo, uf: 'XX' as never, estado: 'Lugar' };
    expect(analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [ufErrada] }).ok).toBe(false);
    const estadoErrado = { ...profissionalExemplo, estado: 'Minas Gerais' };
    expect(analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [estadoErrado] }).ok).toBe(false);
  });

  it('rejeita ids duplicados', () => {
    const resultado = analisarCatalogo({
      versao: 1,
      geradoEm: null,
      total: 2,
      profissionais: [profissionalExemplo, { ...profissionalExemplo, nome: 'Outra Pessoa', whatsapp: '5519988887777' }],
    });
    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.erros.some((e) => e.includes('duplicado'))).toBe(true);
    }
  });

  it('rejeita total divergente da lista', () => {
    expect(analisarCatalogo({ ...catalogoValido, total: 5 }).ok).toBe(false);
  });

  it('rejeita datas fora do formato AAAA-MM-DD', () => {
    const invalido = { ...profissionalExemplo, atualizadoEm: '01/10/2026' };
    expect(analisarCatalogo({ versao: 1, geradoEm: null, total: 1, profissionais: [invalido] }).ok).toBe(false);
  });

  it('rejeita entrada que não é objeto', () => {
    expect(analisarCatalogo('texto').ok).toBe(false);
    expect(analisarCatalogo(null).ok).toBe(false);
    expect(analisarCatalogo([]).ok).toBe(false);
  });
});
