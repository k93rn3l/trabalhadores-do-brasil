/**
 * Configuração central do site.
 *
 * O nome definitivo da plataforma ainda não foi escolhido: altere apenas o
 * campo `nome` aqui (e a mensagem do WhatsApp, se desejar) para trocar a
 * identidade em todo o site, no build e nos metadados.
 *
 * URLs externas (Google Forms) vêm de variáveis de ambiente PUBLIC_* e podem
 * ficar vazias: nesses casos as páginas exibem um aviso em vez de um botão
 * quebrado — veja `recursoConfigurado`.
 */
const env = import.meta.env ?? {};

function texto(valor: string | undefined): string {
  return typeof valor === 'string' ? valor.trim() : '';
}

export const siteConfig = {
  /** Nome da plataforma. Centralizado aqui de propósito: mude só este campo. */
  nome: 'Rede Autônoma',
  descricao:
    'Encontre profissionais autônomos em todo o Brasil: pesquise por profissão, categoria, estado e município e fale diretamente pelo WhatsApp. Cadastro gratuito.',
  palavrasChave: [
    'profissionais autônomos',
    'encontrar profissional',
    'serviços',
    'catálogo de profissionais',
    'Brasil',
  ],

  urlFormCadastro: texto(env.PUBLIC_GOOGLE_FORM_CADASTRO_URL),
  urlFormAlteracao: texto(env.PUBLIC_GOOGLE_FORM_ALTERACAO_URL),
  urlFormDenuncia: texto(env.PUBLIC_GOOGLE_FORM_DENUNCIA_URL),
  contatoEmail: texto(env.PUBLIC_CONTATO_EMAIL),

  /** Mensagem inicial enviada ao profissional pelo WhatsApp (configurável). */
  get mensagemWhatsApp(): string {
    return `Olá! Encontrei seu contato no ${this.nome} e gostaria de saber mais sobre seus serviços.`;
  },
} as const;

/** Uma URL externa só é considerada configurada se for https válida. */
export function recursoConfigurado(url: string | undefined | null): url is string {
  return typeof url === 'string' && /^https:\/\/\S+$/i.test(url.trim());
}
