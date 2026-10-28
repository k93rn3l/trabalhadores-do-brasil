# Publicação no Cloudflare Pages

O site é 100% estático (`dist/`), sem funções de borda nem requisitos especiais.

## 1. Conectar o repositório

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages** →
   **Create application → Pages → Connect to Git**;
2. Autorize o GitHub e selecione o repositório do catálogo;
3. Configure o projeto:

| Campo | Valor |
|---|---|
| Project name | `catalogo-profissionais` (vira `catalogo-profissionais.pages.dev`) |
| Production branch | `main` |
| Framework preset | `Astro` (ou None — os comandos abaixo mandam) |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | variável de ambiente `NODE_VERSION = 20` (item 2) |

4. **Save and Deploy**. O primeiro build sai em `https://SEU-PROJETO.pages.dev`.

A partir daí, **todo push na `main`** — incluindo o commit automático da
sincronização horária — publica uma nova versão. Pull requests geram previews
temporários em `*.preview.SEU-PROJETO.pages.dev`.

## 2. Variáveis de ambiente do build

Em **Settings → Environment variables** (Production e Preview):

| Variável | Obrigatória | Valor |
|---|---|---|
| `NODE_VERSION` | Sim | `20` |
| `PUBLIC_SITE_URL` | Recomendada com domínio próprio | `https://www.seudominio.com.br` |
| `PUBLIC_GOOGLE_FORM_CADASTRO_URL` | Para habilitar o cadastro | link do Forms |
| `PUBLIC_GOOGLE_FORM_ALTERACAO_URL` | Opcional | link do Forms de alteração |
| `PUBLIC_GOOGLE_FORM_DENUNCIA_URL` | Opcional | link do Forms de denúncia |
| `PUBLIC_CONTATO_EMAIL` | Opcional | e-mail institucional |

Se `PUBLIC_SITE_URL` ficar vazia, o build usa automaticamente a URL
`*.pages.dev` do ambiente (`CF_PAGES_URL`) para canonical, sitemap e robots.txt —
nada de domínio inventado.

## 3. O que já está pronto no projeto

- **`public/_headers`** — cabeçalhos de segurança (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`) e cache:
  imutável para assets com hash (`/_astro/*`) e sempre-revalidar para
  `/data/*` (dados frescos após a sincronização);
- **`public/_redirects`** — arquivo de redirecionamentos (comentado, para uso futuro);
- **`dist/404.html`** — página 404 amigável (o Pages a usa automaticamente);
- HTTPS automático e renovado em todos os domínios `*.pages.dev`.

## 4. Domínio próprio

Quando adquirir o domínio (ex.: `meudominio.com.br`):

1. Pages → seu projeto → **Custom domains → Set up a custom domain**;
2. Digite `www.meudominio.com.br`;
3. Se o DNS já estiver no Cloudflare, ele cria o `CNAME` automaticamente;
   fora do Cloudflare, aponte um CNAME para `SEU-PROJETO.pages.dev`;
4. Aguarde o certificado HTTPS ser emitido (minutos);
5. (Opcional) adicione também a raiz `meudominio.com.br` com redirecionamento
   para `www` — o Pages oferece isso na mesma tela;
6. Volte em **Environment variables** e defina
   `PUBLIC_SITE_URL=https://www.meudominio.com.br` + **Retry deployment** para
   canonical/sitemap/robots absolutos corretos.

Nada no código precisa mudar — o projeto nunca fixa um domínio.

## 5. Verificações pós-deploy

- Abra `https://SEU-PROJETO.pages.dev/` e confira nome, categorias e busca;
- `/cadastrar/` deve mostrar o botão (se a URL do Forms foi configurada);
- `/data/catalogo.json` deve retornar o mesmo conteúdo do repositório;
- `https://SEU-PROJETO.pages.dev/robots.txt` deve listar o sitemap
  (aparece quando `PUBLIC_SITE_URL` ou `CF_PAGES_URL` está definida);
- Pages → Deployments: cada sincronização aprovada gera um novo deployment.
