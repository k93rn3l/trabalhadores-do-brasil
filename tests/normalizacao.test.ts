import { describe, expect, it } from 'vitest';
import { capitalizar, limparTexto, normalizarTexto, slug } from '../src/lib/normalizar';

describe('normalizarTexto', () => {
  it('ignora maiúsculas, minúsculas e acentos', () => {
    expect(normalizarTexto('eletricista')).toBe('eletricista');
    expect(normalizarTexto('ELÉTRICISTA')).toBe('eletricista');
    expect(normalizarTexto('Eletricista')).toBe('eletricista');
  });

  it('colapsa espaços e remove extremos', () => {
    expect(normalizarTexto('  Pedreiro   de   obras ')).toBe('pedreiro de obras');
  });

  it('normaliza cedilha, tremas e outros diacríticos', () => {
    expect(normalizarTexto('Coração, pingüim, façanha')).toBe('coracao, pinguim, facanha');
  });
});

describe('slug', () => {
  it('gera slugs seguros para URLs', () => {
    expect(slug('Belo Horizonte')).toBe('belo-horizonte');
    expect(slug('Instalações elétricas')).toBe('instalacoes-eletricas');
    expect(slug('  São  Paulo — Capital! ')).toBe('sao-paulo-capital');
  });

  it('retorna vazio para texto sem caracteres utilizáveis', () => {
    expect(slug('---***---')).toBe('');
  });

  it('limita o comprimento final', () => {
    expect(slug('a'.repeat(200)).length).toBeLessThanOrEqual(80);
  });
});

describe('capitalizar', () => {
  it('converte nomes em maiúsculas para formato apresentável', () => {
    expect(capitalizar('MARIA DA SILVA')).toBe('Maria Da Silva');
    expect(capitalizar('JOÃO SOUZA')).toBe('João Souza');
  });

  it('preserva nomes já digitados com caixa mista', () => {
    expect(capitalizar('Ana Beatriz')).toBe('Ana Beatriz');
    expect(capitalizar('McDonald')).toBe('McDonald');
  });

  it('lida com texto vazio', () => {
    expect(capitalizar('')).toBe('');
  });
});

describe('limparTexto', () => {
  it('remove caracteres de controle', () => {
    expect(limparTexto('linha\u0000com\u0007controle\u001f')).toBe('linha com controle');
  });
});
