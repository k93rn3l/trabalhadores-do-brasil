# Trabalhadores do Brasil

Catálogo público e gratuito de profissionais autônomos de todo o Brasil.
Qualquer visitante pesquisa por serviço, categoria, estado ou município e
fala diretamente com o profissional pelo WhatsApp — sem cadastro, sem taxa
e sem intermediação.

## Funcionalidades

- Busca nacional com filtros combináveis (texto, estado, município, categoria), indiferente a acentos;
- Páginas por profissional, categoria, estado e município;
- Contato direto por WhatsApp com mensagem inicial padrão;
- Layout leve, responsivo e acessível (prioridade para celular);
- Políticas de privacidade e termos alinhados à LGPD.

## Tecnologia

Site estático gerado com [Astro](https://astro.build), TypeScript, CSS e
JavaScript puros — sem banco de dados, sem backend em execução.

## Desenvolvimento

```bash
npm install        # dependências
npm run dev        # servidor local em http://localhost:4321
npm run build      # gera o site estático em dist/
npm run preview    # serve o build para conferência
npm test           # testes do site
```

Variáveis de ambiente opcionais (copie `.env.example` para `.env`):
`PUBLIC_SITE_URL` (domínio canônico) e URLs dos formulários externos.

## Publicação

O workflow `Sincronizar profissionais` gera o site no CI (a partir da
planilha privada), roda os testes e publica por **upload direto** no
Cloudflare Pages. O repositório guarda apenas código — nenhum dado pessoal
entra no histórico do git.

## Dados e privacidade (LGPD)

Dados pessoais **nunca são versionados**: `public/data/` (catálogo) e
`dados/` (estado operacional) são ignorados pelo git e uma guarda no CI
impede que sejam commitados. O catálogo é gerado em cada sincronização a
partir da planilha privada do Google Sheets e existe apenas no runner e no
site publicado; o estado de identidades/exclusões (pseudonimizado por HMAC)
fica no Cloudflare KV. Assim, a exclusão de um profissional remove o dado do
site de fato — sem cópias em histórico versionado. Para desenvolver
localmente com dados fictícios:

```bash
python scripts/sync_catalogo.py --csv scripts/modelo_planilha.csv --saida public/data --dir-dados dados --id-secret teste
```

Cadastros são publicados com consentimento explícito; a moderação atua por
exceção — veja a Política de Privacidade no próprio site (`/privacidade/`).
