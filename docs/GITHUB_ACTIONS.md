# GitHub Actions: workflow “Sincronizar profissionais”

Arquivo: `.github/workflows/sincronizar-profissionais.yml`.

## Gatilhos

- `schedule` — a cada hora (`cron: 0 * * * *`, UTC);
- `workflow_dispatch` — manual, com entrada **dry_run** (“Simular sem gravar”)
  que força simulação mesmo com a publicação habilitada.

## Trava de publicação (segurança da primeira execução)

O job grava o catálogo **somente** quando:

1. a execução não é `dry_run`, **e**
2. a **variável de repositório `HABILITAR_PUBLICACAO`** é exatamente `SIM`.

Antes disso, toda execução é **simulação**: lê a planilha real, valida e
imprime o resumo (linhas, elegíveis, pendentes, rejeitados e motivos resumidos,
sem dados pessoais). Nada é gravado nem commitado.

## Etapas (modo gravação)

1. Python 3.12 + dependências;
2. `sync_catalogo.py --publicar` (gera `public/data/profissionais.json`);
3. Validação independente do JSON (`scripts/validar_catalogo.py`);
4. Node 20 + `npm ci` + testes do site + **build de produção**;
5. Verificação de mudança real (`git diff -- public/data`) — sem mudança,
   sem commit (o sincronizador também preserva `geradoEm` quando o conteúdo
   público é idêntico);
6. Commit `chore(sync): atualizar profissionais (…)` e push;
7. **Deploy Hook do Cloudflare Pages**: se o secret
   `CLOUDFLARE_DEPLOY_HOOK_URL` existir, faz `POST` após o push e registra o
   resultado. Ausente → log claro de que a publicação automática dependerá da
   integração Git do Pages. O log distingue **“deploy solicitado”** de
   **“deploy concluído”** (acompanhe em Workers & Pages → Deployments).

Permissões mínimas: `contents: write`. Guard contra pull requests (schedule/
dispatch nunca ocorrem em PR, mas o bloqueio explícito impede acesso a segredos
em qualquer cenário). `concurrency` impede duas sincronizações simultâneas.

## Nota sobre GITHUB_TOKEN

Commits criados com `GITHUB_TOKEN` **não disparam** outros workflows do GitHub
Actions (restrição do próprio GitHub). Por isso o workflow testa e builda tudo
**antes** do commit, e a publicação no Cloudflare acontece pela integração Git
do Pages (que observa o push) e/ou pelo Deploy Hook — nunca dependeríamos de um
segundo workflow acionado pelo commit.

## CI (`ci.yml`)

Push/PR → testes do site, testes do sincronizador, build e validação do JSON
commitado. Permissão `contents: read`, sem segredos.

## Segredos e variáveis (resumo)

| Tipo | Nome | Função |
|---|---|---|
| Secret | `GOOGLE_SERVICE_ACCOUNT_JSON` | credencial da conta de serviço |
| Secret | `PUBLIC_ID_SECRET` | HMAC dos IDs públicos |
| Secret | `CLOUDFLARE_DEPLOY_HOOK_URL` | Deploy Hook (opcional) |
| Secret/Var | `GOOGLE_SHEET_ID` | ID da planilha (padrão já no workflow) |
| Var | `GOOGLE_SHEET_TAB_NAME` | aba (padrão “Respostas ao formulário 1”) |
| Var | `HABILITAR_PUBLICACAO` | `SIM` libera a gravação |
