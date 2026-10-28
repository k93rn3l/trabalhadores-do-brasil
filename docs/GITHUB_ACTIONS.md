# GitHub Actions: automação de sincronização e CI

Dois workflows vivem em `.github/workflows/`. Nenhum precisa de configuração
além dos Secrets descritos em [GOOGLE_SHEETS_E_GOOGLE_CLOUD.md](GOOGLE_SHEETS_E_GOOGLE_CLOUD.md).

## 1. `sync-catalogo.yml` — Sincronizar catálogo

**Gatilhos:**

- `schedule: cron '0 * * * *'` — a cada hora (fuso UTC; 1h = 0h BRB em horário de Brasília);
- `workflow_dispatch` — botão “Run workflow” para executar na hora.

**Permissões mínimas:** `contents: write` (necessário para o commit dos dados).
O job é bloqueado em `pull_request`/`pull_request_target` — eventos que nunca
disparam este workflow, mas o guard impede acesso a segredos em qualquer cenário.

**Etapas do job:**

1. Checkout do código;
2. Python 3.12 + `pip install -r scripts/requirements.txt`;
3. **Sincronização** com as variáveis/segredos do repositório
   (`GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_TAB_NAME`);
4. Validação independente do JSON (`scripts/validar_catalogo.py`);
5. Node 20 + `npm ci` + **testes do site** + **build de produção**
   (garante que os novos dados não quebram nada antes do commit);
6. Verificação de mudança real (`git diff -- public/data`);
7. Commit `chore(sync): atualizar catálogo público (DATA UTC)` **somente se os
   dados públicos mudaram** — o sincronizador já evita reescrever quando nada
   mudou, então não há commits vazios nem loops.

O commit na `main` dispara automaticamente nova publicação no Cloudflare Pages
(integração Git configurada em [CLOUDFLARE_PAGES.md](CLOUDFLARE_PAGES.md)).

### Executar manualmente

Aba **Actions → Sincronizar catálogo → Run workflow**. Útil depois de aprovar
vários cadastros e não querer esperar a hora cheia.

### Se o workflow falhar

- Falha de autenticação/planilha: revise o compartilhamento e os Secrets
  (o catálogo atual permanece publicado — fail-closed);
- Falha de estrutura: confira os cabeçalhos da planilha;
- Falha de teste/build: o commit não acontece; veja o log da etapa correspondente.

## 2. `ci.yml` — CI de código

**Gatilhos:** push na `main` e pull requests.

**Permissões:** `contents: read` (somente leitura — sem acesso a segredos).

**Etapas:** `npm ci` → Vitest (72 testes) → `astro check` não incluso aqui, rode
localmente se desejar; build de produção → Python 3.12 → pytest (43 testes) →
validação do `public/data/catalogo.json` commitado.

## 3. Custos e limites

Ambos os workflows rodam confortavelmente no **free tier** do GitHub Actions
(2.000 min/mês para contas gratuitas em repositórios privados; ilimitado em
públicos). A sincronização horária consome ~3–5 min/hora.

## 4. Desativar ou mudar a periodicidade

- Editar o `cron` em `.github/workflows/sync-catalogo.yml`
  (ex.: `0 */6 * * *` = a cada 6 horas);
- Para pausar: Actions → Sincronizar catálogo → **⋯ → Disable workflow**.
