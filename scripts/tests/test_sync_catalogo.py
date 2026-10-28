"""Testes do sincronizador (scripts/sync_catalogo.py).

Não requer dependências do Google: a busca na API é isolada em
buscar_linhas_google e os testes usam --csv ou as funções puras.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

spec = importlib.util.spec_from_file_location("sync_catalogo", RAIZ / "scripts" / "sync_catalogo.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

# (título na planilha, chave interna usada pelo sincronizador)
COLUNAS_MODELO = [
    ("Carimbo de data/hora", "timestamp"),
    ("Nome público", "nome"),
    ("Categoria", "categoria"),
    ("Profissão", "profissao"),
    ("Descrição do serviço", "descricao"),
    ("UF", "uf"),
    ("Município", "municipio"),
    ("Bairros atendidos", "bairros"),
    ("Outros municípios atendidos", "outros_municipios"),
    ("Atendimento remoto", "remoto"),
    ("WhatsApp", "whatsapp"),
    ("E-mail administrativo", "email"),
    ("Endereço comercial", "endereco"),
    ("Consentimento", "consentimento"),
    ("ID", "id"),
    ("Status", "status"),
    ("Data de aprovação", "data_aprovacao"),
    ("Última atualização", "data_atualizacao"),
    ("Observações", "observacoes"),
    ("Ativo", "ativo"),
]
CABECALHO = [titulo for titulo, _ in COLUNAS_MODELO]

PADRAO = {
    "timestamp": "01/10/2026 10:15:00",
    "nome": "Maria da Silva",
    "categoria": "Beleza e estética",
    "profissao": "Cabelereira",
    "descricao": "Cortes e coloração a domicílio.",
    "uf": "SP",
    "municipio": "Campinas",
    "bairros": "Taquaral; Centro",
    "outros_municipios": "Valinhos",
    "remoto": "Sim",
    "whatsapp": "(19) 99999-0001",
    "email": "maria@exemplo.com",
    "endereco": "Rua das Flores, 123",
    "consentimento": "Sim, Autorizo a Publicação dos Dados Informados.",
    "id": "",
    "status": "APROVADO",
    "data_aprovacao": "02/10/2026",
    "data_atualizacao": "",
    "observacoes": "contato em persona",
    "ativo": "",
}


def linha(**sobrescritas) -> list[str]:
    valores = dict(PADRAO)
    valores.update(sobrescritas)
    return [valores[chave] for _, chave in COLUNAS_MODELO]


def montar(linhas: list[list[str]]) -> tuple[dict, dict, list[str]]:
    mapa = sync.mapa_colunas(CABECALHO)
    return sync.montar_catalogo(linhas, mapa)


def escrever_csv(caminho: Path, linhas: list[list[str]]) -> None:
    import csv

    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        csv.writer(arquivo).writerows([CABECALHO, *linhas])


# ---------------------------------------------------------------------------
# Normalização e validações básicas
# ---------------------------------------------------------------------------

class TestNormalizacao:
    def test_normalizar_texto_ignora_acentos_e_caixa(self):
        assert sync.normalizar_texto("ELÉTRICA") == "eletrica"
        assert sync.normalizar_texto("  Hidráulica ") == "hidraulica"

    def test_slug(self):
        assert sync.slug("Belo Horizonte") == "belo-horizonte"
        assert sync.slug("Instalações — elétricas!") == "instalacoes-eletricas"

    def test_normalizar_uf(self):
        assert sync.normalizar_uf("sp") == "SP"
        assert sync.normalizar_uf("São Paulo") == "SP"
        assert sync.normalizar_uf("distrito federal") == "DF"
        assert sync.normalizar_uf("XX") is None
        assert sync.normalizar_uf("") is None

    def test_normalizar_whatsapp(self):
        assert sync.normalizar_whatsapp("(11) 99999-8888") == "5511999998888"
        assert sync.normalizar_whatsapp("5511999998888") == "5511999998888"
        assert sync.normalizar_whatsapp("+55 55 98123-4567") == "5555981234567"

    def test_normalizar_whatsapp_rejeita_fixos_e_invalidos(self):
        assert sync.normalizar_whatsapp("1132445566") is None
        assert sync.normalizar_whatsapp("999998888") is None
        assert sync.normalizar_whatsapp("99999999999") is None
        assert sync.normalizar_whatsapp("") is None

    def test_afirmativo_e_negativo(self):
        assert sync.afirmativo("Sim") is True
        assert sync.afirmativo("SIM, AUTORIZO A PUBLICAÇÃO DOS DADOS INFORMADOS.") is True
        assert sync.afirmativo("Não") is False
        assert sync.afirmativo("") is False
        assert sync.negativo("Não") is True
        assert sync.negativo("não ativo") is True
        assert sync.negativo("Sim") is False


# ---------------------------------------------------------------------------
# Cabeçalhos e estrutura
# ---------------------------------------------------------------------------

class TestCabecalhos:
    def test_mapeia_cabecalho_padrao(self):
        mapa = sync.mapa_colunas(CABECALHO)
        for coluna in sync.COLUNAS_OBRIGATORIAS:
            assert coluna in mapa

    def test_aceita_variacoes_de_titulo(self):
        variante = list(CABECALHO)
        variante[1] = "Nome público do profissional ou nome comercial"
        variante[10] = "Número de WhatsApp"
        variante[13] = "Consentimento para publicação"
        mapa = sync.mapa_colunas(variante)
        assert mapa["nome"] == 1
        assert mapa["whatsapp"] == 10
        assert mapa["consentimento"] == 13

    def test_rejeita_cabecalho_sem_colunas_obrigatorias(self):
        with pytest.raises(sync.ErroColunas, match="ausentes"):
            sync.mapa_colunas(["Timestamp", "Nome público", "WhatsApp"])


# ---------------------------------------------------------------------------
# Regras de publicação (fail-closed)
# ---------------------------------------------------------------------------

class TestRegrasDePublicacao:
    def test_publica_aprovado_com_consentimento(self):
        catalogo, contagem, _ = montar([linha()])
        assert contagem["publicados"] == 1
        registro = catalogo["profissionais"][0]
        assert registro["nome"] == "Maria da Silva"
        assert registro["whatsapp"] == "5519999990001"
        assert registro["uf"] == "SP"
        assert registro["municipioSlug"] == "campinas"
        assert registro["regioes"] == ["Taquaral", "Centro"]
        assert registro["municipiosAtendidos"] == ["Valinhos"]
        assert registro["remoto"] is True
        assert registro["atualizadoEm"] == "2026-10-02"

    def test_somente_campos_publicos_no_json(self):
        catalogo, _, _ = montar([linha()])
        registro = catalogo["profissionais"][0]
        assert set(registro.keys()) == set(sync.CAMPOS_PUBLICOS)
        # Nada privado pode vazar:
        for chave in ("email", "observacoes", "endereco", "status",
                      "consentimento", "data_aprovacao", "ativo", "timestamp"):
            assert chave not in registro
        assert "maria@exemplo.com" not in json.dumps(catalogo)
        assert "contato em persona" not in json.dumps(catalogo)
        assert "Rua das Flores" not in json.dumps(catalogo)

    def test_pendente_nao_e_publicado(self):
        _, contagem, _ = montar([linha(status="PENDENTE")])
        assert contagem["publicados"] == 0
        assert contagem["pendentes"] == 1

    def test_rejeitado_nao_e_publicado(self):
        _, contagem, _ = montar([linha(status="REJEITADO")])
        assert contagem["publicados"] == 0
        assert contagem["rejeitados"] == 1

    def test_inativo_nao_e_publicado(self):
        _, contagem, _ = montar([linha(status="INATIVO")])
        assert contagem["publicados"] == 0
        assert contagem["inativos"] == 1

    def test_status_vazio_tratado_como_pendente(self):
        _, contagem, avisos = montar([linha(status="")])
        assert contagem["publicados"] == 0
        assert contagem["pendentes"] == 1
        assert any("PENDENTE" in aviso for aviso in avisos)

    def test_status_desconhecido_tratado_como_pendente(self):
        _, contagem, _ = montar([linha(status="QUEM SABE")])
        assert contagem["publicados"] == 0
        assert contagem["pendentes"] == 1

    def test_aprovado_sem_consentimento_nao_e_publicado(self):
        _, contagem, avisos = montar([linha(consentimento="Não")])
        assert contagem["publicados"] == 0
        assert contagem["sem_consentimento"] == 1
        assert any("consentimento" in aviso for aviso in avisos)

    def test_ativo_negativo_nao_e_publicado(self):
        _, contagem, _ = montar([linha(ativo="Não")])
        assert contagem["publicados"] == 0
        assert contagem["inativos"] == 1

    def test_uf_invalida_nao_publica(self):
        _, contagem, avisos = montar([linha(uf="XX")])
        assert contagem["publicados"] == 0
        assert any("UF" in aviso for aviso in avisos)

    def test_whatsapp_invalido_nao_publica(self):
        _, contagem, avisos = montar([linha(whatsapp="19 3232-0000")])
        assert contagem["publicados"] == 0
        assert any("WhatsApp" in aviso for aviso in avisos)

    def test_municipio_vazio_nao_publica(self):
        _, contagem, _ = montar([linha(municipio="  ")])
        assert contagem["publicados"] == 0

    def test_sem_dados_pessoais_nos_avisos(self):
        _, _, avisos = montar([
            linha(whatsapp="3232-0000", email="secreto@exemplo.com", nome="Fulana Secreta")
        ])
        texto = " ".join(avisos)
        assert "Fulana" not in texto
        assert "secreto" not in texto


class TestDuplicados:
    def test_id_duplicado_mantem_versao_mais_recente(self):
        catalogo, contagem, _ = montar([
            linha(descricao="versão antiga", data_aprovacao="01/10/2026"),
            linha(descricao="versão nova", data_aprovacao="05/10/2026"),
        ])
        assert contagem["publicados"] == 1
        assert contagem["duplicados"] == 1
        assert catalogo["profissionais"][0]["descricao"] == "versão nova"

    def test_id_manual_da_planilha_e_respeitado(self):
        catalogo, _, _ = montar([linha(id="maria-campinas-001")])
        assert catalogo["profissionais"][0]["id"] == "maria-campinas-001"

    def test_id_derivado_e_estavel(self):
        catalogo1, _, _ = montar([linha()])
        catalogo2, _, _ = montar([linha()])
        assert catalogo1["profissionais"][0]["id"] == catalogo2["profissionais"][0]["id"]


class TestAtualizacaoEDesativacao:
    def _publicado(self, linhas):
        catalogo, _, _ = montar(linhas)
        return catalogo["profissionais"]

    def test_alteracao_na_planilha_reflete_no_catalogo(self):
        antes = self._publicado([linha(descricao="Pintura residencial.")])
        depois = self._publicado([linha(descricao="Pintura residencial e comercial.")])
        assert antes[0]["descricao"] != depois[0]["descricao"]

    def test_desativar_remove_da_proxima_publicacao(self):
        ativo = self._publicado([linha()])
        desativado = self._publicado([linha(ativo="Não")])
        assert len(ativo) == 1
        assert len(desativado) == 0

    def test_excluir_linha_remove_do_catalogo(self):
        com = self._publicado([linha(), linha(nome="Outra Pessoa", municipio="Santos")])
        sem = self._publicado([linha()])
        assert len(com) == 2
        assert len(sem) == 1


class TestSemRegistros:
    def test_apenas_pendentes_gera_catalogo_valido_e_vazio(self):
        catalogo, contagem, _ = montar([linha(status="PENDENTE"), linha(status="REJEITADO")])
        assert catalogo["profissionais"] == []
        assert catalogo["total"] == 0
        assert contagem["publicados"] == 0
        valido, erros = sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"}
        )
        assert valido, erros

    def test_linhas_totalmente_vazias_sao_ignoradas(self):
        _, contagem, _ = montar([[""] * len(CABECALHO), [""] * len(CABECALHO), linha()])
        assert contagem["publicados"] == 1
        assert contagem["linhas"] == 1


# ---------------------------------------------------------------------------
# Validação do catálogo
# ---------------------------------------------------------------------------

class TestValidarCatalogo:
    def base(self):
        catalogo, _, _ = montar([linha()])
        catalogo["geradoEm"] = "2026-10-28T12:00:00Z"
        return catalogo

    def test_catalogo_valido_passa(self):
        valido, erros = sync.validar_catalogo(self.base())
        assert valido, erros

    def test_rejeita_campo_privado_vazado(self):
        catalogo = self.base()
        catalogo["profissionais"][0]["email"] = "vazado@exemplo.com"
        valido, erros = sync.validar_catalogo(catalogo)
        assert not valido
        assert any("privado" in erro for erro in erros)

    def test_rejeita_whatsapp_mal_formado(self):
        catalogo = self.base()
        catalogo["profissionais"][0]["whatsapp"] = "11999998888"
        assert not sync.validar_catalogo(catalogo)[0]

    def test_rejeita_total_incoerente(self):
        catalogo = self.base()
        catalogo["total"] = 99
        assert not sync.validar_catalogo(catalogo)[0]


# ---------------------------------------------------------------------------
# Escrita e atomicidade
# ---------------------------------------------------------------------------

class TestEscrita:
    def test_end_to_end_csv_escreve_catalogo_e_blocos_uf(self, tmp_path):
        saida = tmp_path / "data"
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [
            linha(),
            linha(nome="João Souza", uf="MG", municipio="Belo Horizonte",
                  whatsapp="(31) 98888-0002", bairros="Centro"),
        ])
        codigo = sync.main(["--csv", str(csv_path), "--saida", str(saida), "--verbose"])
        assert codigo == 0

        principal = json.loads((saida / "catalogo.json").read_text(encoding="utf-8"))
        assert principal["total"] == 2
        assert (saida / "uf" / "sp.json").exists()
        assert (saida / "uf" / "mg.json").exists()
        bloco_sp = json.loads((saida / "uf" / "sp.json").read_text(encoding="utf-8"))
        assert bloco_sp["total"] == 1
        assert bloco_sp["profissionais"][0]["uf"] == "SP"

    def test_sem_alteracoes_reais_preserva_arquivo(self, tmp_path):
        saida = tmp_path / "data"
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [linha()])
        assert sync.main(["--csv", str(csv_path), "--saida", str(saida)]) == 0
        original = (saida / "catalogo.json").read_text(encoding="utf-8")

        # Segunda execução: mesmos dados => não reescreve (mesmo geradoEm).
        codigo = sync.main(["--csv", str(csv_path), "--saida", str(saida)])
        assert codigo == 0
        assert (saida / "catalogo.json").read_text(encoding="utf-8") == original

    def test_falha_de_estrutura_nao_sobrescreve_catalogo(self, tmp_path):
        saida = tmp_path / "data"
        csv_bom = tmp_path / "bom.csv"
        escrever_csv(csv_bom, [linha()])
        assert sync.main(["--csv", str(csv_bom), "--saida", str(saida)]) == 0
        original = (saida / "catalogo.json").read_text(encoding="utf-8")

        csv_ruim = tmp_path / "ruim.csv"
        csv_ruim.write_text(
            "Coluna A,Coluna B\nvalor 1,valor 2\n", encoding="utf-8"
        )
        codigo = sync.main(["--csv", str(csv_ruim), "--saida", str(saida)])
        assert codigo == 1
        assert (saida / "catalogo.json").read_text(encoding="utf-8") == original

    def test_dry_run_nao_escreve(self, tmp_path):
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [linha()])
        saida = tmp_path / "data"
        assert sync.main(["--csv", str(csv_path), "--saida", str(saida), "--dry-run"]) == 0
        assert not (saida / "catalogo.json").exists()

    def test_falha_de_autenticacao_preserva_catalogo(self, tmp_path, monkeypatch):
        saida = tmp_path / "data"
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [linha()])
        assert sync.main(["--csv", str(csv_path), "--saida", str(saida)]) == 0
        original = (saida / "catalogo.json").read_text(encoding="utf-8")

        def explodir(*args, **kwargs):
            raise RuntimeError("credenciais inválidas")

        monkeypatch.setattr(sync, "buscar_linhas_google", explodir)
        monkeypatch.setenv("GOOGLE_SHEET_ID", "abc123")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type": "service_account"}')
        codigo = sync.main(["--saida", str(saida)])
        assert codigo == 1
        assert (saida / "catalogo.json").read_text(encoding="utf-8") == original

    def test_sem_configuracao_google_retorna_erro(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
        assert sync.main(["--saida", str(tmp_path)]) == 1

    def test_bloco_uf_obsoleto_e_removido(self, tmp_path):
        saida = tmp_path / "data"
        csv_com_mg = tmp_path / "com_mg.csv"
        escrever_csv(csv_com_mg, [linha(), linha(nome="João Souza", uf="MG",
                                                 municipio="Belo Horizonte",
                                                 whatsapp="(31) 98888-0002")])
        assert sync.main(["--csv", str(csv_com_mg), "--saida", str(saida)]) == 0
        assert (saida / "uf" / "mg.json").exists()

        csv_so_sp = tmp_path / "so_sp.csv"
        escrever_csv(csv_so_sp, [linha()])
        assert sync.main(["--csv", str(csv_so_sp), "--saida", str(saida)]) == 0
        assert not (saida / "uf" / "mg.json").exists()
        assert (saida / "uf" / "sp.json").exists()


# ---------------------------------------------------------------------------
# Consistência com o catálogo commitado no repositório
# ---------------------------------------------------------------------------

class TestCatalogoDoRepositorio:
    def test_catalogo_inicial_passa_na_validacao(self):
        caminho = RAIZ / "public" / "data" / "catalogo.json"
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        valido, erros = sync.validar_catalogo(dados)
        assert valido, erros
        assert dados["total"] == 0  # produção começa vazio, sem dados fictícios

    def test_modelo_de_planilha_e_processavel(self):
        """O CSV modelo (docs) precisa ser aceito pelo sincronizador."""
        caminho = RAIZ / "scripts" / "modelo_planilha.csv"
        linhas = sync.ler_csv(str(caminho))
        mapa = sync.mapa_colunas(linhas[0])
        catalogo, contagem, _ = sync.montar_catalogo(linhas[1:], mapa)
        assert contagem["publicados"] == 1
        assert contagem["pendentes"] == 1
        valido, erros = sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"}
        )
        assert valido, erros
