# Trabalhadores do Brasil

Plataforma nacional, **gratuita, estática e sem servidor próprio**, para divulgação de
serviços prestados por profissionais autônomos em todo o Brasil. Visitantes encontram
prestadores por profissão, categoria, estado, município e região atendida — e entram em
contato diretamente pelo **WhatsApp**.

> O nome da plataforma (**Trabalhadores do Brasil**) está centralizado em
> `src/config/site.ts`. Trocar o nome exige alterar um único campo.

**Fluxo completo:** profissional preenche o **Google Forms** → respostas caem na
planilha privada do **Google Sheets** → a moderação aprova → o workflow
**Sincronizar profissionais** do **GitHub Actions** roda a cada hora → apenas
cadastros APROVADOS, com ATIVO=SIM e consentimento válido são exportados para o
JSON público → o **Cloudflare Pages** publica o site atualizado automaticamente.

**Integração real já configurada no código:** formulário
`https://forms.gle/uKqyYZkaTpGTpepb7`, planilha
`1nxcIvRTlAf1HTXbNaeq6oo3gOJN8L52hbcL6NGzTk3M`, aba “Respostas ao formulário 1”.

---

## 1. Descrição do projeto

- Site estático gerado com **Astro (SSG) + TypeScript**, HTML, CSS e JavaScript puros.
- Cadastro via **Google Forms**; dados privados em **Google Sheets** (nunca públicos).
- Sincronização horária por **GitHub Actions** com conta de serviço do Google Cloud.
- Catálogo público em **JSON** versionado no repositório (`public/data/profissionais.json`
  + blocos por UF em `public/data/uf/`), gerado por **allowlist** de campos.
- Sem autenticação de usuários, sem backend em execução, sem serviços pagos.
- Busca com **27 UFs**, filtros combináveis, sem diferenciação de acentos e
  carregamento otimizado por estado (blocos `/data/uf/UF.json`).
- Páginas estáticas por profissional, categoria, estado e município (SEO).
- Políticas de privacidade e termos alinhados à **LGPD**, com consentimento
  explícito e fail-closed: nada é publicado sem aprovação E consentimento E atividade.

## 2. Arquitetura

```
Google Forms ──► Google Sheets (privada)
                      │  ① GitHub Actions (cron horário)
                      │  ② scripts/sync_catalogo.py (conta de serviço)
                      │  ③ filtra APROVADO + ativo + consentimento
                      ▼
              public/data/profissionais.json (+ data/uf/*.json)
                      │  ④ commit (somente se houver mudança real)
                      ▼
              Cloudflare Pages ──► build Astro (SSG) ──► site publicado
```

- `src/pages/` — páginas Astro (inicial, busca, perfil, categoria, estado, município, institucionais).
- `src/components/` — componentes reutilizáveis (cartão, filtros, cabeçalho, rodapé…).
- `src/layouts/` — layout base compartilhado.
- `src/styles/global.css` — identidade visual (variáveis CSS).
- `src/lib/` — busca, filtros, validação, WhatsApp, normalização (isomórfico).
- `src/config/` — nome do site, links externos, categorias.
- `src/types`/tipos — tipagem TypeScript do catálogo em `src/lib/catalogo-parse.ts`.
- `public/data/` — catálogo JSON público (gerado pelo sincronizador).
- `scripts/` — sincronizador Python + validador + modelo de planilha + testes.
- `tests/` — testes automatizados do site (Vitest).
- `.github/workflows/` — automações (sync horário e CI).
- `docs/` — documentação técnica e administrativa.

## 3. Requisitos de instalação

- **Node.js 20 ou superior** (com npm);
- **Python 3.10 ou superior** (somente para o sincronizador e testes Python);
- Conta GitHub (para repositório e Actions);
- Contas gratuitas Google (Forms/Sheets/Cloud) e Cloudflare (Pages) — apenas
  quando for ativar as integrações.

## 4. Como executar localmente

```bash
npm install          # dependências do site
npm run dev          # servidor de desenvolvimento em http://localhost:4321
```

O projeto funciona **sem nenhuma credencial**: o catálogo inicial é vazio e as
integrações não configuradas exibem avisos adequados em vez de botões quebrados.

Para o sincronizador localmente (opcional):

```bash
python -m pip install -r scripts/requirements.txt
```

## 5. Como gerar o build

```bash
npm run build        # gera o site estático em dist/
npm run preview      # serve o build localmente para conferência
```

Variáveis de ambiente opcionais no build (ver `.env.example`):
`PUBLIC_SITE_URL`, `PUBLIC_GOOGLE_FORM_CADASTRO_URL`,
`PUBLIC_GOOGLE_FORM_ALTERACAO_URL`, `PUBLIC_GOOGLE_FORM_DENUNCIA_URL`,
`PUBLIC_CONTATO_EMAIL`. No Cloudflare Pages, se `PUBLIC_SITE_URL` estiver vazia,
a URL gratuita `*.pages.dev` do build é usada automaticamente.

## 6. Como configurar o Google Forms

Guia completo em **[docs/GOOGLE_FORMS.md](docs/GOOGLE_FORMS.md)**. Resumo:

1. Crie um formulário no Google Forms com os campos e validações especificados
   (títulos exatos incluídos no guia);
2. Ative “Receber respostas” e vincule a um Google Sheets (“Vincular às respostas”);
3. Configure a URL na variável `PUBLIC_GOOGLE_FORM_CADASTRO_URL` (local `.env`
   ou variável de ambiente no Cloudflare Pages).

Até a URL ser configurada, a página `/cadastrar/` exibe um aviso de
“formulário em configuração” — nunca um link inventado.

## 7. Como configurar a planilha Google Sheets

A planilha real já existe (aba “Respostas ao formulário 1”). As colunas
administrativas — STATUS, ATIVO, ID_PUBLICO, DATA_APROVACAO, DATA_ATUALIZACAO,
OBSERVACOES_INTERNAS — já fazem parte dela. A estrutura completa, coluna por
coluna, está em **[docs/GOOGLE_SHEETS_E_GOOGLE_CLOUD.md](docs/GOOGLE_SHEETS_E_GOOGLE_CLOUD.md)**;
o modelo em CSV é `scripts/modelo_planilha.csv`. A planilha permanece **privada**.

## 8. Como criar a conta de serviço no Google Cloud

Passo a passo (com telas) em **[docs/GOOGLE_SHEETS_E_GOOGLE_CLOUD.md](docs/GOOGLE_SHEETS_E_GOOGLE_CLOUD.md)**:
criar projeto → habilitar a Google Sheets API → criar conta de serviço → criar chave
JSON. A chave dá acesso **somente de leitura** à planilha compartilhada.

## 9. Como compartilhar a planilha com a conta de serviço

Na planilha, botão **Compartilhar** → informe o **e-mail da conta de serviço**
(`algo@projeto.iam.gserviceaccount.com) → permissão **Leitor**. Detalhes no mesmo
guia do item 8.

## 10. Como configurar os GitHub Secrets

Em **Settings → Secrets and variables → Actions** (detalhes em
[docs/GOOGLE_SHEETS_E_GOOGLE_CLOUD.md](docs/GOOGLE_SHEETS_E_GOOGLE_CLOUD.md)):

| Nome | Tipo | Uso |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Secret | JSON completo da conta de serviço |
| `PUBLIC_ID_SECRET` | Secret | `openssl rand -hex 32` — gera os IDs públicos (HMAC). Guarde para sempre |
| `CLOUDFLARE_DEPLOY_HOOK_URL` | Secret | (opcional) Deploy Hook do Cloudflare Pages |
| `GOOGLE_SHEET_ID` | Secret/Var | opcional — o workflow já tem o ID real como padrão |
| `GOOGLE_SHEET_TAB_NAME` | Variable | opcional — padrão “Respostas ao formulário 1” |
| `HABILITAR_PUBLICACAO` | Variable | **`SIM`** libera a gravação; qualquer outro valor = simulação |

Nenhum segredo vai para o código ou para o frontend.

## 11. Como funciona a aprovação de cadastros

- Todo cadastro novo entra com status **PENDENTE**;
- A moderação escreve `APROVADO`, `REJEITADO` ou `INATIVO` na coluna **STATUS**;
- **Regra obrigatória (fail-closed):** só é publicado o que for `STATUS=APROVADO`
  **e** `ATIVO=SIM` **e** tiver o consentimento válido (frase exata do
  formulário) **e** campos essenciais corretos — **campo vazio nunca aprova**;
- Alterações e exclusões na planilha refletem no site na próxima sincronização
  (no máximo 1 hora). Perfis desativados desaparecem da publicação seguinte.

Guia para não programadores: **[docs/GUIA_ADMINISTRATIVO.md](docs/GUIA_ADMINISTRATIVO.md)**.

## 12. Como executar a sincronização manualmente

```bash
# simulação com CSV exportado da planilha (nunca grava):
python scripts/sync_catalogo.py --csv planilha.csv --saida public/data --dry-run --verbose

# gravação local (exige PUBLIC_ID_SECRET):
npm run sync            # sync_catalogo.py --publicar

# contra o Google real, em simulação (usa variáveis de ambiente):
npm run sync:dry
```

Sem `--publicar` (ou com a variável do repositório diferente de `SIM`), o
modo Google **só simula** — trava de segurança da primeira publicação. O
sincronizador grava de forma **atômica** e **nunca sobrescreve** o catálogo
existente em falhas de autenticação, estrutura ou processamento. Sem mudanças
reais no conteúdo público, o arquivo não é reescrito (sem commits vazios).

## 13. Como configurar o GitHub Actions

O workflow **`sincronizar-profissionais.yml`** já existe:

- Roda a cada hora e via **Run workflow** (com opção **dry_run**);
- **Grava somente** quando a variável `HABILITAR_PUBLICACAO=SIM` e a execução
  não é simulação — antes disso, relata o que seria publicado sem gravar;
- Em modo gravação: sincroniza → valida JSON → testes → build → commit
  **apenas com mudança real** → push → **Deploy Hook** do Cloudflare Pages
  (se configurado; distingue “deploy solicitado” de “deploy concluído”);
- Permissões mínimas (`contents: write`), `concurrency` contra execuções
  simultâneas, sem acesso a segredos em pull requests;
- Commits com `GITHUB_TOKEN` não disparam outros workflows (limitação do
  GitHub) — por isso o próprio workflow testa e builda antes do commit.

Detalhes em **[docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md)**. Basta
configurar os Secrets do item 10 e habilitar Actions no repositório.

## 14. Como publicar no Cloudflare Pages

Guia completo em **[docs/CLOUDFLARE_PAGES.md](docs/CLOUDFLARE_PAGES.md)**. Resumo:

1. No Cloudflare: **Workers & Pages → Create → Pages → Connect to Git**;
2. Selecione o repositório e a branch `main`;
3. Build command: `npm run build` · Output directory: `dist` ·
   Node version (variável `NODE_VERSION`): `20`;
4. Salve: o primeiro deploy sai em `https://SEU-PROJETO.pages.dev`;
5. Cada push na `main` (inclusive o commit automático da sincronização)
   dispara nova publicação.

## 15. Como adicionar domínio próprio

Descrito em **[docs/CLOUDFLARE_PAGES.md](docs/CLOUDFLARE_PAGES.md#domínio-próprio)**:
Custom domains → Set up a custom domain → `www.seudominio.com.br` → ajustar DNS
(CNAME) → HTTPS automático. Depois, defina `PUBLIC_SITE_URL=https://www.seudominio.com.br`
nas variáveis de build do Pages para canonical/sitemap corretos. Nada no projeto
exige que o domínio já exista.

## 16. Como adicionar categorias de serviços

- **Listar na home/sugestões:** edite `src/config/categorias.ts` (nome, descrição
  e profissões sugeridas);
- **Categorias novas vindas da planilha:** qualquer categoria digitada no
  formulário gera automaticamente página (`/categoria/slug/`) e filtro — sem
  alterar código. O arquivo de configuração serve para apresentação e SEO.

## 17. Como atualizar o nome e a identidade visual

Tudo está centralizado:

| O quê | Onde |
|---|---|
| Nome do site | `srcConfig.nome` em `src/config/site.ts` |
| Cores, fonte, raios | variáveis CSS no topo de `src/styles/global.css` |
| Favicon/ícones | `public/favicon.svg` e SVGs nos componentes |
| Mensagem do WhatsApp | `siteConfig.mensagemWhatsApp` |
| Textos institucionais | páginas em `src/pages/` |

## 18. Como atender solicitações de alteração ou exclusão

Procedimento completo (incluindo verificação de legitimidade para exclusões e
troca de WhatsApp) em **[docs/SOLICITACOES_E_DENUNCIAS.md](docs/SOLICITACOES_E_DENUNCIAS.md)**.
Fluxo resumido: pedido pelo formulário/e-mail → verificação de que parte do
titular (WhatsApp cadastrado, e-mail administrativo ou verificação alternativa) →
alteração na planilha → publicação automática na próxima sincronização.

## 19. Como executar os testes

```bash
npm test                  # testes do site (Vitest): 72 testes
npm run test:python       # testes do sincronizador (pytest): 43 testes
npx astro check           # verificação de tipos TypeScript
npm run build             # build de produção (também roda no CI)
```

Cobertura: normalização sem acentos, combinação de filtros, validação de UF,
validação de WhatsApp e links wa.me, leitura/validação do JSON, filtragem de não
aprovados, exigência de consentimento, remoção de dados privados, duplicados,
atualização/desativação, falhas de autenticação, comportamento sem registros e build.

## 20. Como diagnosticar falhas de sincronização

1. **Actions → “Sincronizar catálogo”** → abra a execução com erro;
2. Mensagens comuns (o script nunca imprime dados pessoais):
   - `Cabeçalhos obrigatórios ausentes` → planilha sem as colunas administrativas
     (item 7) ou títulos renomeados;
   - `não foi possível consultar o Google Sheets` → credenciais/ID aba/compartilhamento
     (itens 8–10); o catálogo atual é preservado;
   - `O catálogo gerado é inválido` → registro com dados inconsistentes; os avisos
     indicam a **linha** e o motivo;
3. Rode `npm run sync:dry` localmente com um CSV exportado para reproduzir;
4. Para executar na hora: Actions → Sincronizar catálogo → **Run workflow**.

---

## Estado atual e pendências externas

O projeto está completo e funcional localmente (build, testes e preview
verificados, inclusive simulação de sincronização com a estrutura real da
planilha). A integração com o Google **não foi executada com credenciais
reais** — configure o seguinte para ativar:

- [ ] Criar conta de serviço no Google Cloud e compartilhar a planilha com ela (leitor);
- [ ] Secrets: `GOOGLE_SERVICE_ACCOUNT_JSON`, `PUBLIC_ID_SECRET` (`openssl rand -hex 32`)
      e, se quiser, `CLOUDFLARE_DEPLOY_HOOK_URL`;
- [ ] Rodar o workflow em simulação e conferir o cadastro de teste aprovado;
- [ ] Definir a variável `HABILITAR_PUBLICACAO=SIM` para liberar a gravação;
- [ ] Conectar o repositório ao Cloudflare Pages (build `npm run build`, saída `dist`);
- [ ] Definir `PUBLIC_SITE_URL` quando houver domínio próprio;
- [ ] Preencher os trechos `[PREENCHER: …]` de `/privacidade/` e `/termos/`.

## Segurança e privacidade — resumo

- Somente campos autorizados são exportados; e-mail administrativo, endereço
  comercial e observações **nunca** saem da planilha (testado em ambos os lados);
- Fail-closed em toda a cadeia: sem aprovação/consentimento/atividade não publica;
  JSON inválido reprova o CI; falha de sincronização preserva o catálogo atual;
- Escapes de HTML em toda renderização (proteção XSS) e validação/sanitização de
  todas as entradas; links externos com `rel="noopener noreferrer"`;
- Cabeçalhos de segurança em `public/_headers`; HTTPS automático no Pages;
- Nenhuma credencial no frontend; segredos apenas em GitHub Secrets;
- Sem rastreamento, sem cookies de publicidade, sem analytics invasivos.

## Licença e uso

Projeto próprio, sem dependências pagas. Ícones desenhados inline (SVG).
“WhatsApp” é marca de seus titulares; os links usam o formato público `wa.me`.
