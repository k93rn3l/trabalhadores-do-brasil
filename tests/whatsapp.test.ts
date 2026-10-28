import { describe, expect, it } from 'vitest';
import { linkWhatsApp, normalizarWhatsApp } from '../src/lib/whatsapp';

describe('normalizarWhatsApp', () => {
  it.each([
    ['(11) 99999-8888', '5511999998888'],
    ['11999998888', '5511999998888'],
    ['5511999998888', '5511999998888'],
    ['+55 11 99999-8888', '5511999998888'],
    ['+55 (21) 9 8765-4321', '5521987654321'],
    ['55 55 98123-4567', '5555981234567'], // DDD 55 (RS), não código do país
    ['5511987654321', '5511987654321'],
    ['0 55 11 99999-8888', '5511999998888'], // prefixo de operadora
  ])('normaliza %s para %s', (entrada, esperado) => {
    expect(normalizarWhatsApp(entrada)).toBe(esperado);
  });

  it.each([
    ['1132445566'],             // telefone fixo com DDD
    ['551132445566'],           // fixo com código do país
    ['999998888'],              // sem DDD
    ['99999999999'],            // todos iguais
    ['1234567890'],             // DDD inexistente (10)
    ['abcedfghi'],              // sem dígitos
    [''],                       // vazio
    ['551198765432'],           // incompleto (12 dígitos)
  ])('rejeita número inválido: %s', (entrada) => {
    expect(normalizarWhatsApp(entrada)).toBeNull();
  });
});

describe('linkWhatsApp', () => {
  it('gera link wa.me básico', () => {
    expect(linkWhatsApp('5511999998888')).toBe('https://wa.me/5511999998888');
  });

  it('adiciona mensagem codificada', () => {
    const link = linkWhatsApp('5511999998888', 'Olá! Vi seu contato no catálogo.');
    expect(link).toBe(
      'https://wa.me/5511999998888?text=' +
        encodeURIComponent('Olá! Vi seu contato no catálogo.'),
    );
  });

  it('ignora mensagem apenas com espaços', () => {
    expect(linkWhatsApp('5511999998888', '   ')).toBe('https://wa.me/5511999998888');
  });
});
