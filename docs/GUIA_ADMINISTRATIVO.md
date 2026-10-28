# Guia administrativo — para quem não programa

Como aprovar, corrigir, pausar ou remover profissionais do catálogo usando
apenas o Google Sheets. O site se atualiza sozinho em até **1 hora** depois das
alterações (para aplicar na hora, veja o item 7).

## O que você precisa

- O link da planilha **privada** de respostas do formulário (Google Sheets);
- Permissão de edição nela.

## 1. Entendendo a planilha

Cada **linha** é um cadastro. As colunas do formulário vêm preenchidas
(nome, categoria, profissão, WhatsApp…). As últimas colunas são **nossas**:

| Coluna | O que faz |
|---|---|
| **ID_PUBLICO** | Deixe vazia (o sistema cria um código estável). Preencha só para travar o endereço do perfil (ex.: `maria-campinas`). |
| **STATUS** | `PENDENTE`, `APROVADO`, `REJEITADO` ou `INATIVO`. |
| **ATIVO** | **`SIM`** = ativo. **`NÃO`** = pausado. **Vazio NÃO publica** — precisa dizer `SIM`. |
| **DATA_APROVACAO** | Anote quando aprovou (ex.: `05/11/2026`). |
| **DATA_ATUALIZACAO** | Anote quando editar qualquer dado do cadastro. |
| **OBSERVACOES_INTERNAS** | Suas anotações. **Nunca aparecem no site.** |

## 2. Aprovar um cadastro (rotina principal)

Para publicar uma linha, preencha **as três coisas**:

1. **STATUS** = `APROVADO`
2. **ATIVO** = `SIM`
3. **DATA_APROVACAO** = data de hoje

Confira também: WhatsApp de celular com DDD, Estado e Município preenchidos e a
coluna **Consentimento para publicação** com a frase padrão do formulário
(“Li as informações… autorizo a divulgação pública…”). Em até 1 hora o perfil
aparece no site.

> Se a linha não aparecer, veja o item 8 — o motivo aparece no log da
> sincronização (linha e razão, nunca dados pessoais).

## 3. Reprovar

**STATUS** = `REJEITADO`. Nunca aparece no site; fica na planilha como
histórico. Anote o motivo em OBSERVACOES_INTERNAS.

## 4. Pausar temporariamente

**ATIVO** = `NÃO` (mantendo `APROVADO`). O perfil sai do site; para voltar,
troque para `SIM`.

## 5. Excluir definitivamente

Botão direito no número da linha → **Excluir linha**. Na próxima sincronização
o perfil some do site. Se o pedido veio do próprio profissional (LGPD), a
planilha é a única fonte — apagar a linha remove tudo.

## 6. Corrigir dados

Edite direto nas células. Depois preencha **DATA_ATUALIZACAO** com a data de
hoje (o site mostra essa data no perfil).

**Sobre o endereço do perfil:** ele é derivado do carimbo e do WhatsApp. Se
você corrigir o telefone (ou o nome) de alguém com ID_PUBLICO vazio, o
endereço público muda. Se a pessoa divulgou o link (cartão, Instagram), preencha
**ID_PUBLICO** com um código à sua escolha (letras minúsculas, números e
hífen) ANTES de alterar o telefone — assim o endereço permanece.

## 7. Publicar na hora (sem esperar 1 hora)

GitHub → aba **Actions** → **Sincronizar profissionais** → **Run workflow**
→ Execute (≈3 minutos). Enquanto a variável `HABILITAR_PUBLICACAO` não for
`SIM`, o workflow roda em modo **simulação**: mostra o que seria publicado e
não grava nada — útil para conferir antes de liberar.

## 8. Um cadastro aprovado não apareceu. E agora?

Confira na linha, nesta ordem:

1. **STATUS** é exatamente `APROVADO`? (sem espaços extras, sem “aprovado”)
2. **ATIVO** é exatamente `SIM`? (vazio não publica!)
3. **Consentimento** é a frase padrão do formulário?
4. **WhatsApp** é celular com DDD (fixos são recusados)?
5. **Estado (UF)** e **Município** preenchidos?

A lista exata de recusas com o número das linhas está em: GitHub → Actions →
última execução de “Sincronizar profissionais” → etapa “Sincronizar Google
Sheets → JSON”.

## 9. Cuidados importantes

- **Nunca compartilhe a planilha publicamente** — contém e-mails e dados não
  aprovados;
- E-mail, Endereço comercial e Observações **nunca** são publicados (o sistema
  exporta por lista de permissões — só o que está autorizado sai);
- Não renomeie colunas nem insira linhas acima do cabeçalho — a sincronização
  identifica as colunas pelo nome;
- Dúvida sobre o que é público? Abra o perfil no site: o que está lá é tudo
  o que aparece.
