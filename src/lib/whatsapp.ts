/**
 * Validação e normalização de números brasileiros de WhatsApp
 * e geração de links oficiais no formato https://wa.me/55DDDNUMERO.
 */

/**
 * Converte a entrada (com parênteses, traços, +55 etc.) no formato
 * internacional "55DDD9XXXXXXXX", ou null quando o número não é um
 * celular brasileiro válido para WhatsApp.
 *
 * Aceita: "(11) 99999-8888", "5511999998888", "11999998888",
 * "+55 55 98123-4567" (DDD 55 — Pelotas/RS).
 * Rejeita: fixos (10 dígitos), sem DDD, DDD inválido, celular sem o 9.
 */
export function normalizarWhatsApp(entrada: string): string | null {
  if (typeof entrada !== 'string') return null;
  let digitos = entrada.replace(/\D/g, '');
  if (!digitos) return null;
  digitos = digitos.replace(/^0+/, ''); // prefixos de operadora/longa distância

  if (digitos.length === 13 && digitos.startsWith('55')) {
    return validarCelular(digitos.slice(2));
  }
  if (digitos.length === 11) {
    return validarCelular(digitos);
  }
  return null;
}

function validarCelular(dddENumero: string): string | null {
  if (dddENumero.length !== 11) return null;
  const ddd = Number.parseInt(dddENumero.slice(0, 2), 10);
  const numero = dddENumero.slice(2);
  if (Number.isNaN(ddd) || ddd < 11 || ddd > 99) return null;
  if (!numero.startsWith('9')) return null; // celulares brasileiros têm 9 dígitos
  if (/^(\d)\1{10}$/.test(dddENumero)) return null; // ex.: 11111111111
  return `55${dddENumero}`;
}

/** Monta o link oficial do WhatsApp com mensagem inicial opcional. */
export function linkWhatsApp(whatsapp: string, mensagem?: string): string {
  const base = `https://wa.me/${whatsapp}`;
  const texto = mensagem?.trim();
  return texto ? `${base}?text=${encodeURIComponent(texto)}` : base;
}
