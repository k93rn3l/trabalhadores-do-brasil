/**
 * Normalização de textos para buscas e comparações em pt-BR.
 * "Eletricista", "ELÉTRICISTA" e " eletricista " devem ser equivalentes.
 */
const DIACRITICOS = /[\u0300-\u036f]/g;

/** Minúsculas, sem acentos, espaços extras colapsados. */
export function normalizarTexto(valor: string): string {
  return valor
    .normalize('NFD')
    .replace(DIACRITICOS, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

/** Slug seguro para URLs: minúsculo, sem acentos, separado por hífens. */
export function slug(valor: string): string {
  return normalizarTexto(valor)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80)
    .replace(/-+$/g, '');
}

/**
 * Deixa nomes próprios apresentáveis: "MARIA DA SILVA" vira "Maria Da Silva",
 * mas nomes já digitados com caixa mista ("Ana Beatriz") são preservados.
 */
export function capitalizar(valor: string): string {
  const texto = valor.replace(/\s+/g, ' ').trim();
  if (!texto) return '';
  const somenteLetras = texto.replace(/[^\p{L}]/gu, '');
  const maiusculas = texto.match(/\p{Lu}/gu)?.length ?? 0;
  if (somenteLetras.length > 0 && maiusculas / somenteLetras.length > 0.6) {
    const minusculo = texto.toLocaleLowerCase('pt-BR');
    return minusculo.replace(
      /\p{L}+/gu,
      (palavra) => palavra.charAt(0).toLocaleUpperCase('pt-BR') + palavra.slice(1),
    );
  }
  return texto;
}

/** Remove caracteres de controle e espaços duplicados (sanitização básica). */
export function limparTexto(valor: string): string {
  // eslint-disable-next-line no-control-regex
  return valor.replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim();
}
