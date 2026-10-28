/** Formatações de exibição em pt-BR. */

/** "2026-10-01" -> "1 de outubro de 2026". */
export function formatarData(iso: string): string {
  const data = new Date(`${iso}T12:00:00Z`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/** Número inteiro com separador de milhar pt-BR. */
export function formatarNumero(valor: number): string {
  return valor.toLocaleString('pt-BR');
}

/** Plural simples: 1 profissional, 2 profissionais. */
export function pluralizar(total: number, singular: string, plural: string): string {
  return total === 1 ? singular : plural;
}
