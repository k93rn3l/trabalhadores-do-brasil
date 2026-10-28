# Solicitações de alteração/exclusão e denúncias — procedimento operacional

Documento interno da moderação. Define como atender pedidos de titulares e
denúncias de visitantes **com verificação de legitimidade**, evitando que
terceiros removam ou sequestrem cadastros alheios. A face pública desses fluxos
está nas páginas `/solicitar-alteracao/` e `/denunciar/` do site.

## 1. Canais de entrada

| Canal | Quando existe |
|---|---|
| Formulário “Solicitação de alteração/exclusão” (`PUBLIC_GOOGLE_FORM_ALTERACAO_URL`) | Configurado pelo administrador; respostas caem numa planilha própria |
| Formulário “Denúncia” (`PUBLIC_GOOGLE_FORM_DENUNCIA_URL`) | Idem |
| E-mail institucional (`PUBLIC_CONTATO_EMAIL`) | Sempre disponível quando configurado |

Até os formulários existirem, o e-mail é o canal; as páginas do site indicam
isso automaticamente.

## 2. Tipos de solicitação e prazo-alvo

| Tipo | Prazo-alvo | Ação na planilha |
|---|---|---|
| Correção de informações | 5 dias úteis | Editar células + “Última atualização” |
| Troca de WhatsApp | 5 dias úteis | Editar WhatsApp + data (ver §4!) |
| Mudança de região/categoria | 5 dias úteis | Editar + data |
| Desativação temporária | 2 dias úteis | “Ativo” = Não |
| Exclusão definitiva (LGPD) | 15 dias (prazo legal de resposta) | Excluir linha (§5) |
| Retirada de consentimento | Imediato na próxima sincronização | Tratar como exclusão ou desativação, conforme pedido |

## 3. Verificação de legitimidade (obrigatória para mudanças sensíveis)

Mudanças **sensíveis** = troca de WhatsApp, exclusão, retirada de consentimento.
Para os demais (correção de descrição etc.), a correspondência de dados já basta.

Aceita-se como prova de titularidade, **em ordem de preferência**:

1. **Mensagem do WhatsApp cadastrado** pedindo a alteração — o pedido pode
   chegar pelo próprio `wa.me` do perfil ou por ligação confirmada;
2. **E-mail vindo do e-mail administrativo registrado** na linha;
3. **Verificação alternativa** (quando o titular perdeu o acesso):
   - vídeo-chamada breve apresentando documento com o nome público **parcialmente
     visível** (suficiente para conferir nome, sem expor número), ou
   - foto segurando um papel escrito à mão com o nome público e a data do pedido,
     enviada por qualquer canal;
4. Em caso de dúvida razoável, **não alterar** e escalar para segunda pessoa
   da moderação.

**Nunca** execute mudança sensível baseada apenas em “meu nome é X, apaga lá”,
mesmo com os dados corretos — o site é público e os dados do cadastro também.

## 4. Troca de WhatsApp — detalhe técnico importante

O endereço público do perfil (`/profissional/ID/`) é derivado, entre outros
campos, do WhatsApp e do nome. Ao trocar o número:

1. Edite o WhatsApp na planilha;
2. **Se quiser preservar o endereço antigo** (ex.: o profissional divulgou o
   link impresso), preencha a coluna **ID** com o código do perfil atual
   (visível na URL antiga) antes de salvar;
3. Sem ID fixado, o perfil ganhará novo endereço na próxima sincronização —
   avise o solicitante.

## 5. Exclusão definitiva (checklist LGPD)

- [ ] Titularidade verificada (§3);
- [ ] Registrar o pedido em Observações **antes** de excluir (data, canal,
      what foi pedido) — ou em seu registro interno de moderação;
- [ ] Excluir a linha da planilha;
- [ ] Confirmar ao titular (pelo mesmo canal) quando sair do ar
      (até 1 hora, ou rodar a sincronização manual);
- [ ] O JSON público é derivado: a exclusão da linha remove todos os dados
      públicos na próxima sincronização. Não há backup público a limpar.

## 6. Denúncias — triagem

Classifique por severidade:

| Severidade | Exemplos | Ação imediata |
|---|---|---|
| Alta | Uso de dados de terceiros; conteúdo ilegal/ofensivo | “Ativo” = Não **na hora** (pausa o perfil); investigar; manter ou excluir |
| Média | Informação enganosa, número fora de serviço | Tentar contato com o profissional (48h); sem resposta, pausar até corrigir |
| Baixa | Cadastro duplicado | Manter o mais recente/completo; pausar o outro; registrar |

Regra de ouro: em dúvida sobre dano a terceiros, **pause primeiro e investigue
depois** — a pausa é reversível, a exposição não.

## 7. Denunciante

- O contato do denunciante **nunca** é repassado ao profissional denunciado;
- Denúncias anônimas são aceitas, mas sem contato a apuração pode ficar
  limitada — registre a limitação em Observações;
- Fim da apuração: comunicar o denunciante (quando houver contato) e o
  profissional (quando a conta permanecer ativa e o caso não for fraude).

## 8. Registro mínimo

Cada atendimento deixa rastro em Observações (ou registro interno):

```
[2026-11-05] Solicitação de correção via form. Verificado e-mail admin.
Descrição atualizada + data. Sem pendências.
```

Não registre dados sensíveis além do necessário para a finalidade
(minimização — LGPD).
