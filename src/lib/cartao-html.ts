/**
 * Gerador de HTML do cartão de profissional — fonte única usada tanto pelas
 * páginas estáticas (Astro) quanto pela busca no navegador. Todo conteúdo
 * variável passa por escapeHTML: nenhum dado do catálogo é injetado sem
 * escape, o que protege contra XSS mesmo se dados maliciosos entrarem na
 * planilha.
 */
import type { Profissional } from './catalogo-parse';
import { linkWhatsApp } from './whatsapp';

const ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

export function escapeHTML(texto: string): string {
  return texto.replace(/[&<>"']/g, (caractere) => ESCAPES[caractere] ?? caractere);
}

/** Corta o texto em palavra inteira, adicionando reticências. */
export function truncar(texto: string, maximo: number): string {
  if (texto.length <= maximo) return texto;
  const cortado = texto.slice(0, maximo - 1);
  const ultimoEspaco = cortado.lastIndexOf(' ');
  const base = ultimoEspaco > maximo * 0.6 ? cortado.slice(0, ultimoEspaco) : cortado;
  return `${base.trimEnd()}…`;
}

const ICONE_WHATSAPP =
  '<svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">' +
  '<path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.5.1-.2.2-.6.8-.7 1-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4 0-.5.1-.7l.4-.5c.1-.2.1-.3 0-.5l-.7-1.7c-.2-.5-.4-.4-.5-.4h-.5c-.2 0-.5.1-.7.3-.2.3-.9.9-.9 2.2s.9 2.5 1.1 2.7c.1.2 1.8 2.8 4.5 3.9 2.2.9 2.6.7 3.1.7.5 0 1.6-.6 1.8-1.3.2-.6.2-1.2.2-1.3-.1-.2-.2-.2-.4-.3Z"/></svg>';

/**
 * HTML do cartão de profissional. `mensagemWhatsApp` é a mensagem inicial
 * codificada para o link wa.me.
 */
export function cartaoHTML(p: Profissional, mensagemWhatsApp: string): string {
  const urlPerfil = `/profissional/${encodeURIComponent(p.id)}/`;
  const bairros = p.bairros.slice(0, 3);
  const sobraBairros = p.bairros.length - bairros.length;
  const bairrosTexto =
    escapeHTML(bairros.join(', ')) + (sobraBairros > 0 ? ` e +${sobraBairros}` : '');

  return `<article class="cartao">
  <div class="cartao__topo">
    <h3 class="cartao__nome"><a href="${urlPerfil}">${escapeHTML(p.nome)}</a></h3>
    <p class="cartao__profissao">${escapeHTML(p.profissao)}</p>
    <p class="cartao__meta">
      <span>${escapeHTML(p.municipio)} — ${p.uf}</span>${p.atendimento_remoto ? '<span class="etiqueta etiqueta--online">Atende online</span>' : ''}
    </p>
  </div>
  ${bairros.length ? `<p class="cartao__regioes"><strong>Atende:</strong> ${bairrosTexto}</p>` : ''}
  <p class="cartao__descricao">${escapeHTML(truncar(p.descricao, 180))}</p>
  <p class="cartao__categoria"><a class="etiqueta etiqueta--categoria" href="/categoria/${p.categoriaSlug}/">${escapeHTML(p.categoria)}</a></p>
  <div class="cartao__acoes">
    <a class="botao botao--whatsapp" href="${linkWhatsApp(p.whatsapp, mensagemWhatsApp)}" target="_blank" rel="noopener noreferrer">${ICONE_WHATSAPP} Conversar no WhatsApp</a>
    <a class="botao botao--discreto" href="${urlPerfil}">Ver perfil</a>
  </div>
</article>`;
}
