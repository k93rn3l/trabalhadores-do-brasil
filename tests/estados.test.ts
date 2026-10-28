import { describe, expect, it } from 'vitest';
import { NOMES_POR_UF, UFS, normalizarUF, validarUF } from '../src/lib/estados';

describe('lista de UFs', () => {
  it('contém exatamente as 27 unidades federativas', () => {
    expect(UFS).toHaveLength(27);
    expect(UFS).toContain('DF');
    expect(new Set(UFS).size).toBe(27);
    expect(Object.keys(NOMES_POR_UF)).toHaveLength(27);
  });
});

describe('validarUF', () => {
  it('aceita siglas válidas em qualquer caixa', () => {
    expect(validarUF('SP')).toBe(true);
    expect(validarUF('sp')).toBe(true);
  });

  it('rejeita siglas inexistentes', () => {
    expect(validarUF('XX')).toBe(false);
    expect(validarUF('')).toBe(false);
    expect(validarUF('São Paulo')).toBe(false);
  });
});

describe('normalizarUF', () => {
  it('aceita sigla com acentos/maiúsculas ou não', () => {
    expect(normalizarUF('sp')).toBe('SP');
    expect(normalizarUF('SP')).toBe('SP');
    expect(normalizarUF(' Sp ')).toBe('SP');
  });

  it('converte nome do estado para sigla, com ou sem acento', () => {
    expect(normalizarUF('São Paulo')).toBe('SP');
    expect(normalizarUF('sao paulo')).toBe('SP');
    expect(normalizarUF('Distrito Federal')).toBe('DF');
    expect(normalizarUF('rio grande do sul')).toBe('RS');
    expect(normalizarUF('Rio de Janeiro')).toBe('RJ');
  });

  it('retorna null para valores inválidos', () => {
    expect(normalizarUF('São Pauloo')).toBeNull();
    expect(normalizarUF('Texas')).toBeNull();
    expect(normalizarUF('')).toBeNull();
  });
});
