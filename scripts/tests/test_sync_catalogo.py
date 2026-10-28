"""Testes do sincronizador (scripts/sync_catalogo.py) com a estrutura REAL
da planilha (cabeçalhos atuais, UF "SP - São Paulo", consentimento longo,
ATIVO=SIM obrigatório). Sem dependências do Google: usa --csv e funções puras.
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

SEGREDO_TESTE = "segredo-teste-0123456789abcdef"

# (título na planilha, chave interna) — estrutura real, com espaços extras
# em alguns títulos para exercitar a normalização.
COLUNAS_MODELO = [
    ("Carimbo de data/hora", "timestamp"),
    (" Nome profissional ", "nome"),
    ("Categoria", "categoria"),
    (" Profissão ", "profissao"),
    ("Descrição do serviço", "descricao"),
    ("Estado (UF)", "uf"),
    (" Município ", "municipio"),
    ("Bairros atendidos", "bairros"),
    ("Outros municípios atendidos", "outros_municipios"),
    ("Atendimento remoto", "remoto"),
    (" WhatsApp ", "whatsapp"),
    ("E-mail administrativo", "email"),
    ("Endereço comercial", "endereco"),
    ("Consentimento para publicação", "consentimento"),
    ("ID_PUBLICO", "id"),
    ("STATUS", "status"),
    ("ATIVO", "ativo"),
    ("DATA_APROVACAO", "data_aprovacao"),
    ("DATA_ATUALIZACAO", "data_atualizacao"),
    ("OBSERVACOES_INTERNAS", "observacoes"),
]
CABECALHO = [titulo for titulo, _ in COLUNAS_MODELO]

CONSENTIMENTO = (
    "Li as informações sobre o uso dos meus dados pessoais e autorizo "
    "a divulgação pública dos dados profissionais indicados."
)

PADRAO = {
    "timestamp": "01/10/2026 10:15:00",
    "nome": "Maria da Silva",
    "categoria": "Beleza e estética",
    "profissao": "Cabelereira",
    "descricao": "Cortes e coloração a domicílio.",
    "uf": "SP - São Paulo",
    "municipio": "Campinas",
    "bairros": "Taquaral; Centro",
    "outros_municipios": "Valinhos",
    "remoto": "Sim",
    "whatsapp": "19999990001",
    "email": "maria@exemplo.com",
    "endereco": "Rua das Flores, 123",
    "consentimento": CONSENTIMENTO,
    "id": "",
    "status": "APROVADO",
    "data_aprovacao": "02/10/2026",
    "data_atualizacao": "",
    "observacoes": "anotacao interna sensivel",
    "ativo": "SIM",
}


def linha(**sobrescritas) -> list[str]:
    valores = dict(PADRAO)
    valores.update(sobrescritas)
    return [valores[chave] for _, chave in COLUNAS_MODELO]


def montar(linhas: list[list[str]]):
    mapa = sync.mapa_colunas(CABECALHO)
    return sync.montar_catalogo(linhas, mapa, SEGREDO_TESTE)


def escrever_csv(caminho: Path, linhas: list[list[str]]) -> None:
    import csv

    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        csv.writer(arquivo).writerows([CABECALHO, *linhas])


def executar(tmp_path: Path, linhas: list[list[str]], *flags: str) -> int:
    csv_path = tmp_path / "planilha.csv"
    escrever_csv(csv_path, linhas)
    saida = tmp_path / "data"
    return sync.main(["--csv", str(csv_path), "--saida", str(saida),
                      "--id-secret", SEGREDO_TESTE, *flags])


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

class TestNormalizacao:
    def test_cabecalhos_com_espacos_extras_sao_reconhecidos(self):
        mapa = sync.mapa_colunas(CABECALHO)
        for chave in sync.COLUNAS_OBRIGATORIAS:
            assert chave in mapa
        assert mapa["nome"] == 1
        assert mapa["whatsapp"] == 10

    def test_estado_com_nome_completo_converte_para_uf(self):
        assert sync.normalizar_uf("RJ - Rio de Janeiro") == "RJ"
        assert sync.normalizar_uf("SP - São Paulo") == "SP"
        assert sync.normalizar_uf("rj") == "RJ"
        assert sync.normalizar_uf("São Paulo") == "SP"
        assert sync.normalizar_uf("XX - Lugar Nenhum") is None
        assert sync.normalizar_uf("") is None

    def test_numero_brasileiro_e_normalizado(self):
        assert sync.normalizar_whatsapp("21999999999") == "5521999999999"
        assert sync.normalizar_whatsapp("(21) 99999-9999") == "5521999999999"
        assert sync.normalizar_whatsapp("+55 21 99999 9999") == "5521999999999"
        assert sync.normalizar_whatsapp("5521999999999") == "5521999999999"
        # não duplica código do país; lixo de 15 dígitos é rejeitado
        assert sync.normalizar_whatsapp("5521999999999") == "5521999999999"
        assert sync.normalizar_whatsapp("555521999999999") is None
        # fixo e incompleto rejeitados
        assert sync.normalizar_whatsapp("2122223333") is None
        assert sync.normalizar_whatsapp("999999999") is None

    def test_consentimento_exato_e_rejeita_texto_arbitrario(self):
        assert sync.consentimento_valido(CONSENTIMENTO) is True
        assert sync.consentimento_valido(CONSENTIMENTO + " ") is True
        assert sync.consentimento_valido("Concordo com tudo") is False
        assert sync.consentimento_valido("Sim") is False
        assert sync.consentimento_valido("") is False

    def test_slug_compativel_com_frontend(self):
        assert sync.slug("ID_Com_Pontuação!") == "id-com-pontuacao"


# ---------------------------------------------------------------------------
# Regras de publicação (§3: fail-closed em tudo)
# ---------------------------------------------------------------------------

class TestRegrasDePublicacao:
    def test_aprovado_e_ativo_e_elegivel(self):
        catalogo, contagem, _ = montar([linha()])
        assert contagem["publicados"] == 1
        registro = catalogo["profissionais"][0]
        assert registro["nome"] == "Maria da Silva"
        assert registro["uf"] == "SP"
        assert registro["estado"] == "São Paulo"
        assert registro["whatsapp"] == "5519999990001"
        assert registro["bairros"] == ["Taquaral", "Centro"]
        assert registro["outros_municipios"] == ["Valinhos"]
        assert registro["atendimento_remoto"] is True
        assert registro["atualizadoEm"] == "2026-10-02"

    def test_pendente_nao_e_publicado(self):
        _, contagem, _ = montar([linha(status="PENDENTE")])
        assert contagem["publicados"] == 0 and contagem["pendentes"] == 1

    def test_rejeitado_nao_e_publicado(self):
        _, contagem, _ = montar([linha(status="REJEITADO")])
        assert contagem["publicados"] == 0 and contagem["rejeitados"] == 1

    def test_inativo_nao_e_publicado(self):
        _, contagem, _ = montar([linha(status="INATIVO")])
        assert contagem["publicados"] == 0 and contagem["inativos"] == 1

    def test_ativo_nao_sim_nao_e_publicado(self):
        _, contagem, _ = montar([linha(ativo="NÃO")])
        assert contagem["publicados"] == 0

    def test_ativo_vazio_nao_e_interpretado_como_aprovacao(self):
        _, contagem, avisos = montar([linha(ativo="")])
        assert contagem["publicados"] == 0
        assert any("ATIVO" in aviso for aviso in avisos)

    def test_sem_consentimento_valido_nao_e_publicado(self):
        _, contagem, _ = montar([linha(consentimento="sim, mas duvidoso")])
        assert contagem["publicados"] == 0 and contagem["sem_consentimento"] == 1

    def test_whatsapp_invalido_nao_e_publicado(self):
        _, contagem, avisos = montar([linha(whatsapp="19 3232-0000")])
        assert contagem["publicados"] == 0
        assert any("WhatsApp" in aviso for aviso in avisos)

    def test_status_vazio_tratado_como_pendente(self):
        _, contagem, _ = montar([linha(status="")])
        assert contagem["publicados"] == 0 and contagem["pendentes"] == 1

    def test_desativar_profissional_publicado_remove_da_saida(self):
        ativo = montar([linha()])[0]
        desativado = montar([linha(ativo="NÃO")])[0]
        assert len(ativo["profissionais"]) == 1
        assert len(desativado["profissionais"]) == 0

    def test_alteracao_na_planilha_reflete_no_catalogo(self):
        antes = montar([linha(descricao="Pintura residencial.")])[0]
        depois = montar([linha(descricao="Pintura residencial e comercial.")])[0]
        assert antes["profissionais"][0]["descricao"] != depois["profissionais"][0]["descricao"]


# ---------------------------------------------------------------------------
# Privacidade: allowlist estrita
# ---------------------------------------------------------------------------

class TestPrivacidade:
    def test_json_contem_somente_campos_publicos(self):
        catalogo, _, _ = montar([linha()])
        registro = catalogo["profissionais"][0]
        assert set(registro.keys()) == set(sync.CAMPOS_PUBLICOS)
        texto = json.dumps(catalogo, ensure_ascii=False)
        assert "maria@exemplo.com" not in texto          # e-mail
        assert "Rua das Flores" not in texto             # endereço comercial
        assert "anotacao interna" not in texto           # observações
        assert CONSENTIMENTO not in texto                # consentimento bruto
        assert "APROVADO" not in texto                   # status administrativo

    def test_validador_rejeita_campo_privado_vazado(self):
        catalogo, _, _ = montar([linha()])
        catalogo["profissionais"][0]["email_administrativo"] = "vazado@exemplo.com"
        valido, erros = sync.validar_catalogo({**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert not valido and any("privado" in e for e in erros)


# ---------------------------------------------------------------------------
# Identificadores públicos
# ---------------------------------------------------------------------------

class TestIdentificadores:
    def test_id_deterministico_entre_execucoes(self):
        id1 = montar([linha()])[0]["profissionais"][0]["id"]
        id2 = montar([linha()])[0]["profissionais"][0]["id"]
        assert id1 == id2 and sync.REGEX_ID.match(id1)

    def test_id_muda_com_segredo_diferente(self):
        mapa = sync.mapa_colunas(CABECALHO)
        catalogo1, _, _ = sync.montar_catalogo([linha()], mapa, "segredo-a")
        catalogo2, _, _ = sync.montar_catalogo([linha()], mapa, "segredo-b")
        assert catalogo1["profissionais"][0]["id"] != catalogo2["profissionais"][0]["id"]

    def test_id_nao_expose_telefone_ou_carimbo(self):
        registro = montar([linha()])[0]["profissionais"][0]
        assert "19999990001" not in registro["id"]
        assert "01/10/2026" not in registro["id"]

    def test_id_publico_da_planilha_e_respeitado(self):
        catalogo, _, _ = montar([linha(id="maria-campinas-001")])
        assert catalogo["profissionais"][0]["id"] == "maria-campinas-001"

    def test_duplicado_por_telefone_profissao_municipio(self):
        catalogo, contagem, avisos = montar([
            linha(descricao="primeiro envio", timestamp="01/10/2026 09:00:00"),
            linha(descricao="reenvio acidental", timestamp="05/10/2026 09:00:00"),
        ])
        assert contagem["publicados"] == 1
        assert contagem["duplicados"] == 1
        assert catalogo["profissionais"][0]["descricao"] == "reenvio acidental"


# ---------------------------------------------------------------------------
# Escrita, atomicidade e falhas
# ---------------------------------------------------------------------------

class TestEscritaEFalhas:
    def test_end_to_end_csv_escreve_profissionais_json_e_blocos(self, tmp_path):
        saida = tmp_path / "data"
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [
            linha(),
            linha(nome="João Souza", uf="MG - Minas Gerais", municipio="Belo Horizonte",
                  whatsapp="31988880002", bairros="Centro", remoto="Não"),
        ])
        codigo = sync.main(["--csv", str(csv_path), "--saida", str(saida),
                            "--id-secret", SEGREDO_TESTE, "--verbose"])
        assert codigo == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 2
        assert (saida / "uf" / "sp.json").exists()
        assert (saida / "uf" / "mg.json").exists()

    def test_falha_de_estrutura_preserva_catalogo(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        original = (saida / "profissionais.json").read_text(encoding="utf-8")

        csv_ruim = tmp_path / "ruim.csv"
        csv_ruim.write_text("Coluna A,Coluna B\nv1,v2\n", encoding="utf-8")
        codigo = sync.main(["--csv", str(csv_ruim), "--saida", str(saida)])
        assert codigo == 1
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_falha_da_api_nao_apaga_catalogo_anterior(self, tmp_path, monkeypatch):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        original = (saida / "profissionais.json").read_text(encoding="utf-8")

        def explodir(*args, **kwargs):
            raise RuntimeError("credenciais inválidas")

        monkeypatch.setattr(sync, "buscar_linhas_google", explodir)
        monkeypatch.setenv("GOOGLE_SHEET_ID", "abc")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type": "service_account"}')
        codigo = sync.main(["--saida", str(saida), "--id-secret", SEGREDO_TESTE])
        assert codigo == 1
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_sem_id_secret_modo_publicar_falha(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PUBLIC_ID_SECRET", raising=False)
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [linha()])
        codigo = sync.main(["--csv", str(csv_path), "--saida", str(tmp_path / "d"), "--publicar"])
        assert codigo == 1

    def test_simulacao_nao_grava_nem_exige_segreDo(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PUBLIC_ID_SECRET", raising=False)
        csv_path = tmp_path / "planilha.csv"
        escrever_csv(csv_path, [linha()])
        saida = tmp_path / "data"
        codigo = sync.main(["--csv", str(csv_path), "--saida", str(saida), "--dry-run"])
        assert codigo == 0
        assert not (saida / "profissionais.json").exists()

    def test_sem_mudancas_reais_preserva_arquivo(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        original = (saida / "profissionais.json").read_text(encoding="utf-8")
        assert executar(tmp_path, [linha()]) == 0
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_bloco_uf_obsoleto_e_removido(self, tmp_path):
        saida = tmp_path / "data"
        escrever_csv(tmp_path / "com_mg.csv", [linha(), linha(
            nome="João Souza", uf="MG - Minas Gerais", municipio="Belo Horizonte",
            whatsapp="31988880002")])
        assert sync.main(["--csv", str(tmp_path / "com_mg.csv"), "--saida", str(saida),
                          "--id-secret", SEGREDO_TESTE]) == 0
        assert (saida / "uf" / "mg.json").exists()
        assert executar(tmp_path, [linha()]) == 0
        assert not (saida / "uf" / "mg.json").exists()

    def test_migracao_remove_catalogo_json_antigo(self, tmp_path):
        saida = tmp_path / "data"
        saida.mkdir(parents=True)
        (saida / "catalogo.json").write_text("{}", encoding="utf-8")
        assert executar(tmp_path, [linha()]) == 0
        assert not (saida / "catalogo.json").exists()
        assert (saida / "profissionais.json").exists()


# ---------------------------------------------------------------------------
# Validação e consistência
# ---------------------------------------------------------------------------

class TestValidacao:
    def base(self):
        catalogo = montar([linha()])[0]
        catalogo["geradoEm"] = "2026-10-28T12:00:00Z"
        return catalogo

    def test_catalogo_valido_passa(self):
        valido, erros = sync.validar_catalogo(self.base())
        assert valido, erros

    def test_estado_incoerente_com_uf_rejeitado(self):
        catalogo = self.base()
        catalogo["profissionais"][0]["estado"] = "Minas Gerais"
        assert not sync.validar_catalogo(catalogo)[0]

    def test_total_incoerente_rejeitado(self):
        catalogo = self.base()
        catalogo["total"] = 99
        assert not sync.validar_catalogo(catalogo)[0]


class TestSemRegistros:
    def test_apenas_pendentes_gera_catalogo_valido_e_vazio(self):
        catalogo, contagem, _ = montar([linha(status="PENDENTE"), linha(status="REJEITADO")])
        assert catalogo["profissionais"] == [] and catalogo["total"] == 0
        valido, erros = sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert valido, erros

    def test_aviso_nao_expose_dados_pessoais(self):
        _, _, avisos = montar([linha(whatsapp="1932320000", nome="Fulana Secreta",
                                     email="secreto@exemplo.com")])
        texto = " ".join(avisos)
        assert "Fulana" not in texto and "secreto" not in texto


class TestCatalogoDoRepositorio:
    def test_catalogo_inicial_passa_na_validacao(self):
        dados = json.loads((RAIZ / "public" / "data" / "profissionais.json").read_text(encoding="utf-8"))
        valido, erros = sync.validar_catalogo(dados)
        assert valido, erros
        assert dados["total"] == 0  # produção começa vazia

    def test_modelo_de_planilha_real_e_processavel(self):
        linhas = sync.ler_csv(str(RAIZ / "scripts" / "modelo_planilha.csv"))
        mapa = sync.mapa_colunas(linhas[0])
        catalogo, contagem, _ = sync.montar_catalogo(linhas[1:], mapa, SEGREDO_TESTE)
        assert contagem["publicados"] == 1 and contagem["pendentes"] == 1
        valido, erros = sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert valido, erros
