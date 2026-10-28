#!/usr/bin/env python3
"""
Sincronizador: Google Sheets (privado) -> catálogo público JSON.

Fluxo: autentica com conta de serviço -> lê a aba configurada -> valida
cabeçalhos -> normaliza e valida registros -> publica SOMENTE cadastros
APROVADOS, ativos e com consentimento válido -> escreve arquivos de forma
atômica (nunca sobrescreve o catálogo em caso de falha).

Princípios:
  - Fail-closed: qualquer erro de estrutura/autenticação interrompe sem
    tocar nos arquivos existentes (código de saída 1).
  - Minimização: apenas campos autorizados são exportados; e-mail,
    endereço comercial, observações e dados de registros não aprovados
    nunca saem da planilha.
  - Logs sem dados pessoais: avisos referenciam linha e motivo, nunca o
    conteúdo da célula.

Uso:
  GOOGLE_SHEET_ID=... GOOGLE_SERVICE_ACCOUNT_JSON=... python scripts/sync_catalogo.py
  python scripts/sync_catalogo.py --csv planilha.csv          # modo local/teste
  python scripts/sync_catalogo.py --dry-run --verbose         # não escreve nada
"""

from __future__ import annotations

import argparse
import csv as csv_modulo
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSAO_CATALOGO = 1

STATUS_VALIDOS = {"PENDENTE", "APROVADO", "REJEITADO", "INATIVO"}

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

# Ordem exata dos campos no JSON público (estável para diffs e consumers).
CAMPOS_PUBLICOS = (
    "id", "nome", "categoria", "categoriaSlug", "profissao", "descricao",
    "uf", "municipio", "municipioSlug", "regioes", "municipiosAtendidos",
    "remoto", "whatsapp", "atualizadoEm",
)

# Chaves que JAMAIS podem aparecer em um item público.
CHAVES_PROIBIDAS = {
    "email", "emailAdministrativo", "endereco", "enderecoComercial",
    "observacoes", "status", "dataAprovacao", "consentimento", "ativo",
    "timestamp", "dataEnvio",
}

REGEX_WHATSAPP = re.compile(r"^55[1-9][0-9]9[0-9]{8}$")
REGEX_ID = re.compile(r"^[a-z0-9-]{4,64}$")
REGEX_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Mapeamento de cabeçalhos da planilha -> chaves internas (aliases em
# minúsculas e sem acento). Títulos recomendados no docs/GOOGLE_FORMS.md.
COLUNAS: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "carimbo de data/hora", "data de envio", "data"),
    "nome": ("nome publico", "nome publico do profissional ou nome comercial",
             "nome do profissional", "nome"),
    "categoria": ("categoria", "categoria de servico", "area"),
    "profissao": ("profissao", "profissao ou tipo de servico", "servico", "tipo de servico"),
    "descricao": ("descricao", "descricao do servico", "sobre o servico"),
    "uf": ("uf", "estado", "unidade federativa"),
    "municipio": ("municipio", "cidade"),
    "bairros": ("bairros atendidos", "bairros", "regioes atendidas", "regiao atendida"),
    "outros_municipios": ("outros municipios atendidos", "municipios atendidos",
                          "outras cidades atendidas"),
    "remoto": ("atendimento remoto", "remoto", "atende remoto"),
    "whatsapp": ("whatsapp", "whatsapp profissional", "numero whatsapp",
                 "numero de whatsapp", "zap"),
    "email": ("email administrativo", "email", "e-mail"),
    "endereco": ("endereco comercial", "endereco"),
    "consentimento": ("consentimento", "consentimento para publicacao",
                      "consentimento publicacao", "autorizacao", "autorizo a publicacao"),
    "id": ("id", "identificador", "identificador unico", "id publico"),
    "status": ("status", "situacao"),
    "data_aprovacao": ("data de aprovacao", "data aprovacao", "aprovado em"),
    "data_atualizacao": ("ultima atualizacao", "data da ultima atualizacao", "atualizado em"),
    "observacoes": ("observacoes", "observacoes administrativas", "notas"),
    "ativo": ("ativo", "cadastro ativo", "situacao de atividade", "atividade"),
}

COLUNAS_OBRIGATORIAS = ("nome", "categoria", "profissao", "descricao", "uf",
                        "municipio", "whatsapp", "consentimento", "status")


class ErroColunas(Exception):
    """Cabeçalhos da planilha não correspondem ao esperado."""


# ---------------------------------------------------------------------------
# Normalização (espelha src/lib/* do frontend; testes cobrem ambos os lados)
# ---------------------------------------------------------------------------

def normalizar_texto(valor: str) -> str:
    """Minúsculas, sem acentos, espaços colapsados."""
    decomposto = unicodedata.normalize("NFD", valor)
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acentos).lower().strip()


def slug(valor: str) -> str:
    """Slug seguro para URLs."""
    texto = normalizar_texto(valor)
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-{2,}", "-", texto).strip("-")
    return texto[:80].rstrip("-")


def limpar_celula(valor: Any) -> str:
    """str -> remove caracteres de controle, colapsa espaços."""
    if valor is None:
        return ""
    texto = str(valor)
    texto = re.sub(r"[\x00-\x1f\x7f]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def mascarar_telefone(numero: str) -> str:
    return f"…{numero[-4:]}" if len(numero) >= 4 else "…"


def normalizar_uf(valor: str) -> str | None:
    limpo = re.sub(r"[^a-z ]", " ", normalizar_texto(valor)).strip()
    if not limpo:
        return None
    if limpo.upper() in UFS:
        return limpo.upper()
    for sigla, nome in UFS.items():
        if normalizar_texto(nome) == limpo:
            return sigla
    return None


def normalizar_whatsapp(valor: str) -> str | None:
    """Valida e converte para 55DDD9XXXXXXXX. Fixos e números incompletos -> None."""
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
        or texto in {"true", "x", "ok", "autorizo", "aceito", "concordo", "sim,"}
        or texto.startswith("autorizo")
        or texto.startswith("aceito")
    )


def negativo(valor: str) -> bool:
    texto = normalizar_texto(valor)
    return texto.startswith("nao") or texto in {"false", "0", "n", "inativo"}


def parse_data(valor: str) -> date | None:
    texto = limpar_celula(valor)
    if not texto:
        return None
    texto = texto.split(" ")[0]  # remove hora, se houver
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def dividir_lista(valor: str, maximo_itens: int = 15) -> list[str]:
    """Divide campos de lista por ';' ou ',' ou quebra de linha já normalizada."""
    texto = limpar_celula(valor)
    if not texto:
        return []
    partes = re.split(r"[;,]", texto)
    itens: list[str] = []
    for parte in partes:
        item = parte.strip()[:120]
        if item and item.lower() not in {i.lower() for i in itens}:
            itens.append(item)
    return itens[:maximo_itens]


# ---------------------------------------------------------------------------
# Leitura da planilha (Google Sheets via API oficial ou CSV local)
# ---------------------------------------------------------------------------

def mapa_colunas(cabecalho: list[str]) -> dict[str, int]:
    """Normaliza o cabeçalho e valida colunas obrigatórias."""
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
            + ". Consulte docs/GOOGLE_FORMS.md para a estrutura esperada."
        )
    return mapa


def linha_para_dicionario(linha: list[str], mapa: dict[str, int]) -> dict[str, str]:
    dados: dict[str, str] = {}
    for chave, indice in mapa.items():
        valor = linha[indice] if indice < len(linha) else ""
        dados[chave] = limpar_celula(valor)
    return dados


def buscar_linhas_google(planilha_id: str, aba: str, credenciais_json: str) -> list[list[str]]:
    """Consulta a aba configurada com a API oficial (importação tardia)."""
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
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
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
# Processamento dos registros
# ---------------------------------------------------------------------------

def gerar_id(dados: dict[str, str], whatsapp: str) -> str:
    """ID público estável: coluna ID (se a moderação fixar) ou hash curto."""
    id_manual = slug(dados.get("id", ""))
    if REGEX_ID.match(id_manual):
        return id_manual
    base = f"{dados.get('timestamp', '')}|{dados.get('nome', '')}|{whatsapp}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def processar_linha(
    dados: dict[str, str], numero_linha: int, avisos: list[str]
) -> dict[str, Any] | None:
    """Converte uma linha em registro público, aplicando todas as regras.

    Retorna None (com aviso) quando o registro não pode ser publicado.
    Nunca registra conteúdo sensível nos avisos — apenas linha e motivo.
    """
    def avisar(motivo: str) -> None:
        avisos.append(f"linha {numero_linha}: {motivo}")

    # Linha totalmente vazia: ignora em silêncio.
    if not any(dados.values()):
        return None

    status = dados.get("status", "").strip().upper()
    if not status:
        status = "PENDENTE"
        avisar("sem status — tratado como PENDENTE")
    elif status not in STATUS_VALIDOS:
        avisar(f"status desconhecido '{status}' — tratado como PENDENTE")
        status = "PENDENTE"

    if status != "APROVADO":
        return None  # pendentes/rejeitados/inativos simplesmente não publicam

    if not afirmativo(dados.get("consentimento", "")):
        avisar("APROVADO sem consentimento válido — não publicado")
        return None

    if negativo(dados.get("ativo", "")):
        avisar("cadastro marcado como inativo — não publicado")
        return None

    uf = normalizar_uf(dados.get("uf", ""))
    if uf is None:
        avisar("UF inválida ou vazia — não publicado")
        return None

    municipio = dados.get("municipio", "")[:120]
    if not municipio:
        avisar("município vazio — não publicado")
        return None

    whatsapp = normalizar_whatsapp(dados.get("whatsapp", ""))
    if whatsapp is None:
        avisar("WhatsApp inválido (fixo, incompleto ou formato errado) — não publicado")
        return None

    nome = dados.get("nome", "")[:160]
    categoria = dados.get("categoria", "")[:120]
    profissao = dados.get("profissao", "")[:120]
    descricao = dados.get("descricao", "")[:2000]
    if not nome or not categoria or not profissao or not descricao:
        avisar("campo essencial vazio (nome/categoria/profissão/descrição) — não publicado")
        return None

    data_referencia = (
        parse_data(dados.get("data_atualizacao", ""))
        or parse_data(dados.get("data_aprovacao", ""))
        or parse_data(dados.get("timestamp", ""))
    )
    if data_referencia is None:
        avisar("sem data utilizável (envio/aprovação/atualização) — não publicado")
        return None

    registro = {
        "id": gerar_id(dados, whatsapp),
        "nome": nome,
        "categoria": categoria,
        "categoriaSlug": slug(categoria),
        "profissao": profissao,
        "descricao": descricao,
        "uf": uf,
        "municipio": municipio,
        "municipioSlug": slug(municipio),
        "regioes": dividir_lista(dados.get("bairros", "")),
        "municipiosAtendidos": dividir_lista(dados.get("outros_municipios", "")),
        "remoto": afirmativo(dados.get("remoto", "")),
        "whatsapp": whatsapp,
        "atualizadoEm": data_referencia.isoformat(),
    }
    if not registro["categoriaSlug"] or not registro["municipioSlug"]:
        avisar("categoria ou município sem texto utilizável — não publicado")
        return None
    return registro


def montar_catalogo(
    linhas: list[list[str]], mapa: dict[str, int]
) -> tuple[dict[str, Any], dict[str, int], list[str]]:
    """Constrói o catálogo completo a partir das linhas da planilha."""
    avisos: list[str] = []
    contagem = {
        "linhas": 0, "publicados": 0, "pendentes": 0, "rejeitados": 0,
        "inativos": 0, "sem_consentimento": 0, "invalidos": 0, "duplicados": 0,
    }

    por_id: dict[str, tuple[dict[str, Any], tuple]] = {}

    for indice, linha in enumerate(linhas):
        numero_linha = indice + 2  # +2: linha 1 é o cabeçalho
        dados = linha_para_dicionario(linha, mapa)
        if not any(dados.values()):
            continue
        contagem["linhas"] += 1

        status_bruto = dados.get("status", "").strip().upper() or "PENDENTE"
        if status_bruto not in STATUS_VALIDOS:
            status_bruto = "PENDENTE"

        registro = processar_linha(dados, numero_linha, avisos)
        if registro is None:
            if status_bruto == "PENDENTE":
                contagem["pendentes"] += 1
            elif status_bruto == "REJEITADO":
                contagem["rejeitados"] += 1
            elif status_bruto == "INATIVO":
                contagem["inativos"] += 1
            elif not afirmativo(dados.get("consentimento", "")):
                contagem["sem_consentimento"] += 1
            elif negativo(dados.get("ativo", "")):
                contagem["inativos"] += 1
            else:
                contagem["invalidos"] += 1
            continue

        prioridade = (
            parse_data(dados.get("data_aprovacao", "")) or date.min,
            parse_data(dados.get("timestamp", "")) or date.min,
            indice,
        )
        if registro["id"] in por_id:
            contagem["duplicados"] += 1
            avisos.append(f"linha {numero_linha}: id duplicado — mantida a versão mais recente")
            if prioridade >= por_id[registro["id"]][1]:
                por_id[registro["id"]] = (registro, prioridade)
        else:
            por_id[registro["id"]] = (registro, prioridade)

    profissionais = [valor[0] for valor in por_id.values()]
    profissionais.sort(key=lambda r: (normalizar_texto(r["nome"]), r["municipioSlug"], r["id"]))
    contagem["publicados"] = len(profissionais)

    catalogo: dict[str, Any] = {
        "versao": VERSAO_CATALOGO,
        "geradoEm": None,  # definido apenas no momento da escrita
        "total": len(profissionais),
        "profissionais": [{campo: registro[campo] for campo in CAMPOS_PUBLICOS}
                          for registro in profissionais],
    }
    return catalogo, contagem, avisos


# ---------------------------------------------------------------------------
# Validação do catálogo final (barreira antes da escrita)
# ---------------------------------------------------------------------------

def validar_catalogo(dados: Any) -> tuple[bool, list[str]]:
    """Validação estrutural completa do JSON público. Espelha src/lib/catalogo-parse.ts."""
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
    for indice, item in enumerate(profissionais):
        prefixo = f"profissionais[{indice}]"
        if not isinstance(item, dict):
            erros.append(f"{prefixo}: deve ser um objeto")
            continue
        proibidas = CHAVES_PROIBIDAS & set(item)
        if proibidas:
            erros.append(f"{prefixo}: contém campos privados ({', '.join(sorted(proibidas))})")
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
        if item.get("uf") not in UFS:
            erros.append(f"{prefixo}: UF inválida")
        whatsapp = item.get("whatsapp", "")
        if not isinstance(whatsapp, str) or not REGEX_WHATSAPP.match(whatsapp):
            erros.append(f"{prefixo}: 'whatsapp' fora do formato 55DDD9XXXXXXXX")
        atualizado = item.get("atualizadoEm", "")
        if not isinstance(atualizado, str) or not REGEX_DATA.match(atualizado):
            erros.append(f"{prefixo}: 'atualizadoEm' fora do formato AAAA-MM-DD")
        for campo_lista in ("regioes", "municipiosAtendidos"):
            valor = item.get(campo_lista)
            if not isinstance(valor, list) or any(not isinstance(i, str) for i in valor):
                erros.append(f"{prefixo}: '{campo_lista}' deve ser lista de textos")
        if not isinstance(item.get("remoto", False), bool):
            erros.append(f"{prefixo}: 'remoto' deve ser booleano")
        for campo_texto, maximo in (("nome", 160), ("categoria", 120),
                                    ("profissao", 120), ("descricao", 2000),
                                    ("municipio", 120)):
            valor = item.get(campo_texto, "")
            if not isinstance(valor, str) or not valor.strip():
                erros.append(f"{prefixo}: '{campo_texto}' vazio")
            elif len(valor) > maximo:
                erros.append(f"{prefixo}: '{campo_texto}' excede {maximo} caracteres")

    total = dados.get("total")
    if total is not None and total != len(profissionais):
        erros.append(f"'total' ({total}) difere da lista ({len(profissionais)})")

    return len(erros) == 0, erros


# ---------------------------------------------------------------------------
# Escrita atômica
# ---------------------------------------------------------------------------

def escrever_atomico(caminho: Path, conteudo: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(conteudo, encoding="utf-8")
    os.replace(temporario, caminho)


def _sem_gerado_em(dados: dict[str, Any]) -> dict[str, Any]:
    return {chave: valor for chave, valor in dados.items() if chave != "geradoEm"}


def salvar_catalogo(diretorio: Path, catalogo: dict[str, Any]) -> bool:
    """Grava catálogo e blocos por UF. Retorna True apenas se houve mudança real."""
    caminho_principal = diretorio / "catalogo.json"

    atual: dict[str, Any] | None = None
    if caminho_principal.exists():
        try:
            atual = json.loads(caminho_principal.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            atual = None  # catálogo atual corrompido: o novo válido o substitui

    if atual is not None and _sem_gerado_em(atual) == _sem_gerado_em(catalogo):
        return False  # nada mudou: preserva geradoEm e evita commit vazio

    catalogo["geradoEm"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    valido, erros = validar_catalogo(catalogo)
    if not valido:
        raise ValueError("catálogo gerado não passou na validação: " + "; ".join(erros[:10]))

    conteudo = json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n"
    escrever_atomico(caminho_principal, conteudo)

    # Blocos por UF (otimização de carregamento da busca).
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

    # Remove arquivos de UF que não possuem mais profissionais.
    for existente in diretorio_uf.glob("*.json"):
        if existente.name not in desejados:
            existente.unlink()

    return True


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza a planilha privada do Google Sheets com o catálogo público."
    )
    parser.add_argument("--saida", default="public/data", help="diretório de saída (padrão: public/data)")
    parser.add_argument("--csv", help="lê de um CSV local em vez do Google Sheets (testes)")
    parser.add_argument("--planilha-id", default=os.environ.get("GOOGLE_SHEET_ID", ""))
    parser.add_argument("--aba", default=os.environ.get("GOOGLE_SHEET_TAB_NAME", "Respostas de formulário 1"))
    parser.add_argument("--credenciais-arquivo", help="caminho do JSON da conta de serviço")
    parser.add_argument("--dry-run", action="store_true", help="valida e mostra resumo sem escrever")
    parser.add_argument("--verbose", action="store_true", help="exibe todos os avisos")
    args = parser.parse_args(argv)

    if args.csv:
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
        except Exception as erro:  # noqa: BLE001 — log sem detalhes sensíveis
            print(
                f"FALHA: não foi possível consultar o Google Sheets "
                f"({type(erro).__name__}). Verifique credenciais, ID da planilha, "
                "aba e o compartilhamento com a conta de serviço. O catálogo "
                "atual foi preservado.",
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

    catalogo, contagem, avisos = montar_catalogo(linhas[1:], mapa)

    # Pré-validação antes de qualquer escrita.
    catalogo_teste = dict(catalogo)
    catalogo_teste["geradoEm"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    valido, erros = validar_catalogo(catalogo_teste)
    if not valido:
        print("FALHA: o catálogo gerado é inválido; nada foi escrito:", file=sys.stderr)
        for erro in erros[:20]:
            print(f"  - {erro}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"DRY-RAN. Resumo: {json.dumps(contagem, ensure_ascii=False)}")
        for aviso in avisos[:50]:
            print(f"  aviso: {aviso}")
        return 0

    try:
        mudou = salvar_catalogo(Path(args.saida), catalogo)
    except (OSError, ValueError) as erro:
        print(f"FALHA ao gravar os arquivos: {erro}", file=sys.stderr)
        return 1

    print(
        f"Sincronização concluída. Linhas: {contagem['linhas']} | "
        f"publicados: {contagem['publicados']} | pendentes: {contagem['pendentes']} | "
        f"rejeitados: {contagem['rejeitados']} | inativos: {contagem['inativos']} | "
        f"sem consentimento: {contagem['sem_consentimento']} | inválidos: {contagem['invalidos']} | "
        f"duplicados: {contagem['duplicados']}."
    )
    if mudou:
        print("Catálogo atualizado com novas informações.")
    else:
        print("Sem alterações reais — arquivos preservados (nenhum commit necessário).")

    limite_avisos = len(avisos) if args.verbose else min(len(avisos), 20)
    for aviso in avisos[:limite_avisos]:
        print(f"  aviso: {aviso}")
    if not args.verbose and len(avisos) > limite_avisos:
        print(f"  … e mais {len(avisos) - limite_avisos} avisos (use --verbose para todos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
