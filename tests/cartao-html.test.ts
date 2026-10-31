import { describe, expect, it } from 'vitest';
import { escapeHTML, truncar, cartaoHTML } from '../src/lib/cartao-html';
import { profissionalExemplo } from './catalogo.test';

describe('escapeHTML', () => {
  it('escapa caracteres perigosos (proteção contra XSS)', () => {
    expect(escapeHTML('<script>alert("x")</script>')).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;',
    );
    expect(escapeHTML("a'&b")).toBe('a&#39;&amp;b');
  });
});

describe('truncar', () => {
  it('mantém textos curtos intactos e corta em palavra inteira', () => {
    expect(truncar('texto curto', 50)).toBe('texto curto');
    const longo = ' palavra'.repeat(40).trim();
    const cortado = truncar(longo, 100);
    expect(cortado.endsWith('…')).toBe(true);
    expect(cortado.length).toBeLessThanOrEqual(100);
  });
});

describe('cartaoHTML', () => {
  it('escapa conteúdo malicioso vindo do catálogo', () => {
    const maligno = {
      ...profissionalExemplo,
      nome: '<img src=x onerror=alert(1)>',
      descricao: '<script>roubo()</script> Serviço de pintura',
    };
    const html = cartaoHTML(maligno, 'mensagem <perigosa>');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('<script');
    expect(html).toContain('&lt;img');
  });

  it('gera link wa.me válido com mensagem codificada', () => {
    const html = cartaoHTML(profissionalExemplo, 'Olá!');
    expect(html).toContain('https://wa.me/5519999998888?text=Ol%C3%A1!');
    expect(html).toContain('/profissional/abcd1234efgh5678/');
    expect(html).toContain('Conversar no WhatsApp');
  });

  it('inclui botão do Instagram com link e @usuário quando informado', () => {
    const html = cartaoHTML(profissionalExemplo, '');
    expect(html).toContain('https://www.instagram.com/maria.silva/');
    expect(html).toContain('@maria.silva');
    expect(html).toContain('botao--instagram');
  });

  it('omite o botão do Instagram quando o campo é nulo', () => {
    const html = cartaoHTML({ ...profissionalExemplo, instagram: null }, '');
    expect(html).not.toContain('instagram.com');
    expect(html).not.toContain('botao--instagram');
  });

  it('indica atendimento online quando remoto', () => {
    expect(cartaoHTML(profissionalExemplo, '')).not.toContain('Atende online');
    expect(cartaoHTML({ ...profissionalExemplo, atendimento_remoto: true }, '')).toContain('Atende online');
  });
});
