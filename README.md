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

O build gera um site 100% estático em `dist/`, pronto para qualquer
hospedagem de arquivos estáticos (por exemplo, Cloudflare Pages com comando
de build `npm run build` e diretório de saída `dist`).

## Dados e privacidade

O catálogo público fica em `public/data/`. Cadastros passam por revisão
humana e só são publicados com consentimento explícito do profissional —
veja a Política de Privacidade no próprio site (`/privacidade/`).
