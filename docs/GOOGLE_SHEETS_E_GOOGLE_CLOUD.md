# Google Sheets + Google Cloud: planilha, conta de serviço e secrets

Este guia cobre: colunas administrativas da planilha, criação da conta de serviço
no Google Cloud, compartilhamento e configuração dos GitHub Secrets.

## 1. Estrutura da planilha

A planilha vinculada ao Forms (aba **“Respostas de formulário 1”**) nasce com as
colunas de resposta. A moderação adiciona **seis colunas administrativas ao final**
(nesta ordem, com estes títulos):

| Coluna administrativa | Uso |
|---|---|
| **ID** | Opcional. Preencha só se quiser fixar o endereço público do perfil (ex.: `maria-campinas-001`). Vazio = ID derivado automaticamente. |
| **Status** | `PENDENTE`, `APROVADO`, `REJEITADO` ou `INATIVO`. Coluna central da moderação. |
| **Data de aprovação** | Quando aprovado (dd/mm/aaaa). Alimenta a “data de atualização pública” quando não houver outra. |
| **Última atualização** | Preencha quando editar dados do cadastro. Vira a data pública do perfil. |
| **Observações** | Anotações internas. **Nunca são publicadas.** |
| **Ativo** | `Sim`/`Não`. Preencha `Não` para desativar sem perder o histórico (pausa de férias, investigação etc.). Vazio conta como `Sim`. |

O modelo completo (cabeçalhos + linhas de exemplo fictícias) está em
[`scripts/modelo_planilha.csv`](../scripts/modelo_planilha.csv) — útil também
para testar o sincronizador localmente com `--csv`.

### Títulos reconhecidos

O sincronizador normaliza os cabeçalhos (minúsculas, sem acento) e aceita
variações comuns: “Cidade” = “Município”; “Estado” = “UF”; “Número de WhatsApp” =
“WhatsApp”; “Carimbo de data/hora” (padrão do Forms em pt-BR) = data de envio.
Renomeações exóticas podem derrubar a validação — prefira os títulos do modelo.

### Regras de publicação (resumo executivo)

Um cadastro só é publicado quando, simultaneamente:

1. `Status` = **APROVADO**;
2. `Consentimento` da resposta é afirmativo (começa com “Sim”/“Autorizo”);
3. `Ativo` não é negativo (vazio ou “Sim”);
4. UF (27 siglas), município, nome, categoria, profissão e descrição preenchidos;
5. WhatsApp é celular brasileiro válido (normalizado para `55DDD9XXXXXXXX`).

Qualquer problema gera aviso com o **número da linha** e o motivo — sem imprimir
dados pessoais. Registros PENDENTES/REJEITADOS/INATIVOS simplesmente não publicam.

## 2. Criar a conta de serviço no Google Cloud (passo a passo)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com) e crie um
   projeto (ex.: “catalogo-profissionais”);
2. Menu ☰ → **APIs e serviços → Biblioteca** → pesquise **“Google Sheets API”** →
   **Ativar**;
3. ☰ → **IAM e administrador → Contas de serviço → Criar conta de serviço**:
   - Nome: `sincronizador-catalogo` → Criar;
   - Função: **nenhuma função é necessária** (acesso só de leitura via
     compartilhamento da planilha) → Concluído;
4. Abra a conta criada → aba **Chaves → Adicionar chave → Criar nova chave → JSON**;
5. O arquivo JSON é baixado — **guarde com cuidado**; é a credencial completa.

## 3. Compartilhar a planilha com a conta de serviço

1. Abra o JSON da chave e copie o campo `"client_email"`
   (algo como `sincronizador-catalogo@catalogo-profissionais.iam.gserviceaccount.com`);
2. Na planilha de respostas, **Compartilhar** → cole o e-mail → papel **Leitor**;
3. Desmarque “Notificar pessoas” → Enviar/Compartilhar.

Pronto: o sincronizador consegue ler a aba, e apenas ler.

## 4. Configurar os GitHub Secrets

No repositório GitHub: **Settings → Secrets and variables → Actions**.

### Secrets (valores ocultos)

| Nome | Valor |
|---|---|
| `GOOGLE_SHEET_ID` | O ID da planilha, extraído da URL: `https://docs.google.com/spreadsheets/d/`**`ESTE_ID`**`/edit` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | O **conteúdo completo** do arquivo JSON da chave (abra o arquivo, copie tudo, cole no campo do secret) |

### Variáveis (valor visível — opcional)

| Nome | Valor padrão |
|---|---|
| `GOOGLE_SHEET_TAB_NAME` | Se ausente, o sincronizador usa `Respostas de formulário 1` |

## 5. Validação rápida (sem esperar o cron)

1. GitHub → aba **Actions** → workflow **“Sincronizar catálogo”** →
   **Run workflow** → Execute;
2. Acompanhe o log: deve terminar com
   `Sincronização concluída. … publicados: N` e, se houver mudança,
   um commit `chore(sync): atualizar catálogo público`;
3. Confira `public/data/catalogo.json` no repositório: apenas registros aprovados.

## 6. Boas práticas de segurança

- A chave JSON só nos Secrets — **nunca** no repositório, no `.env` ou no site;
- Se a chave vazar: Google Cloud → conta de serviço → Chaves → **excluir** a chave
  e criar outra (e atualizar o secret);
- Mantenha a planilha privada; compartilhe somente com pessoas de moderação;
- O workflow de sincronização usa permissão mínima (`contents: write`) e nunca
  roda em pull requests de terceiros.
