# Como configurar o Google Forms de cadastro

Este guia cria o formulário oficial de cadastro de profissionais. Os **títulos das
perguntas importam**: o sincronizador reconhece os cabeçalhos da planilha por
nome normalizado (sem acentos, minúsculas). Use os títulos exatos abaixo.

## 1. Criar o formulário

1. Acesse [forms.google.com](https://forms.google.com) → **Formulário em branco**;
2. Renomeie o formulário para **“Cadastro de profissional — Profissionais Progressistas”**;
3. Em **Configurações → Respostas**, deixe “Coletar e-mails” **desativado**
   (pediremos o e-mail como pergunta normal, para deixar claro que é administrativo);
4. Não exija login: em “Restringir aos usuários”, escolha **qualquer pessoa com o link**.

## 2. Perguntas (na ordem, com os títulos exatos)

| # | Título da pergunta | Tipo | Obrigatória | Opções / validação |
|---|---|---|---|---|
| 1 | **Nome público** | Resposta curta | Sim | Descrição: “Nome que deve aparecer no catálogo (seu nome ou nome comercial).” |
| 2 | **Categoria** | Lista suspensa | Sim | As categorias de `src/config/categorias.ts` (ver abaixo) |
| 3 | **Profissão** | Resposta curta | Sim | Descrição: “Ex.: Eletricista residencial, Diarista, Cabelereira…” |
| 4 | **Descrição do serviço** | Parágrafo | Sim | Máx. 2.000 caracteres |
| 5 | **UF** | Lista suspensa | Sim | As 27 siglas (AC…TO) |
| 6 | **Município** | Resposta curta | Sim | Descrição: “Cidade principal de atendimento.” |
| 7 | **Bairros atendidos** | Resposta curta | Não | Descrição: “Separe por vírgula. Ex.: Centro, Taquaral” |
| 8 | **Outros municípios atendidos** | Resposta curta | Não | Separe por vírgula |
| 9 | **Atendimento remoto** | Múltipla escolha | Não | Única opção: “Sim” |
| 10 | **WhatsApp** | Resposta curta | Sim | Descrição: “Número de celular com DDD. Ex.: (11) 99999-8888”. O Forms não valida telefone; o sincronizador valida e recusa números inválidos. |
| 11 | **E-mail administrativo** | Resposta curta | Sim | Descrição: “Não será publicado. Usado apenas para contato sobre seu cadastro.” + validação de e-mail |
| 12 | **Endereço comercial** | Resposta curta | Não | Descrição: “Opcional. Não é publicado; ajuda a moderação a localizar o cadastro.” |
| 13 | **Consentimento** | Múltipla escolha | Sim | Única opção: “Sim, Autorizo a publicação dos dados informados.” (ver nota) |

> **Nota sobre o campo WhatsApp:** o Google Forms não tem validação de telefone
> confiável. O sincronizador valida o número e **recusa o registro** (com aviso
> na linha correspondente) se não for celular brasileiro válido. Orientar o
> formato no campo de descrição reduz erros.

### Opções da pergunta “Categoria” (copie e cole)

```
Construção e reformas
Serviços domésticos
Manutenção residencial
Instalações elétricas
Hidráulica
Tecnologia e informática
Educação e aulas particulares
Beleza e estética
Jardinagem
Transporte e mudanças
Costura e confecção
Serviços automotivos
Eventos
Serviços administrativos
Serviços profissionais especializados
Outros serviços
```

Adicionar uma opção aqui não altera o código: qualquer valor novo gera página e
filtro automaticamente. Para exibir a categoria na home com descrição, adicione-a
também em `src/config/categorias.ts`.

### Opções da pergunta “Consentimento”

Uma única opção, exatamente:

```
Sim, Autorizo a publicação dos dados informados.
```

Tornando-a obrigatória, ninguém envia sem marcar. O sincronizador aceita
qualquer valor que comece com “sim”/“autorizo”; “não” ou vazio **bloqueia a
publicação**.

## 3. Aviso de privacidade no formulário

Na **descrição do formulário** (topo), inclua um texto como:

> Ao enviar este cadastro, você autoriza a publicação no catálogo público dos
> seguintes dados: nome público, categoria, profissão, descrição, UF, município,
> bairros/municípios atendidos, atendimento remoto e WhatsApp. Seu e-mail e
> endereço comercial NÃO são publicados. Não pedimos CPF, RG ou endereço
> residencial. Você pode solicitar correção ou exclusão a qualquer momento.
> Consulte a Política de Privacidade do site.

## 4. Vincular ao Google Sheets

1. Aba **Respostas → ícone de planilha (Vincular às respostas)**;
2. “Criar uma planilha” → nome sugerido: “Cadastros — Profissionais Progressistas”;
3. Pronto: cada resposta virará uma linha na aba **“Respostas de formulário 1”**.

Continue em **[GOOGLE_SHEETS_E_GOOGLE_CLOUD.md](GOOGLE_SHEETS_E_GOOGLE_CLOUD.md)**
para adicionar as colunas administrativas e a conta de serviço.

## 5. Ativar o botão no site

1. Copie o link de envio do formulário (botão **Enviar → ícone de link**);
2. Configure a variável de ambiente:
   - Local: crie `.env` com `PUBLIC_GOOGLE_FORM_CADASTRO_URL=https://docs.google.com/forms/...`;
   - Cloudflare Pages: Settings → Environment variables → mesmo nome (produção e preview);
3. Pronto: a página `/cadastrar/` passa a exibir o botão de abertura.

Sem a variável, a página mostra o aviso “formulário ainda não configurado” —
comportamento proposital para nunca exibir um link quebrado.

## 6. Formulários opcionais (alteração/exclusão e denúncia)

Crie dois formulários curtos, se desejar usá-los:

- **“Solicitação de alteração/exclusão de cadastro”**: Nome publicado, WhatsApp
  publicado, E-mail administrativo do cadastro, Tipo de solicitação (lista:
  correção / troca de WhatsApp / mudança de região / desativação temporária /
  exclusão), Detalhes.
- **“Denúncia de cadastro”**: Link ou código do perfil, Motivo (lista: número
  incorreto / informação enganosa / duplicado / uso indevido de dados / outro),
  Descrição, Contato para retorno (opcional).

Configure as variáveis `PUBLIC_GOOGLE_FORM_ALTERACAO_URL` e
`PUBLIC_GOOGLE_FORM_DENUNCIA_URL` para ativá-los. Sem elas, as páginas usam o
e-mail institucional como canal (ou exibem aviso).
