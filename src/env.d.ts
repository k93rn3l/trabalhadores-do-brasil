/// <reference types="astro/client" />

interface ImportMetaEnv {
  /** URL canônica pública do site (ex.: https://www.dominio.com.br). */
  readonly PUBLIC_SITE_URL?: string;
  /** URL do Google Forms de cadastro. Vazia => recurso indisponível. */
  readonly PUBLIC_GOOGLE_FORM_CADASTRO_URL?: string;
  /** URL do Google Forms de solicitação de alteração/exclusão. */
  readonly PUBLIC_GOOGLE_FORM_ALTERACAO_URL?: string;
  /** URL do Google Forms de denúncia de cadastro. */
  readonly PUBLIC_GOOGLE_FORM_DENUNCIA_URL?: string;
  /** E-mail institucional de contato. */
  readonly PUBLIC_CONTATO_EMAIL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
