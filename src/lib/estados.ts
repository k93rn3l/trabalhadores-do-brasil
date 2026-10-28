/** As 27 unidades federativas do Brasil. */
export const UFS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
  'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
  'SP', 'SE', 'TO',
] as const;

export type UF = (typeof UFS)[number];

export const NOMES_POR_UF: Record<UF, string> = {
  AC: 'Acre',
  AL: 'Alagoas',
  AP: 'Amapá',
  AM: 'Amazonas',
  BA: 'Bahia',
  CE: 'Ceará',
  DF: 'Distrito Federal',
  ES: 'Espírito Santo',
  GO: 'Goiás',
  MA: 'Maranhão',
  MT: 'Mato Grosso',
  MS: 'Mato Grosso do Sul',
  MG: 'Minas Gerais',
  PA: 'Pará',
  PB: 'Paraíba',
  PR: 'Paraná',
  PE: 'Pernambuco',
  PI: 'Piauí',
  RJ: 'Rio de Janeiro',
  RN: 'Rio Grande do Norte',
  RS: 'Rio Grande do Sul',
  RO: 'Rondônia',
  RR: 'Roraima',
  SC: 'Santa Catarina',
  SP: 'São Paulo',
  SE: 'Sergipe',
  TO: 'Tocantins',
};

function ehUF(valor: string): valor is UF {
  return (UFS as readonly string[]).includes(valor);
}

/** Valida se o valor é uma sigla de UF válida. */
export function validarUF(valor: string): valor is UF {
  return ehUF(valor.toUpperCase());
}

/**
 * Aceita sigla ("sp", "SP") ou nome do estado ("São Paulo", "sao paulo")
 * e devolve a sigla normalizada, ou null quando inválido.
 */
export function normalizarUF(valor: string): UF | null {
  const limpo = valor
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!limpo) return null;
  const sigla = limpo.toUpperCase();
  if (ehUF(sigla)) return sigla;
  for (const uf of UFS) {
    if (normalizarNome(NOMES_POR_UF[uf]) === limpo) return uf;
  }
  return null;
}

function normalizarNome(nome: string): string {
  return nome
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}
