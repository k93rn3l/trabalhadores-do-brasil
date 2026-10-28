# Guia administrativo — para quem não programa

Este guia explica como aprovar, corrigir, pausar ou remover profissionais do
catálogo **usando apenas o Google Sheets**. Nenhuma ferramenta técnica é
necessária. O site se atualiza sozinho em até **1 hora** depois das alterações
(para aplicar na hora, veja o item 7).

## O que você precisa

- O link da planilha **“Cadastros — Profissionais Progressistas”** (Google Sheets);
- Permissão de edição nela.

## 1. Entendendo a planilha

Cada **linha** é um cadastro enviado pelo site. As primeiras colunas vêm do
formulário (nome, categoria, profissão, descrição, UF, município, bairros,
WhatsApp, e-mail, consentimento…). As últimas colunas são **nossas**, de
administração:

| Coluna | O que faz |
|---|---|
| **ID** | Deixe vazia (o sistema cria um código estável). Preencha só se o perfil ficar mudando de endereço sem motivo. |
| **Status** | O coração da moderação: `PENDENTE`, `APROVADO`, `REJEITADO`, `INATIVO`. |
| **Data de aprovação** | Anote quando aprovou (ex.: `05/11/2026`). |
| **Última atualização** | Anote quando editar qualquer dado do cadastro. |
| **Observações** | Suas anotações internas. **Nunca aparecem no site.** |
| **Ativo** | `Sim` (ou vazio) = ativo. `Não` = pausado, some do site sem perder os dados. |

## 2. Aprovar um cadastro (rotina principal)

1. Abra a planilha e localize a linha com **Status = PENDENTE**
   (dica: Dados → Criar um filtro, e filtre por PENDENTE);
2. Confira: nome, profissão, descrição coerente, UF/município plausíveis e
   **WhatsApp de celular com DDD**;
3. Na coluna **Status**, troque `PENDENTE` por `APROVADO` (em maiúsculas, sem acento);
4. Na coluna **Data de aprovação**, coloque a data de hoje;
5. Pronto. Em até 1 hora o perfil aparece no site com página própria.

> Se a linha não aparecer, veja o item 8 — provavelmente há um aviso
> (WhatsApp inválido é a causa mais comum).

## 3. Reprovar um cadastro

Coloque `REJEITADO` no **Status**. O cadastro nunca aparece no site, mas fica
na planilha como histórico. Use **Observações** para registrar o motivo
(ex.: “telefone fixo”, “descrição incompleta”).

## 4. Pausar temporariamente (férias, pedido do profissional)

Coloque `Não` na coluna **Ativo** (mantendo `APROVADO` no Status). O perfil
sai do site; para voltar, apague o `Não` ou escreva `Sim`.

## 5. Excluir definitivamente

1. Selecione a linha inteira (número da linha) com botão direito →
   **Excluir linha**;
2. Na próxima sincronização o perfil deixa de existir no site
   (a página dele passa a dar “não encontrada”).
3. Se o pedido veio do próprio profissional (LGPD), apague também o e-mail das
   suas anotações pessoais — a planilha é a única fonte.

## 6. Corrigir dados de um cadastro

Edite direto na célula (nome, profissão, descrição, bairro, WhatsApp, o que for).
Depois:

- Escreva a data de hoje na coluna **Última atualização** — o site mostra essa
  data no perfil;
- **Atenção:** se mudar nome **ou** WhatsApp, o endereço público do perfil
  muda (o código do perfil é derivado desses dados). Sem problema — o antigo
  deixa de existir e o novo é indexado. Para manter o endereço estável ao
  corrigir um erro de digitação no nome, preencha a coluna **ID** com um código
  à sua escolha (letras minúsculas, números e hífen, ex.: `maria-campinas`).

## 7. Publicar na hora (sem esperar 1 hora)

1. Entre no GitHub → aba **Actions** (precisa de acesso ao repositório);
2. Clique em **“Sincronizar catálogo”** → botão **Run workflow** → **Run workflow**;
3. Espere ~3 minutos. Pronto.

## 8. Um cadastro aprovado não apareceu. E agora?

Em ordem, confira na linha:

1. **Status** é exatamente `APROVADO`? (sem espaços extras, sem “aprovado”);
2. **Consentimento** (coluna do formulário) começa com “Sim”? Se estiver vazio
   ou “Não”, o sistema bloqueia por segurança;
3. **Ativo** não está `Não`;
4. **WhatsApp** é celular com DDD? Telefones fixos (8 dígitos) e números sem DDD
   são recusados automaticamente;
5. **UF** é uma sigla válida (SP, MG…) e **Município** está preenchido?

Para ver a lista exata de recusas com o número das linhas: GitHub → Actions →
última execução de “Sincronizar catálogo” → etapa “Sincronizar Google Sheets → JSON”.

## 9. Cuidados importantes

- **Nunca compartilhe a planilha publicamente** — ela contém e-mails e dados
  não aprovados;
- A coluna de **e-mail** e a de **endereço comercial** nunca aparecem no site —
  o sistema as ignora por design, e há testes automatizados garantindo isso;
- Não insira linhas manuais acima da linha de cabeçalho nem renomeie as
  colunas existentes — a sincronização depende dos títulos;
- Dúvida sobre o que é público? Abra o perfil no site: **o que está lá é tudo
  o que aparece**.
