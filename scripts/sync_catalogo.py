#!/usr/bin/env python3
"""
Sincronizador: Google Sheets (privado) -> catálogo público JSON.

Modelo: **publicação automática com moderação por exceção**.

Identidade administrativa: e-mail verificado coletado pelo Google Forms
(uma resposta por conta). O e-mail nunca é publicado. Dele deriva um hash
pseudonimizado (HMAC) usado para vincular IDs públicos estáveis — trocar o
telefone não muda a URL do perfil, e outro cadastro não consegue se apropriar
de um ID alheio (o vínculo é por identidade, não por telefone).

Decisão por linha:
  - STATUS vazio ........ publica automaticamente (dados válidos + consentimento)
  - STATUS=APROVADO ..... publica e LIBERA de retenção por suspeita (chancela admin)
  - STATUS=PENDENTE ..... retido para revisão manual
  - STATUS=REJEITADO/INATIVO ou ATIVO=NÃO .... BLOQUEADO de forma persistente
    (a edição da resposta no Forms não reativa: colunas administrativas permanecem)

Moderação por exceção — sinais FORTES retêm automaticamente (indício real de
abuso); sinais FRACOS apenas sinalizam (não retêm profissionais legítimos):
  fortes : sem nenhum e-mail utilizável; link no nome; telefone em 3+ contas.
  fracos : nome de uma palavra; descrição curta; link na descrição.

Relatório de moderação: `dados/relatorio-moderacao.json` (sem dados pessoais —
apenas linha, motivo e contagens) gerado em toda execução, para consulta da
fila de retidos/bloqueios sem backend e sem permissão de escrita na planilha.

Mapa de identidades: `dados/identidades.json` (hash->id; pseudonimizado),
versionado junto com o catálogo para garantir IDs estáveis entre execuções.
"""

from __future__ import annotations

import argparse
import csv as csv_modulo
import hashlib
import hmac
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSAO_CATALOGO = 1
ARQUIVO_PRINCIPAL = "profissionais.json"
ABA_PADRAO = "Respostas ao formulário 1"

CONSENTIMENTO_ESPERADO = (
    "li as informacoes sobre o uso dos meus dados pessoais e autorizo "
    "a divulgacao publica dos dados profissionais indicados"
)

TELEFONE_COMPARTILHADO_LIMITE = 3      # sinal FORTE
TAMANHO_DESCRICAO_FRACA = 15           # sinal FRACO (não retém)

UFS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}

# Allowlist exata do JSON público — nada além disto sai da planilha.
CAMPOS_PUBLICOS = (
    "id", "nome", "categoria", "categoriaSlug", "profissao", "descricao",
    "uf", "estado", "municipio", "municipioSlug", "bairros",
    "outros_municipios", "atendimento_remoto", "whatsapp", "atualizadoEm",
)

# Chaves que JAMAIS podem aparecer em um registro público.
CHAVES_PROIBIDAS = {
    "email", "emails", "emailVerificado", "email_verificado",
    "emailAdministrativo", "email_administrativo",
    "endereco", "enderecoComercial", "endereco_comercial",
    "observacoes", "observacoesInternas", "observacoes_internas",
    "status", "ativo", "consentimento", "consentimento_para_publicacao",
    "id_publico", "timestamp", "carimbo", "data_aprovacao", "dataAprovacao",
    "data_atualizacao", "credenciais", "google", "identidade",
}

REGEX_WHATSAPP = re.compile(r"^55[1-9][0-9]9[0-9]{8}$")
REGEX_ID = re.compile(r"^[a-z0-9-]{4,64}$")
REGEX_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REGEX_LINK = re.compile(r"(https?://|www\.)", re.IGNORECASE)

COLUNAS: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "carimbo de data/hora", "carimbo de data hora",
                  "data de envio", "data"),
    "email_verificado": ("email", "e-mail", "email verificado",
                         "endereco de email"),
    "nome": ("nome profissional", "nome publico",
             "nome publico do profissional ou nome comercial",
             "nome do profissional", "nome"),
    "categoria": ("categoria", "categoria de servico", "area"),
    "profissao": ("profissao", "profissao ou tipo de servico", "servico", "tipo de servico"),
    "descricao": ("descricao", "descricao do servico", "sobre o servico"),
    "uf": ("estado (uf)", "uf", "estado", "unidade federativa"),
    "municipio": ("municipio", "cidade"),
    "bairros": ("bairros atendidos", "bairros", "regioes atendidas", "regiao atendida"),
    "outros_municipios": ("outros municipios atendidos", "municipios atendidos",
                          "outras cidades atendidas"),
    "remoto": ("atendimento remoto", "remoto", "atende remoto"),
    "whatsapp": ("whatsapp", "whatsapp profissional", "numero whatsapp",
                 "numero de whatsapp", "zap"),
    "email_administrativo": ("email administrativo", "e-mail administrativo"),
    "endereco": ("endereco comercial", "endereco"),
    "consentimento": ("consentimento para publicacao", "consentimento publicacao",
                      "consentimento", "autorizacao", "autorizo a publicacao"),
    "id": ("id publico", "id", "identificador", "identificador unico"),
    "status": ("status", "situacao"),
    "data_aprovacao": ("data de aprovacao", "data aprovacao", "data_aprovacao", "aprovado em"),
    "data_atualizacao": ("ultima atualizacao", "data da ultima atualizacao",
                         "data_atualizacao", "atualizado em"),
    "observacoes": ("observacoes internas", "observacoes", "notas"),
    "ativo": ("ativo", "cadastro ativo", "situacao de atividade", "atividade"),
}

COLUNAS_OBRIGATORIAS = ("timestamp", "nome", "categoria", "profissao", "descricao",
                        "uf", "municipio", "whatsapp", "consentimento", "status", "ativo")


class ErroColunas(Exception):
    """Cabeçalhos da planilha não correspondem ao esperado."""


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def normalizar_texto(valor: str) -> str:
    decomposto = unicodedata.normalize("NFD", valor)
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    texto = sem_acentos.lower().replace("_", " ")
    return re.sub(r"\s+", " ", texto).strip()


def slug(valor: str) -> str:
    texto = normalizar_texto(valor)
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-{2,}", "-", texto).strip("-")
    return texto[:80].rstrip("-")


def limpar_celula(valor: Any) -> str:
    if valor is None:
        return ""
    texto = re.sub(r"[\x00-\x1f\x7f]+", " ", str(valor))
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_email(valor: str) -> str:
    email = limpar_celula(valor).lower()
    return email if REGEX_EMAIL.match(email) else ""


def identidade_email(dados: dict[str, str]) -> str:
    """E-mail usado como identidade: o verificado; senão, o administrativo."""
    return normalizar_email(dados.get("email_verificado", "")) or \
        normalizar_email(dados.get("email_administrativo", ""))


def normalizar_uf(valor: str) -> str | None:
    limpo = re.sub(r"[^a-z ]", " ", normalizar_texto(valor)).strip()
    if not limpo:
        return None
    partes = limpo.split()
    siglas_minusculas = {sigla.lower() for sigla in UFS}
    if partes[0] in siglas_minusculas:
        return partes[0].upper()
    nomes = {normalizar_texto(nome): sigla for sigla, nome in UFS.items()}
    return nomes.get(limpo)


def normalizar_whatsapp(valor: str) -> str | None:
    digitos = re.sub(r"\D", "", valor or "")
    if not digitos:
        return None
    digitos = digitos.lstrip("0")
    if len(digitos) == 13 and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) != 11:
        return None
    ddd = int(digitos[:2])
    if not (11 <= ddd <= 99):
        return None
    if not digitos[2] == "9":
        return None
    if len(set(digitos)) == 1:
        return None
    return "55" + digitos


def afirmativo(valor: str) -> bool:
    texto = normalizar_texto(valor)
    return bool(
        texto.startswith("sim")
        or texto in {"true", "x", "ok", "autorizo", "aceito", "concordo"}
        or texto.startswith("autorizo")
        or texto.startswith("aceito")
    )


def consentimento_valido(valor: str) -> bool:
    """Somente a frase exata do formulário (ou forma curta inequívoca)."""
    texto = normalizar_texto(valor).rstrip(".")
    if not texto:
        return False
    if texto == CONSENTIMENTO_ESPERADO.rstrip("."):
        return True
    return texto.startswith("sim, autorizo") or texto.startswith("autorizo a publicacao")


def parse_data(valor: str) -> date | None:
    texto = limpar_celula(valor)
    if not texto:
        return None
    texto = texto.split(" ")[0]
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def dividir_lista(valor: str, maximo_itens: int = 15) -> list[str]:
    texto = limpar_celula(valor)
    if not texto:
        return []
    itens: list[str] = []
    for parte in re.split(r"[;,]", texto):
        item = parte.strip()[:120]
        if item and item.lower() not in {i.lower() for i in itens}:
            itens.append(item)
    return itens[:maximo_itens]


# ---------------------------------------------------------------------------
# Leitura da planilha
# ---------------------------------------------------------------------------

def mapa_colunas(cabecalho: list[str]) -> dict[str, int]:
    mapa: dict[str, int] = {}
    for indice, titulo in enumerate(cabecalho):
        chave = normalizar_texto(limpar_celula(titulo))
        if not chave:
            continue
        for nome_interno, aliases in COLUNAS.items():
            if chave in aliases or chave == nome_interno:
                if nome_interno in mapa:
                    raise ErroColunas(
                        f"A coluna interna '{nome_interno}' aparece mais de uma vez "
                        f"(posições {mapa[nome_interno] + 1} e {indice + 1})."
                    )
                mapa[nome_interno] = indice
                break
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in mapa]
    if faltando:
        raise ErroColunas(
            "Cabeçalhos obrigatórios ausentes na planilha: "
            + ", ".join(sorted(faltando))
            + ". Verifique a aba e os títulos das colunas."
        )
    return mapa


def linha_para_dicionario(linha: list[str], mapa: dict[str, int]) -> dict[str, str]:
    return {
        chave: limpar_celula(linha[indice] if indice < len(linha) else "")
        for chave, indice in mapa.items()
    }


def buscar_linhas_google(planilha_id: str, aba: str, credenciais_json: str) -> list[list[str]]:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as erro:
        raise RuntimeError(
            "Dependências do Google não instaladas. Execute: "
            "pip install -r scripts/requirements.txt"
        ) from erro

    info = json.loads(credenciais_json)
    credenciais = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    servico = build("sheets", "v4", credentials=credenciais, cache_discovery=False)
    resultado = (
        servico.spreadsheets()
        .values()
        .get(spreadsheetId=planilha_id, range=aba)
        .execute()
    )
    return resultado.get("values", [])


def ler_csv(caminho: str) -> list[list[str]]:
    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        return [linha for linha in csv_modulo.reader(arquivo)]


# ---------------------------------------------------------------------------
# Identificadores públicos estáveis
# ---------------------------------------------------------------------------

def _hmac(segredo: str, dominio: str, valor: str) -> str:
    return hmac.new(segredo.encode("utf-8"), f"{dominio}|{valor}".encode("utf-8"),
                    hashlib.sha256).hexdigest()[:16]


def resolver_id_publico(
    dados: dict[str, str],
    email: str,
    whatsapp: str,
    segredo: str,
    mapa_identidades: dict[str, str],
    ids_publicados_por_telefone: dict[str, list[str]],
) -> tuple[str, tuple[str, str] | None]:
    """Resolve o ID público e o vínculo (hash de identidade -> id) a registrar.

    Prioridade: ID_PUBLICO persistente > vínculo existente por identidade >
    migração única por telefone (somente se o ID publicado ainda não estiver
    vinculado a outra identidade — impede apropriação de URL) > ID derivado
    determinístico da identidade. O vínculo por identidade garante que trocar
    o telefone não altera a URL do perfil.
    """
    id_manual = slug(dados.get("id", ""))
    if REGEX_ID.match(id_manual):
        return id_manual, None

    hash_identidade = _hmac(segredo, "identidade", email)
    if hash_identidade in mapa_identidades:
        return mapa_identidades[hash_identidade], None

    derivado = _hmac(segredo, "id", email)
    vinculados = set(mapa_identidades.values())
    publicados = ids_publicados_por_telefone.get(whatsapp, [])
    if len(publicados) == 1 and publicados[0] not in vinculados and publicados[0] != derivado:
        # Migração de perfil publicado antes do mapa: mantém a URL atual.
        return publicados[0], (hash_identidade, publicados[0])
    return derivado, (hash_identidade, derivado)


# ---------------------------------------------------------------------------
# Classificação e sinais de moderação
# ---------------------------------------------------------------------------

def classificar_status(status: str) -> str:
    """-> 'auto' | 'aprovado' | 'pendente' | 'bloqueado'"""
    status = status.strip().upper()
    if status == "":
        return "auto"
    if status == "APROVADO":
        return "aprovado"
    if status == "PENDENTE":
        return "pendente"
    if status in {"REJEITADO", "INATIVO"}:
        return "bloqueado"
    return "pendente"  # valor desconhecido: retido por segurança


def ativo_bloqueia(valor: str) -> bool:
    texto = normalizar_texto(valor)
    return texto.startswith("nao") or texto in {"inativo", "false", "0", "n"}


def motivos_suspeita(dados: dict[str, str], telefone_contas: int) -> list[str]:
    """Sinais FORTES: indício real de abuso/impersonação — retêm o registro.
    Filtros automáticos não garantem ausência de fraudes; são apenas triagem."""
    motivos: list[str] = []
    if not identidade_email(dados):
        motivos.append("sem e-mail utilizável (identidade administrativa)")
    if REGEX_LINK.search(dados.get("nome", "") or ""):
        motivos.append("link no nome do profissional")
    if telefone_contas >= TELEFONE_COMPARTILHADO_LIMITE:
        motivos.append(f"mesmo telefone em {telefone_contas} contas distintas")
    return motivos


def sinais_fracos(dados: dict[str, str]) -> list[str]:
    """Sinais FRACOS: não retêm profissionais legítimos — apenas sinalizam
    para a moderação revisar (nomes artísticos/comerciais curtos, portfólios)."""
    sinais: list[str] = []
    if " " not in dados.get("nome", "").strip():
        sinais.append("nome de uma palavra (pode ser nome artístico)")
    if len(limpar_celula(dados.get("descricao", ""))) < TAMANHO_DESCRICAO_FRACA:
        sinais.append("descrição curta")
    if REGEX_LINK.search(dados.get("descricao", "") or ""):
        sinais.append("link na descrição (portfólio)")
    return sinais


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------

def processar_linha(
    dados: dict[str, str],
    numero_linha: int,
    avisos: list[str],
    eventos: dict[str, list[dict[str, Any]]],
    segredo: str,
    mapa_identidades: dict[str, str],
    ids_publicados_por_telefone: dict[str, list[str]],
    telefone_contas: int,
) -> tuple[dict[str, Any] | None, str, tuple[str, str] | None]:
    """Retorna (registro|None, desfecho, vinculo_identidade|None)."""
    def avisar(motivo: str) -> None:
        avisos.append(f"linha {numero_linha}: {motivo}")

    if not any(dados.values()):
        return None, "vazia", None

    situacao = classificar_status(dados.get("status", ""))
    if situacao == "bloqueado" or ativo_bloqueia(dados.get("ativo", "")):
        motivo = "STATUS=" + (dados.get("status", "").strip().upper() or "?")
        if ativo_bloqueia(dados.get("ativo", "")):
            motivo = "ATIVO=NÃO"
        eventos["bloqueados"].append({"linha": numero_linha, "motivo": motivo})
        return None, "bloqueado", None  # edição do Forms não reativa

    if situacao == "pendente":
        motivo = "STATUS=PENDENTE" if dados.get("status", "").strip() else "STATUS desconhecido"
        avisar(f"retido: {motivo} (revisão manual)")
        eventos["pendentes"].append({"linha": numero_linha, "motivo": motivo})
        return None, "pendente", None

    # --- Validações essenciais (registro inválido nunca publica) ---
    email = identidade_email(dados)
    whatsapp = normalizar_whatsapp(dados.get("whatsapp", ""))
    uf = normalizar_uf(dados.get("uf", ""))
    municipio = dados.get("municipio", "")[:120]
    nome = dados.get("nome", "")[:160]
    categoria = dados.get("categoria", "")[:120]
    profissao = dados.get("profissao", "")[:120]
    descricao = dados.get("descricao", "")[:2000]

    invalidos: list[str] = []
    if whatsapp is None:
        invalidos.append("WhatsApp inválido")
    if uf is None:
        invalidos.append("Estado/UF inválido")
    if not municipio:
        invalidos.append("Município vazio")
    if not nome or not categoria or not profissao or not descricao:
        invalidos.append("campo essencial vazio")
    if not consentimento_valido(dados.get("consentimento", "")):
        invalidos.append("consentimento inválido")
    data_referencia = (
        parse_data(dados.get("data_atualizacao", ""))
        or parse_data(dados.get("data_aprovacao", ""))
        or parse_data(dados.get("timestamp", ""))
    )
    if data_referencia is None:
        invalidos.append("sem data utilizável")
    categoria_slug = slug(categoria)
    municipio_slug = slug(municipio)
    if (categoria and not categoria_slug) or (municipio and not municipio_slug):
        invalidos.append("categoria/município sem texto utilizável")

    if invalidos:
        avisar("inválido — " + "; ".join(invalidos) + " — não publicado")
        eventos["invalidos"].append({"linha": numero_linha, "motivos": invalidos})
        return None, "invalido", None

    # --- Sinais: fortes retêm; fracos apenas sinalizam ---
    fortes = motivos_suspeita(dados, telefone_contas)
    if situacao == "auto" and fortes:
        avisar("retido para revisão: " + "; ".join(fortes))
        eventos["retidos"].append({"linha": numero_linha, "motivos": fortes})
        return None, "retido", None

    for sinal in sinais_fracos(dados):
        avisos.append(f"linha {numero_linha}: sinal fraco (publicado) — {sinal}")
        eventos["sinais_fracos"].append({"linha": numero_linha, "sinal": sinal})

    id_publico, vinculo = resolver_id_publico(
        dados, email, whatsapp, segredo, mapa_identidades, ids_publicados_por_telefone
    )
    registro = {
        "id": id_publico,
        "nome": nome,
        "categoria": categoria,
        "categoriaSlug": categoria_slug,
        "profissao": profissao,
        "descricao": descricao,
        "uf": uf,
        "estado": UFS[uf],
        "municipio": municipio,
        "municipioSlug": municipio_slug,
        "bairros": dividir_lista(dados.get("bairros", "")),
        "outros_municipios": dividir_lista(dados.get("outros_municipios", "")),
        "atendimento_remoto": afirmativo(dados.get("remoto", "")),
        "whatsapp": whatsapp,
        "atualizadoEm": data_referencia.isoformat(),
    }
    return registro, "publicado", vinculo


def _prioridade(dados: dict[str, str], indice: int) -> tuple:
    return (
        parse_data(dados.get("data_aprovacao", "")) or date.min,
        parse_data(dados.get("timestamp", "")) or date.min,
        indice,
    )


def montar_catalogo(
    linhas: list[list[str]],
    mapa: dict[str, int],
    segredo: str,
    mapa_identidades: dict[str, str] | None = None,
    ids_publicados_por_telefone: dict[str, list[str]] | None = None,
) -> tuple[dict[str, Any], dict[str, int], list[str], dict[str, str], dict[str, list[dict[str, Any]]]]:
    """Retorna (catálogo, contagem, avisos, mapa de identidades, eventos de moderação)."""
    mapa_identidades = dict(mapa_identidades or {})
    ids_publicados_por_telefone = ids_publicados_por_telefone or {}
    avisos: list[str] = []
    eventos: dict[str, list[dict[str, Any]]] = {
        "retidos": [], "pendentes": [], "bloqueados": [],
        "invalidos": [], "sinais_fracos": [],
    }
    contagem = {
        "linhas": 0, "publicados": 0, "retidos": 0, "pendentes": 0,
        "bloqueados": 0, "invalidos": 0, "duplicados": 0,
    }

    todas = []
    for indice, linha in enumerate(linhas):
        dados = linha_para_dicionario(linha, mapa)
        if not any(dados.values()):
            continue
        todas.append((indice, indice + 2, dados))

    # Pré-passo: contas distintas por telefone (sinal forte).
    contas_por_telefone: dict[str, set[str]] = {}
    for indice, _, dados in todas:
        whatsapp = normalizar_whatsapp(dados.get("whatsapp", ""))
        if whatsapp:
            identidade = identidade_email(dados) or f"linha:{indice}"
            contas_por_telefone.setdefault(whatsapp, set()).add(identidade)

    por_id: dict[str, tuple[dict[str, Any], tuple]] = {}
    por_email: dict[str, tuple[dict[str, Any], tuple]] = {}

    for indice, numero_linha, dados in todas:
        contagem["linhas"] += 1
        whatsapp_normalizado = normalizar_whatsapp(dados.get("whatsapp", ""))
        telefone_contas = len(contas_por_telefone.get(whatsapp_normalizado, set())) \
            if whatsapp_normalizado else 0

        registro, desfecho, vinculo = processar_linha(
            dados, numero_linha, avisos, eventos, segredo,
            mapa_identidades, ids_publicados_por_telefone, telefone_contas,
        )

        if registro is None:
            if desfecho in ("retido", "pendente", "bloqueado", "invalido"):
                contagem[desfecho + "s"] += 1
            continue

        if vinculo:
            hash_identidade, id_vinculado = vinculo
            mapa_identidades[hash_identidade] = id_vinculado

        prioridade = _prioridade(dados, indice)

        # Duplicação por identidade (mesma conta): vale a versão mais recente.
        email = identidade_email(dados)
        if email and email in por_email:
            contagem["duplicados"] += 1
            avisos.append(f"linha {numero_linha}: identidade duplicada — mantida a versão mais recente")
            if prioridade >= por_email[email][1]:
                antiga = por_email[email][0]
                por_email[email] = (registro, prioridade)
                por_id.pop(antiga["id"], None)
                por_id[registro["id"]] = (registro, prioridade)
            continue
        if email:
            por_email[email] = (registro, prioridade)

        if registro["id"] in por_id:
            contagem["duplicados"] += 1
            avisos.append(f"linha {numero_linha}: ID duplicado — mantida a versão mais recente")
            if prioridade >= por_id[registro["id"]][1]:
                por_id[registro["id"]] = (registro, prioridade)
        else:
            por_id[registro["id"]] = (registro, prioridade)

    # Duplicação por WhatsApp+profissão+município (contas distintas, mesmo anúncio).
    por_combinacao: dict[tuple, tuple[dict[str, Any], tuple]] = {}
    for registro, prioridade in por_id.values():
        chave = (
            registro["whatsapp"],
            normalizar_texto(registro["profissao"]),
            registro["municipioSlug"],
        )
        if chave in por_combinacao:
            contagem["duplicados"] += 1
            avisos.append("duplicado: mesmo WhatsApp+profissão+município — mantida a versão mais recente")
            if prioridade >= por_combinacao[chave][1]:
                por_combinacao[chave] = (registro, prioridade)
        else:
            por_combinacao[chave] = (registro, prioridade)

    profissionais = [valor[0] for valor in por_combinacao.values()]
    profissionais.sort(key=lambda r: (normalizar_texto(r["nome"]), r["municipioSlug"], r["id"]))
    contagem["publicados"] = len(profissionais)

    catalogo: dict[str, Any] = {
        "versao": VERSAO_CATALOGO,
        "geradoEm": None,
        "total": len(profissionais),
        "profissionais": [{campo: registro[campo] for campo in CAMPOS_PUBLICOS}
                          for registro in profissionais],
    }
    return catalogo, contagem, avisos, mapa_identidades, eventos


# ---------------------------------------------------------------------------
# Validação do catálogo final
# ---------------------------------------------------------------------------

def validar_catalogo(dados: Any) -> tuple[bool, list[str]]:
    erros: list[str] = []
    if not isinstance(dados, dict):
        return False, ["o catálogo deve ser um objeto JSON"]

    if dados.get("versao") != VERSAO_CATALOGO:
        erros.append(f"campo 'versao' deve ser {VERSAO_CATALOGO}")
    gerado = dados.get("geradoEm")
    if gerado is not None and (
        not isinstance(gerado, str)
        or not re.match(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z$", gerado)
    ):
        erros.append("campo 'geradoEm' deve ser null ou data ISO 8601")

    profissionais = dados.get("profissionais")
    if not isinstance(profissionais, list):
        erros.append("campo 'profissionais' deve ser uma lista")
        return False, erros

    ids: set[str] = set()
    combinacoes: set[tuple] = set()
    for indice, item in enumerate(profissionais):
        prefixo = f"profissionais[{indice}]"
        if not isinstance(item, dict):
            erros.append(f"{prefixo}: deve ser um objeto")
            continue
        proibidas = CHAVES_PROIBIDAS & set(item)
        if proibidas:
            erros.append(f"{prefixo}: contém campos privados ({', '.join(sorted(proibidas))})")
        extras = set(item) - set(CAMPOS_PUBLICOS)
        if extras:
            erros.append(f"{prefixo}: campos fora da allowlist ({', '.join(sorted(extras))})")
        for campo in CAMPOS_PUBLICOS:
            if campo not in item:
                erros.append(f"{prefixo}: campo '{campo}' ausente")
        identificador = item.get("id", "")
        if not isinstance(identificador, str) or not REGEX_ID.match(identificador):
            erros.append(f"{prefixo}: 'id' inválido")
        elif identificador in ids:
            erros.append(f"{prefixo}: 'id' duplicado ({identificador})")
        else:
            ids.add(identificador)
        uf = item.get("uf")
        if uf not in UFS:
            erros.append(f"{prefixo}: UF inválida")
        elif item.get("estado") != UFS[uf]:
            erros.append(f"{prefixo}: 'estado' não corresponde à UF")
        whatsapp = item.get("whatsapp", "")
        if not isinstance(whatsapp, str) or not REGEX_WHATSAPP.match(whatsapp):
            erros.append(f"{prefixo}: 'whatsapp' fora do formato 55DDD9XXXXXXXX")
        atualizado = item.get("atualizadoEm", "")
        if not isinstance(atualizado, str) or not REGEX_DATA.match(atualizado):
            erros.append(f"{prefixo}: 'atualizadoEm' fora do formato AAAA-MM-DD")
        for campo_lista in ("bairros", "outros_municipios"):
            valor = item.get(campo_lista)
            if not isinstance(valor, list) or any(not isinstance(i, str) for i in valor):
                erros.append(f"{prefixo}: '{campo_lista}' deve ser lista de textos")
        if not isinstance(item.get("atendimento_remoto", False), bool):
            erros.append(f"{prefixo}: 'atendimento_remoto' deve ser booleano")
        for campo_texto, maximo in (("nome", 160), ("categoria", 120), ("estado", 120),
                                    ("profissao", 120), ("descricao", 2000),
                                    ("municipio", 120)):
            valor = item.get(campo_texto, "")
            if not isinstance(valor, str) or not valor.strip():
                erros.append(f"{prefixo}: '{campo_texto}' vazio")
            elif len(valor) > maximo:
                erros.append(f"{prefixo}: '{campo_texto}' excede {maximo} caracteres")
        for campo_slug in ("categoriaSlug", "municipioSlug"):
            valor = item.get(campo_slug, "")
            if not isinstance(valor, str) or not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", valor):
                erros.append(f"{prefixo}: '{campo_slug}' inválido")
        combinacao = (whatsapp, normalizar_texto(str(item.get("profissao", ""))),
                      str(item.get("municipioSlug", "")))
        if combinacao in combinacoes:
            erros.append(f"{prefixo}: duplicado (WhatsApp+profissão+município)")
        combinacoes.add(combinacao)

    total = dados.get("total")
    if total is not None and total != len(profissionais):
        erros.append(f"'total' ({total}) difere da lista ({len(profissionais)})")

    return len(erros) == 0, erros


# ---------------------------------------------------------------------------
# Comparação com o catálogo publicado (dry-run)
# ---------------------------------------------------------------------------

def carregar_ids_publicados(diretorio: Path) -> dict[str, list[str]]:
    mapa: dict[str, list[str]] = {}
    caminho = diretorio / ARQUIVO_PRINCIPAL
    if not caminho.exists():
        return mapa
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return mapa
    for item in dados.get("profissionais", []):
        if isinstance(item, dict) and "whatsapp" in item and "id" in item:
            mapa.setdefault(item["whatsapp"], []).append(item["id"])
    return mapa


def comparar_com_atual(diretorio: Path, novo: dict[str, Any]) -> dict[str, int] | None:
    caminho = diretorio / ARQUIVO_PRINCIPAL
    if not caminho.exists():
        return None
    try:
        atual = json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    def indexacao(dados: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {p["id"]: p for p in dados.get("profissionais", []) if isinstance(p, dict) and "id" in p}

    atual_idx = indexacao(atual)
    novo_idx = indexacao(novo)
    novos = set(novo_idx) - set(atual_idx)
    removidos = set(atual_idx) - set(novo_idx)
    mantidos = set(atual_idx) & set(novo_idx)
    alterados = sum(1 for i in mantidos if atual_idx[i] != novo_idx[i])
    return {
        "novos": len(novos), "removidos": len(removidos),
        "alterados": alterados, "mantidos": len(mantidos) - alterados,
    }


# ---------------------------------------------------------------------------
# Persistência: mapa de identidades, relatório de moderação, catálogo
# ---------------------------------------------------------------------------

def carregar_mapa_identidades(diretorio_dados: Path) -> dict[str, str]:
    caminho = diretorio_dados / "identidades.json"
    if not caminho.exists():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in dados.get("mapa", {}).items()}
    except (json.JSONDecodeError, OSError, AttributeError):
        return {}


def salvar_mapa_identidades(diretorio_dados: Path, mapa: dict[str, str]) -> bool:
    caminho = diretorio_dados / "identidades.json"
    atual = carregar_mapa_identidades(diretorio_dados)
    if atual == mapa:
        return False
    conteudo = {"versao": 1, "mapa": dict(sorted(mapa.items()))}
    caminho.parent.mkdir(parents=True, exist_ok=True)
    escrever_atomico(caminho, json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n")
    return True


def escrever_relatorio_moderacao(
    diretorio_dados: Path,
    modo: str,
    contagem: dict[str, int],
    comparacao: dict[str, int] | None,
    eventos: dict[str, list[dict[str, Any]]],
) -> Path | None:
    """Relatório da fila de moderação — apenas linha/motivo, sem dados pessoais."""
    try:
        diretorio_dados.mkdir(parents=True, exist_ok=True)
        caminho = diretorio_dados / "relatorio-moderacao.json"
        relatorio = {
            "geradoEm": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "modo": modo,
            "resumo": contagem,
            "comparacaoComPublicado": comparacao,
            "retidosParaRevisao": eventos.get("retidos", []),
            "pendentesManuais": eventos.get("pendentes", []),
            "bloqueados": eventos.get("bloqueados", []),
            "invalidos": eventos.get("invalidos", []),
            "sinaisFracosPublicados": eventos.get("sinais_fracos", []),
        }
        escrever_atomico(caminho, json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n")
        return caminho
    except OSError as erro:
        print(f"  AVISO: não foi possível gravar o relatório de moderação: {erro}")
        return None


def escrever_atomico(caminho: Path, conteudo: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(conteudo, encoding="utf-8")
    os.replace(temporario, caminho)


def _sem_gerado_em(dados: dict[str, Any]) -> dict[str, Any]:
    return {chave: valor for chave, valor in dados.items() if chave != "geradoEm"}


def salvar_catalogo(diretorio: Path, catalogo: dict[str, Any],
                     diretorio_dados: Path, mapa_identidades: dict[str, str]) -> bool:
    caminho_principal = diretorio / ARQUIVO_PRINCIPAL

    atual: dict[str, Any] | None = None
    if caminho_principal.exists():
        try:
            atual = json.loads(caminho_principal.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            atual = None

    if atual is not None and _sem_gerado_em(atual) == _sem_gerado_em(catalogo):
        salvar_mapa_identidades(diretorio_dados, mapa_identidades)
        return False

    catalogo["geradoEm"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    valido, erros = validar_catalogo(catalogo)
    if not valido:
        raise ValueError("catálogo gerado não passou na validação: " + "; ".join(erros[:10]))

    escrever_atomico(caminho_principal, json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n")

    diretorio_uf = diretorio / "uf"
    por_uf: dict[str, list[dict[str, Any]]] = {}
    for profissional in catalogo["profissionais"]:
        por_uf.setdefault(profissional["uf"], []).append(profissional)

    diretorio_uf.mkdir(parents=True, exist_ok=True)
    desejados = set()
    for uf, itens in por_uf.items():
        bloco = {
            "versao": catalogo["versao"],
            "geradoEm": catalogo["geradoEm"],
            "total": len(itens),
            "profissionais": itens,
        }
        nome = f"{uf.lower()}.json"
        desejados.add(nome)
        escrever_atomico(diretorio_uf / nome, json.dumps(bloco, ensure_ascii=False, indent=2) + "\n")
    for existente in diretorio_uf.glob("*.json"):
        if existente.name not in desejados:
            existente.unlink()

    salvar_mapa_identidades(diretorio_dados, mapa_identidades)
    return True


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza a planilha privada do Google Sheets com o catálogo público."
    )
    parser.add_argument("--saida", default="public/data", help="diretório de saída público")
    parser.add_argument("--dir-dados", default="dados",
                        help="diretório de dados operacionais (identidades.json, relatório)")
    parser.add_argument("--csv", help="lê de um CSV local em vez do Google Sheets (testes)")
    parser.add_argument("--planilha-id", default=os.environ.get("GOOGLE_SHEET_ID", ""))
    parser.add_argument("--aba", default=os.environ.get("GOOGLE_SHEET_TAB_NAME", ABA_PADRAO))
    parser.add_argument("--credenciais-arquivo", help="caminho do JSON da conta de serviço")
    parser.add_argument("--id-secret", default=os.environ.get("PUBLIC_ID_SECRET", ""))
    parser.add_argument("--publicar", action="store_true",
                        help="grava o catálogo (sem esta flag, o modo Google apenas simula)")
    parser.add_argument("--dry-run", action="store_true", help="nunca grava; compara e relata")
    parser.add_argument("--verbose", action="store_true", help="exibe todos os avisos")
    args = parser.parse_args(argv)

    modo_csv = bool(args.csv)
    gravar = not args.dry_run and (args.publicar or modo_csv)

    segredo = args.id_secret.strip()
    segredo_simulado = False
    if not segredo:
        if gravar:
            print(
                "FALHA: PUBLIC_ID_SECRET não configurado. Gere com: openssl rand -hex 32. "
                "O catálogo atual foi preservado.",
                file=sys.stderr,
            )
            return 1
        segredo = "simulacao-sem-segredo"
        segredo_simulado = True

    if modo_csv:
        try:
            linhas = ler_csv(args.csv)
        except OSError as erro:
            print(f"FALHA: não foi possível ler o CSV: {erro}", file=sys.stderr)
            return 1
    else:
        credenciais = (
            Path(args.credenciais_arquivo).read_text(encoding="utf-8")
            if args.credenciais_arquivo
            else os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        )
        if not args.planilha_id or not credenciais:
            print(
                "FALHA: configure GOOGLE_SHEET_ID e GOOGLE_SERVICE_ACCOUNT_JSON "
                "(ou use --csv para testes locais).",
                file=sys.stderr,
            )
            return 1
        try:
            linhas = buscar_linhas_google(args.planilha_id, args.aba, credenciais)
        except Exception as erro:  # noqa: BLE001
            print(
                f"FALHA: não foi possível consultar o Google Sheets "
                f"({type(erro).__name__}). Verifique credenciais, ID da planilha, "
                f"aba '{args.aba}' e o compartilhamento com a conta de serviço. "
                "O catálogo atual foi preservado.",
                file=sys.stderr,
            )
            return 1

    if not linhas:
        print("FALHA: a planilha está vazia ou inacessível (nenhuma linha lida).", file=sys.stderr)
        return 1

    try:
        mapa = mapa_colunas(linhas[0])
    except ErroColunas as erro:
        print(f"FALHA de estrutura: {erro}", file=sys.stderr)
        return 1

    diretorio = Path(args.saida)
    diretorio_dados = Path(args.dir_dados)
    mapa_identidades = carregar_mapa_identidades(diretorio_dados)
    ids_publicados = carregar_ids_publicados(diretorio)

    catalogo, contagem, avisos, mapa_atualizado, eventos = montar_catalogo(
        linhas[1:], mapa, segredo, mapa_identidades, ids_publicados
    )

    catalogo_teste = dict(catalogo)
    catalogo_teste["geradoEm"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    valido, erros = validar_catalogo(catalogo_teste)
    if not valido:
        print("FALHA: o catálogo gerado é inválido; nada foi escrito:", file=sys.stderr)
        for erro in erros[:20]:
            print(f"  - {erro}", file=sys.stderr)
        return 1

    print("Resumo da sincronização (modo " + ("GRAVAÇÃO" if gravar else "SIMULAÇÃO") + "):")
    print(
        f"  linhas lidas: {contagem['linhas']} | a publicar: {contagem['publicados']} | "
        f"retidos (suspeitos): {contagem['retidos']} | pendentes: {contagem['pendentes']} | "
        f"bloqueados: {contagem['bloqueados']} | inválidos: {contagem['invalidos']} | "
        f"duplicados: {contagem['duplicados']}"
    )

    comparacao = comparar_com_atual(diretorio, catalogo)
    if comparacao is None:
        print("  catálogo atual: nenhum (primeira publicação)")
    else:
        print(
            f"  comparação com o publicado: novos: {comparacao['novos']} | "
            f"removidos: {comparacao['removidos']} | alterados: {comparacao['alterados']} | "
            f"mantidos: {comparacao['mantidos']}"
        )

    if segredo_simulado:
        print("  AVISO: PUBLIC_ID_SECRET ausente — IDs exibidos são de simulação.")
    if not gravar:
        print("  Nada foi gravado (use --publicar ou configure HABILITAR_PUBLICACAO=SIM).")

    limite_avisos = len(avisos) if args.verbose else min(len(avisos), 20)
    for aviso in avisos[:limite_avisos]:
        print(f"  aviso: {aviso}")
    if not args.verbose and len(avisos) > limite_avisos:
        print(f"  … e mais {len(avisos) - limite_avisos} avisos (use --verbose para todos).")

    # Relatório da fila de moderação — gravado em toda execução (inclusive
    # simulação), para consulta sem backend e sem escrita na planilha.
    relatorio = escrever_relatorio_moderacao(
        diretorio_dados,
        "GRAVACAO" if gravar else "SIMULACAO",
        contagem,
        comparacao,
        eventos,
    )
    if relatorio:
        print(f"  relatório de moderação: {relatorio}")

    if not gravar:
        return 0

    try:
        mudou = salvar_catalogo(diretorio, catalogo, diretorio_dados, mapa_atualizado)
    except (OSError, ValueError) as erro:
        print(f"FALHA ao gravar os arquivos: {erro}", file=sys.stderr)
        return 1

    if mudou:
        print(f"Catálogo atualizado em {args.saida}/{ARQUIVO_PRINCIPAL}.")
    else:
        print("Sem alterações reais — arquivos preservados (nenhum commit necessário).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
