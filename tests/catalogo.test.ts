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
  municipio: 'Campinas',
  municipioSlug: 'campinas',
  regioes: ['Taquaral', 'Centro'],
  municipiosAtendidos: ['Valinhos'],
  remoto: false,
  whatsapp: '5519999998888',
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
      expect(resultado.catalogo.profissionais[0]?.nome).toBe('Maria da Silva');
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
    const resultado = analisarCatalogo({ ...catalogoValido, versao: 2 });
    expect(resultado.ok).toBe(false);
  });

  it('rejeita registros com campos obrigatórios ausentes', () => {
    const incompleto = { ...profissionalExemplo };
    delete (incompleto as Record<string, unknown>).whatsapp;
    const resultado = analisarCatalogo({
      versao: 1,
      geradoEm: null,
      total: 1,
      profissionais: [incompleto],
    });
    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.erros.some((e) => e.includes('whatsapp'))).toBe(true);
    }
  });

  it('rejeita WhatsApp fora do formato internacional', () => {
    const invalido = { ...profissionalExemplo, whatsapp: '11999998888' };
    const resultado = analisarCatalogo({
      versao: 1, geradoEm: null, total: 1, profissionais: [invalido],
    });
    expect(resultado.ok).toBe(false);
  });

  it('rejeita UF inexistente', () => {
    const invalido = { ...profissionalExemplo, uf: 'XX' };
    const resultado = analisarCatalogo({
      versao: 1, geradoEm: null, total: 1, profissionais: [invalido],
    });
    expect(resultado.ok).toBe(false);
  });

  it('rejeita ids duplicados', () => {
    const resultado = analisarCatalogo({
      versao: 1,
      geradoEm: null,
      total: 2,
      profissionais: [profissionalExemplo, { ...profissionalExemplo, nome: 'Outra Pessoa' }],
    });
    expect(resultado.ok).toBe(false);
    if (!resultado.ok) {
      expect(resultado.erros.some((e) => e.includes('duplicado'))).toBe(true);
    }
  });

  it('rejeita total divergente da lista', () => {
    const resultado = analisarCatalogo({ ...catalogoValido, total: 5 });
    expect(resultado.ok).toBe(false);
  });

  it('rejeita datas fora do formato AAAA-MM-DD', () => {
    const invalido = { ...profissionalExemplo, atualizadoEm: '01/10/2026' };
    const resultado = analisarCatalogo({
      versao: 1, geradoEm: null, total: 1, profissionais: [invalido],
    });
    expect(resultado.ok).toBe(false);
  });

  it('rejeita entrada que não é objeto', () => {
    expect(analisarCatalogo('texto').ok).toBe(false);
    expect(analisarCatalogo(null).ok).toBe(false);
    expect(analisarCatalogo([]).ok).toBe(false);
  });
});
