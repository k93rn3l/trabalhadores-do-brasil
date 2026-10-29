"""Testes do sincronizador no modelo de PUBLICAÇÃO AUTOMÁTICA com moderação
por exceção. Fixtures sintéticas (nenhum dado real), estrutura idêntica à da
planilha real: coluna "Email" verificada + colunas administrativas.
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

# (título na planilha, chave interna) — estrutura real, com espaços extras.
COLUNAS_MODELO = [
    ("Carimbo de data/hora", "timestamp"),
    ("Email", "email_verificado"),
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
    ("E-mail administrativo", "email_administrativo"),
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
    "email_verificado": "maria@exemplo.com",
    "nome": "Maria da Silva",
    "categoria": "Beleza e estética",
    "profissao": "Cabelereira",
    "descricao": "Cortes e coloração a domicílio com hora marcada.",
    "uf": "SP - São Paulo",
    "municipio": "Campinas",
    "bairros": "Taquaral; Centro",
    "outros_municipios": "Valinhos",
    "remoto": "Sim",
    "whatsapp": "19999990001",
    "email_administrativo": "contato@exemplo.com",
    "endereco": "Rua das Flores, 123",
    "consentimento": CONSENTIMENTO,
    "id": "",
    "status": "",           # vazio: publicação automática
    "data_aprovacao": "",
    "data_atualizacao": "",
    "observacoes": "anotacao interna sensivel",
    "ativo": "",            # vazio NÃO bloqueia no modelo automático
}


def linha(**sobrescritas) -> list[str]:
    valores = dict(PADRAO)
    valores.update(sobrescritas)
    return [valores[chave] for _, chave in COLUNAS_MODELO]


def montar(linhas, ids_publicados=None):
    mapa = sync.mapa_colunas(CABECALHO)
    return sync.montar_catalogo(linhas, mapa, SEGREDO_TESTE, ids_publicados or {})


def escrever_csv(caminho: Path, linhas: list[list[str]]) -> None:
    import csv

    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        csv.writer(arquivo).writerows([CABECALHO, *linhas])


def executar(tmp_path: Path, linhas, *flags: str) -> int:
    csv_path = tmp_path / "planilha.csv"
    escrever_csv(csv_path, list(linhas))
    return sync.main(["--csv", str(csv_path), "--saida", str(tmp_path / "data"),
                      "--id-secret", SEGREDO_TESTE, *flags])


# ---------------------------------------------------------------------------
# 1. Novo cadastro: publicação automática
# ---------------------------------------------------------------------------

class TestNovoCadastro:
    def test_status_vazio_publica_automaticamente(self):
        catalogo, contagem, _ = montar([linha()])
        assert contagem["publicados"] == 1
        registro = catalogo["profissionais"][0]
        assert registro["nome"] == "Maria da Silva"
        assert registro["uf"] == "SP" and registro["estado"] == "São Paulo"
        assert registro["whatsapp"] == "5519999990001"
        assert registro["bairros"] == ["Taquaral", "Centro"]
        assert registro["atendimento_remoto"] is True
        assert registro["atualizadoEm"] == "2026-10-01"  # do carimbo

    def test_ativo_vazio_nao_bloqueia(self):
        _, contagem, _ = montar([linha(ativo="")])
        assert contagem["publicados"] == 1 and contagem["bloqueados"] == 0

    def test_ativo_sim_publica(self):
        _, contagem, _ = montar([linha(ativo="SIM")])
        assert contagem["publicados"] == 1

    def test_validacoes_essenciais(self):
        for campo, valor in [("whatsapp", "19 3232-0000"), ("uf", "XX - Lugar"),
                             ("municipio", "  "), ("descricao", ""),
                             ("consentimento", "concordo com tudo")]:
            _, contagem, _ = montar([linha(**{campo: valor})])
            assert contagem["publicados"] == 0 and contagem["invalidos"] == 1, campo


# ---------------------------------------------------------------------------
# 2/3. Edição automática e identificador estável
# ---------------------------------------------------------------------------

class TestEdicaoEIdentidade:
    def test_edicao_da_resposta_atualiza_o_publicado(self):
        antes = montar([linha()])[0]["profissionais"][0]
        depois = montar([linha(descricao="Agora também faz escova e penteados.")])[0]["profissionais"][0]
        assert depois["descricao"] != antes["descricao"]

    def test_mudanca_de_telefone_preserva_o_id(self):
        id_antes = montar([linha()])[0]["profissionais"][0]["id"]
        id_depois = montar([linha(whatsapp="11988887777")])[0]["profissionais"][0]["id"]
        assert id_antes == id_depois  # ID deriva do e-mail verificado

    def test_id_e_deterministico_e_nao_expoe_dados(self):
        id1 = montar([linha()])[0]["profissionais"][0]["id"]
        id2 = montar([linha()])[0]["profissionais"][0]["id"]
        assert id1 == id2 and sync.REGEX_ID.match(id1)
        assert "maria" not in id1 and "19999990001" not in id1

    def test_id_publico_manual_e_respeitado(self):
        catalogo, _, _ = montar([linha(id="maria-campinas-001")])
        assert catalogo["profissionais"][0]["id"] == "maria-campinas-001"

    def test_migracao_preserva_id_ja_publicado(self):
        # Catálogo legado: WhatsApp já publicado com ID antigo -> reutiliza.
        ids_legado = {"5519999990001": ["id-antigo-abc"]}
        catalogo, _, _ = montar([linha()], ids_publicados=ids_legado)
        assert catalogo["profissionais"][0]["id"] == "id-antigo-abc"


# ---------------------------------------------------------------------------
# 4. Bloqueio administrativo persistente
# ---------------------------------------------------------------------------

class TestBloqueio:
    @pytest.mark.parametrize("status", ["REJEITADO", "INATIVO"])
    def test_status_bloqueante_impede_publicacao(self, status):
        _, contagem, _ = montar([linha(status=status)])
        assert contagem["publicados"] == 0 and contagem["bloqueados"] == 1

    def test_ativo_nao_impede_publicacao(self):
        _, contagem, _ = montar([linha(ativo="NÃO")])
        assert contagem["publicados"] == 0 and contagem["bloqueados"] == 1

    def test_edicao_nao_reativa_bloqueio(self):
        # profissional bloqueado edita a resposta (dados mudam) — segue bloqueado
        _, contagem, _ = montar([
            linha(status="REJEITADO", whatsapp="11977776666",
                  descricao="Novos serviços após edição."),
        ])
        assert contagem["publicados"] == 0 and contagem["bloqueados"] == 1

    def test_exclusao_da_linha_remove_do_catalogo(self):
        com = montar([linha(), linha(email_verificado="outro@exemplo.com",
                                     nome="João Souza", whatsapp="31988880002",
                                     municipio="Belo Horizonte", uf="MG - Minas Gerais")])[0]
        sem = montar([linha()])[0]
        assert len(com["profissionais"]) == 2
        assert len(sem["profissionais"]) == 1

    def test_pendente_e_retido_para_revisao(self):
        _, contagem, avisos = montar([linha(status="PENDENTE")])
        assert contagem["publicados"] == 0 and contagem["pendentes"] == 1
        assert any("PENDENTE" in a for a in avisos)

    def test_status_desconhecido_e_retido(self):
        _, contagem, _ = montar([linha(status="QUALQUER")])
        assert contagem["publicados"] == 0 and contagem["pendentes"] == 1


# ---------------------------------------------------------------------------
# 5/6. Suspeitos: retenção por exceção
# ---------------------------------------------------------------------------

class TestSuspeitos:
    def test_nome_de_uma_palavra_e_retido(self):
        _, contagem, _ = montar([linha(nome="Marcelo")])
        assert contagem["retidos"] == 1 and contagem["publicados"] == 0

    def test_descricao_curta_e_retida(self):
        _, contagem, _ = montar([linha(descricao="Corto cabelo.")])
        assert contagem["retidos"] == 1

    def test_link_na_descricao_e_retido(self):
        _, contagem, _ = montar([linha(descricao="Veja meus serviços em www.spam.com.br agora.")])
        assert contagem["retidos"] == 1

    def test_sem_email_verificado_e_retido(self):
        _, contagem, _ = montar([linha(email_verificado="")])
        assert contagem["retidos"] == 1

    def test_telefone_em_tres_contas_e_retido(self):
        _, contagem, _ = montar([
            linha(email_verificado="a@exemplo.com", whatsapp="19999990001", municipio="Campinas"),
            linha(email_verificado="b@exemplo.com", nome="João Souza", whatsapp="19999990001",
                  municipio="Santos"),
            linha(email_verificado="c@exemplo.com", nome="Ana Lima", whatsapp="19999990001",
                  municipio="Jundiaí"),
        ])
        assert contagem["retidos"] == 3 and contagem["publicados"] == 0

    def test_aprovado_administrativo_libera_suspeito(self):
        # STATUS=APROVADO = chancela: publica mesmo com indício de suspeita
        _, contagem, _ = montar([linha(nome="Marcelo", status="APROVADO",
                                       data_aprovacao="05/10/2026")])
        assert contagem["publicados"] == 1 and contagem["retidos"] == 0


# ---------------------------------------------------------------------------
# Duplicações
# ---------------------------------------------------------------------------

class TestDuplicacoes:
    def test_mesmo_email_mantem_versao_mais_recente(self):
        catalogo, contagem, _ = montar([
            linha(timestamp="01/10/2026 09:00:00", descricao="Primeiro envio."),
            linha(timestamp="05/10/2026 09:00:00", descricao="Reenvio corrigido."),
        ])
        assert contagem["publicados"] == 1 and contagem["duplicados"] == 1
        assert catalogo["profissionais"][0]["descricao"] == "Reenvio corrigido."

    def test_mesmo_whatsapp_profissao_municipio(self):
        catalogo, contagem, _ = montar([
            linha(email_verificado="a@exemplo.com", timestamp="01/10/2026 09:00:00"),
            linha(email_verificado="b@exemplo.com", timestamp="05/10/2026 09:00:00",
                  descricao="Outra conta, mesmo anúncio."),
        ])
        assert contagem["publicados"] == 1 and contagem["duplicados"] == 1


# ---------------------------------------------------------------------------
# 7. Privacidade: allowlist
# ---------------------------------------------------------------------------

class TestPrivacidade:
    def test_json_somente_com_campos_publicos(self):
        catalogo, _, _ = montar([linha()])
        registro = catalogo["profissionais"][0]
        assert set(registro.keys()) == set(sync.CAMPOS_PUBLICOS)
        texto = json.dumps(catalogo, ensure_ascii=False)
        for proibido in ["maria@exemplo.com", "contato@exemplo.com",
                         "Rua das Flores", "anotacao interna", CONSENTIMENTO]:
            assert proibido not in texto, proibido

    def test_validador_rejeita_vazamento(self):
        catalogo, _, _ = montar([linha()])
        catalogo["profissionais"][0]["email_verificado"] = "vazado@exemplo.com"
        valido, erros = sync.validar_catalogo({**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert not valido and any("privado" in e for e in erros)


# ---------------------------------------------------------------------------
# 8. Dry-run com comparação ao catálogo publicado
# ---------------------------------------------------------------------------

class TestComparacaoDryRun:
    def test_contagens_novos_removidos_alterados(self, tmp_path):
        saida = tmp_path / "data"
        # 1ª execução grava 2 profissionais
        assert executar(tmp_path, [linha(), linha(
            email_verificado="joao@exemplo.com", nome="João Souza",
            whatsapp="31988880002", municipio="Belo Horizonte",
            uf="MG - Minas Gerais")]) == 0

        # Previsto: remove João, altera Maria, adiciona Ana
        comparavel = montar([
            linha(descricao="Descrição nova após edição."),
            linha(email_verificado="ana@exemplo.com", nome="Ana Lima",
                  whatsapp="21988880003", municipio="Niterói", uf="RJ - Rio de Janeiro"),
        ], ids_publicados=sync.carregar_ids_publicados(saida))[0]
        resultado = sync.comparar_com_atual(saida, comparavel)
        assert resultado == {"novos": 1, "removidos": 1, "alterados": 1, "mantidos": 0}

    def test_dry_run_imprime_comparacao_e_nao_grava(self, tmp_path, capsys):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        codigo = executar(tmp_path, [linha(descricao="Descrição nova.")], "--dry-run")
        assert codigo == 0
        texto = capsys.readouterr().out
        assert "novos: 0" in texto and "alterados: 1" in texto
        assert "Nada foi gravado" in texto


# ---------------------------------------------------------------------------
# 9. Escrita, atomicidade e falhas
# ---------------------------------------------------------------------------

class TestEscritaEFalhas:
    def test_end_to_end_escreve_profissionais_json_e_blocos(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha(), linha(
            email_verificado="joao@exemplo.com", nome="João Souza",
            whatsapp="31988880002", municipio="Belo Horizonte",
            uf="MG - Minas Gerais")], "--verbose") == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 2
        assert (saida / "uf" / "sp.json").exists()
        assert (saida / "uf" / "mg.json").exists()

    def test_sincronizacao_sem_mudancas_preserva_arquivo(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        original = (saida / "profissionais.json").read_text(encoding="utf-8")
        assert executar(tmp_path, [linha()]) == 0
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_falha_de_estrutura_preserva_catalogo(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        original = (saida / "profissionais.json").read_text(encoding="utf-8")
        ruim = tmp_path / "ruim.csv"
        ruim.write_text("Coluna A,Coluna B\nv1,v2\n", encoding="utf-8")
        assert sync.main(["--csv", str(ruim), "--saida", str(saida)]) == 1
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_falha_da_api_nao_apaga_catalogo(self, tmp_path, monkeypatch):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        original = (saida / "profissionais.json").read_text(encoding="utf-8")

        def explodir(*a, **k):
            raise RuntimeError("credenciais inválidas")

        monkeypatch.setattr(sync, "buscar_linhas_google", explodir)
        monkeypatch.setenv("GOOGLE_SHEET_ID", "abc")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type": "service_account"}')
        assert sync.main(["--saida", str(saida), "--id-secret", SEGREDO_TESTE]) == 1
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_sem_id_secret_modo_publicar_falha(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PUBLIC_ID_SECRET", raising=False)
        csv_path = tmp_path / "p.csv"
        escrever_csv(csv_path, [linha()])
        assert sync.main(["--csv", str(csv_path), "--saida", str(tmp_path / "d"),
                          "--publicar"]) == 1

    def test_bloco_uf_obsoleto_e_removido(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha(), linha(
            email_verificado="joao@exemplo.com", nome="João Souza",
            whatsapp="31988880002", municipio="Belo Horizonte",
            uf="MG - Minas Gerais")]) == 0
        assert (saida / "uf" / "mg.json").exists()
        assert executar(tmp_path, [linha()]) == 0
        assert not (saida / "uf" / "mg.json").exists()


# ---------------------------------------------------------------------------
# Normalização e estrutura (mantidos do modelo anterior)
# ---------------------------------------------------------------------------

class TestNormalizacao:
    def test_cabecalhos_com_espacos_extras(self):
        mapa = sync.mapa_colunas(CABECALHO)
        for chave in sync.COLUNAS_OBRIGATORIAS:
            assert chave in mapa
        assert mapa["email_verificado"] == 1
        assert mapa["email_administrativo"] == 12

    def test_uf_formato_do_formulario(self):
        assert sync.normalizar_uf("RJ - Rio de Janeiro") == "RJ"
        assert sync.normalizar_uf("SP - São Paulo") == "SP"
        assert sync.normalizar_uf("São Paulo") == "SP"
        assert sync.normalizar_uf("") is None

    def test_whatsapp_normalizado(self):
        assert sync.normalizar_whatsapp("21999999999") == "5521999999999"
        assert sync.normalizar_whatsapp("(21) 99999-9999") == "5521999999999"
        assert sync.normalizar_whatsapp("2122223333") is None

    def test_consentimento_exato_e_rejeita_arbitrario(self):
        assert sync.consentimento_valido(CONSENTIMENTO) is True
        assert sync.consentimento_valido("Concordo com tudo") is False

    def test_email_normalizado(self):
        assert sync.normalizar_email(" Maria@Exemplo.COM ") == "maria@exemplo.com"
        assert sync.normalizar_email("sem-arroba") == ""


class TestValidacao:
    def base(self):
        catalogo = montar([linha()])[0]
        catalogo["geradoEm"] = "2026-10-28T12:00:00Z"
        return catalogo

    def test_catalogo_valido_passa(self):
        valido, erros = sync.validar_catalogo(self.base())
        assert valido, erros

    def test_total_incoerente_rejeitado(self):
        catalogo = self.base()
        catalogo["total"] = 99
        assert not sync.validar_catalogo(catalogo)[0]


class TestSemRegistros:
    def test_so_registros_retidos_gera_catalogo_valido_e_vazio(self):
        catalogo, _, _ = montar([linha(status="PENDENTE"), linha(status="REJEITADO"),
                                 linha(nome="SemNome")])
        assert catalogo["profissionais"] == [] and catalogo["total"] == 0
        valido, erros = sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert valido, erros

    def test_aviso_nao_expose_dados_pessoais(self):
        _, _, avisos = montar([linha(whatsapp="1932320000", nome="Fulana Secreta",
                                     email_verificado="secreto@exemplo.com")])
        texto = " ".join(avisos)
        assert "Fulana" not in texto and "secreto" not in texto


class TestCatalogoDoRepositorio:
    def test_catalogo_inicial_valido_e_vazio(self):
        dados = json.loads((RAIZ / "public" / "data" / "profissionais.json").read_text(encoding="utf-8"))
        valido, erros = sync.validar_catalogo(dados)
        assert valido, erros
        assert dados["total"] == 0

    def test_modelo_de_planilha_processavel(self):
        linhas = sync.ler_csv(str(RAIZ / "scripts" / "modelo_planilha.csv"))
        mapa = sync.mapa_colunas(linhas[0])
        catalogo, contagem, _ = sync.montar_catalogo(linhas[1:], mapa, SEGREDO_TESTE)
        assert contagem["publicados"] == 1   # Maria (STATUS vazio) publica
        assert contagem["pendentes"] == 1    # João (PENDENTE) fica retido
        valido, erros = sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert valido, erros
