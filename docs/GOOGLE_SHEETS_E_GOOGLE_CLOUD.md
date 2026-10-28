# Integração real: Google Sheets + Google Cloud + GitHub Secrets

Guia da integração em produção. O formulário e a planilha **já existem**:

- Formulário público: https://forms.gle/uKqyYZkaTpGTpepb7 (Cadastro de Profissionais Autônomos)
- Planilha privada: `1nxcIvRTlAf1HTXbNaeq6oo3gOJN8L52hbcL6NGzTk3M` — aba **“Respostas ao formulário 1”**

## 1. Estrutura real da planilha

| Coluna | Título | Uso |
|---|---|---|
| A | Carimbo de data/hora | Data de envio (Forms). Parte da identidade do ID público. |
| B | Nome profissional | Nome divulgado |
| C | Categoria | Divulgada |
| D | Profissão | Divulgada |
| E | Descrição do serviço | Divulgada |
| F | Estado (UF) | Formato “SP - São Paulo” — convertido internamente para sigla |
| G | Município | Divulgado |
| H | Bairros atendidos | Divulgado (lista separada por vírgula/ponto-e-vírgula) |
| I | Outros municípios atendidos | Divulgado |
| J | Atendimento remoto | Sim/Não |
| K | WhatsApp | Só dígitos (ex.: 19999990001) — normalizado para wa.me |
| L | E-mail administrativo | **Privado** — nunca publicado |
| M | Endereço comercial | **Privado** — a autorização atual não o inclui |
| N | Consentimento para publicação | Frase exata do formulário (ver §2) |
| O | ID_PUBLICO | Opcional: fixa o endereço público do perfil |
| P | STATUS | PENDENTE / APROVADO / REJEITADO / INATIVO |
| Q | ATIVO | **SIM** / NÃO — vazio NÃO publica |
| R | DATA_APROVACAO | dd/mm/aaaa |
| S | DATA_ATUALIZACAO | preencha ao editar o cadastro |
| T | OBSERVACOES_INTERNAS | **Privado** — nunca publicado |

O sincronizador identifica colunas **pelo nome normalizado** (minúsculo, sem
acento, espaços extras removidos, underscore = espaço), nunca por posição.
Espaços extras nos títulos (ex.: “ Categoria ”) são aceitos.

## 2. Regras de publicação (fail-closed)

Um cadastro só entra no catálogo quando **todos** forem verdadeiros:

1. `STATUS` = **APROVADO**;
2. `ATIVO` = **SIM** (campo vazio nunca é interpreta como aprovação);
3. `Consentimento para publicação` = a frase exata do formulário:
   “Li as informações sobre o uso dos meus dados pessoais e autorizo a
   divulgação pública dos dados profissionais indicados.” Textos arbitrários
   **não** são aceitos;
4. Nome, categoria, profissão, descrição, município preenchidos;
5. Estado válido (aceita “SP - São Paulo”, “SP” ou “São Paulo”);
6. WhatsApp celular válido com DDD.

A exportação é por **allowlist**: apenas os campos autorizados saem
(id, nome, categoria, profissão, descrição, uf, estado, município, bairros,
outros municípios, atendimento remoto, whatsapp, data pública). E-mail,
endereço comercial, observações e status administrativos ficam na planilha.

Duplicidades: mesmo `ID_PUBLICO`, ou mesma combinação WhatsApp+profissão+
município publicam apenas a versão mais recente (com aviso no log).

## 3. IDs públicos

- `ID_PUBLICO` preenchido e válido → usado como está (slug: a–z, 0–9, hífen);
- vazio → `HMAC-SHA256(PUBLIC_ID_SECRET, carimbo|whatsapp)` truncado —
  determinístico, estável enquanto o segredo (e o carimbo/telefone) não mudarem,
  e sem expor telefone nem carimbo;
- **Atenção:** se o telefone mudar com ID_PUBLICO vazio, a URL pública muda.
  Para profissionais que divulgaram o link, preencha o `ID_PUBLICO` antes da
  troca.

## 4. Conta de serviço (Google Cloud)

1. [console.cloud.google.com](https://console.cloud.google.com) → crie/abra o projeto;
2. **APIs e serviços → Biblioteca** → **Google Sheets API** → Ativar;
3. **IAM → Contas de serviço → Criar**: nome `sincronizador` → sem função → concluir;
4. Abra a conta → **Chaves → Adicionar chave → JSON** → baixe o arquivo.

## 5. Compartilhar a planilha (somente leitura)

1. No JSON da chave, copie o `client_email` (@...iam.gserviceaccount.com);
2. Na planilha → **Compartilhar** → cole o e-mail → papel **Leitor** → enviar.

## 6. GitHub Secrets e Variables

**Settings → Secrets and variables → Actions:**

| Onde | Nome | Valor |
|---|---|---|
| Secret | `GOOGLE_SERVICE_ACCOUNT_JSON` | conteúdo completo do JSON da chave |
| Secret | `PUBLIC_ID_SECRET` | `openssl rand -hex 32` (gere uma vez e **guarde**: trocar muda os IDs) |
| Secret | `CLOUDFLARE_DEPLOY_HOOK_URL` | (opcional) URL do Deploy Hook do Pages |
| Secret/Variable | `GOOGLE_SHEET_ID` | opcional — o workflow já tem o ID real como padrão |
| Variable | `GOOGLE_SHEET_TAB_NAME` | opcional — padrão `Respostas ao formulário 1` |
| Variable | `HABILITAR_PUBLICACAO` | **`SIM`** habilita a gravação; qualquer outro valor = simulação |

## 7. Primeira sincronização (runbook)

1. Configure os Secrets/Variables acima (exceto `HABILITAR_PUBLICACAO`);
2. GitHub → **Actions → Sincronizar profissionais → Run workflow** (sem marcar
   dry-run): com `HABILITAR_PUBLICACAO` vazio, roda em **SIMULAÇÃO** e imprime
   o resumo — linhas lidas, elegíveis, pendentes, rejeitados, motivos;
3. Confira se o cadastro de teste aprovado aparece como “elegíveis: 1”;
4. Quando estiver satisfeito, defina a variável `HABILITAR_PUBLICACAO=SIM`;
5. Rode o workflow novamente: agora ele grava `public/data/profissionais.json`,
   valida, testa, builda e faz commit (o Deploy Hook/Cloudflare publica).

## 8. Executar localmente

```bash
# simulação com CSV exportado da planilha (Arquivo > Fazer download > CSV):
python scripts/sync_catalogo.py --csv planilha.csv --saida public/data --dry-run --verbose

# gravação local (exige PUBLIC_ID_SECRET):
python scripts/sync_catalogo.py --csv planilha.csv --saida public/data \
  --id-secret $(openssl rand -hex 32 ... use o SEGREDO OFICIAL) --publicar

# contra o Google real (usa GOOGLE_SHEET_ID/GOOGLE_SERVICE_ACCOUNT_JSON do ambiente):
python scripts/sync_catalogo.py --credenciais-arquivo chave.json --dry-run --verbose
```

Até `--publicar` ser usado (ou a variável do repositório ser `SIM`), nada é
gravado — por construção, a primeira publicação nunca acontece sem revisão.

## 9. Falhas comuns

| Mensagem | Causa provável |
|---|---|
| `não foi possível consultar o Google Sheets` | JSON inválido, planilha não compartilhada com a conta de serviço, ID/aba errados |
| `Cabeçalhos obrigatórios ausentes` | aba errada ou títulos renomeados |
| `PUBLIC_ID_SECRET não configurado` | gere com `openssl rand -hex 32` e salve no Secret |
| `APROVADO sem consentimento válido` | resposta da coluna N não é a frase exata do formulário |
| `ATIVO não é SIM` | preencha SIM explicitamente (vazio não publica) |

Em qualquer falha, o catálogo atual permanece publicado (fail-closed).
