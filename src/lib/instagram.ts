/**
 * Validação e normalização de nomes de usuário do Instagram e geração de
 * links no formato https://www.instagram.com/usuario/.
 *
 * Regras compartilhadas com o Google Forms e o sincronizador: "@" inicial
 * opcional; letras de A a Z, números, ponto e sublinhado; sem pontos
 * consecutivos e sem ponto no início/fim; até 30 caracteres (sem o "@").
 * O catálogo guarda apenas o identificador — o link é montado aqui.
 */
const REGEX_INSTAGRAM = /^@?([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)$/;

/**
 * Converte a entrada no nome de usuário canônico (sem "@"), ou null quando
 * não é um identificador válido do Instagram.
 *
 * Aceita: "@meuservico", "meuservico", "@maria.silva", "profissional_rj".
 * Rejeita: links, espaços, "@@", caracteres especiais, pontos consecutivos,
 * ponto nas pontas e identificadores com mais de 30 caracteres.
 */
export function normalizarInstagram(entrada: string | null | undefined): string | null {
  if (typeof entrada !== 'string') return null;
  const correspondencia = REGEX_INSTAGRAM.exec(entrada.trim());
  const usuario = correspondencia?.[1];
  return usuario && usuario.length <= 30 ? usuario : null;
}

/** Link do perfil no Instagram, ou null quando o valor não é utilizável. */
export function linkInstagram(entrada: string | null | undefined): string | null {
  const usuario = normalizarInstagram(entrada);
  return usuario ? `https://www.instagram.com/${usuario}/` : null;
}
