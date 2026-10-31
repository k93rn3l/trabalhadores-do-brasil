import { describe, expect, it } from 'vitest';
import { linkInstagram, normalizarInstagram } from '../src/lib/instagram';

describe('normalizarInstagram', () => {
  it.each([
    ['@meuservico', 'meuservico'],
    ['meuservico', 'meuservico'],
    ['@maria.silva', 'maria.silva'],
    ['profissional_rj', 'profissional_rj'],
    ['@empresa123', 'empresa123'],
    ['  @maria.silva  ', 'maria.silva'],
    ['a'.repeat(30), 'a'.repeat(30)],
  ])('normaliza %s para %s', (entrada, esperado) => {
    expect(normalizarInstagram(entrada)).toBe(esperado);
  });

  it.each([
    ['https://instagram.com/meuservico'],
    ['www.instagram.com/meuservico'],
    ['instagram.com/meuservico'],
    ['@usuario com espacos'],
    ['@@meuservico'],
    ['usuario!'],
    ['.usuario'],
    ['usuario.'],
    ['a..b'],
    ['a'.repeat(31)],
    [''],
  ])('rejeita identificador inválido: %s', (entrada) => {
    expect(normalizarInstagram(entrada)).toBeNull();
  });

  it('rejeita valor ausente', () => {
    expect(normalizarInstagram(null)).toBeNull();
    expect(normalizarInstagram(undefined)).toBeNull();
  });
});

describe('linkInstagram', () => {
  it('gera link do perfil com barra final', () => {
    expect(linkInstagram('meuservico')).toBe('https://www.instagram.com/meuservico/');
    expect(linkInstagram('@maria.silva')).toBe('https://www.instagram.com/maria.silva/');
  });

  it('retorna null quando o valor é inválido ou ausente', () => {
    expect(linkInstagram(null)).toBeNull();
    expect(linkInstagram(undefined)).toBeNull();
    expect(linkInstagram('https://instagram.com/meuservico')).toBeNull();
  });
});
