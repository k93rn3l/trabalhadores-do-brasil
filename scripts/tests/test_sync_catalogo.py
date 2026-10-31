"""Testes do sincronizador: publicação automática com moderação por exceção,
sinais fracos × fortes, IDs estáveis por identidade e relatório de moderação.
Fixtures sintéticas — nenhum dado real.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
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
    (" Instagram (@) ", "instagram"),
    ("E-mail administrativo", "email_administrativo"),
    ("Endereço comercial", "endereco"),
    ("Consentimento para publicação", "consentimento"),
    ("ID_PUBLICO", "id"),
    ("STATUS", "status"),
    ("ATIVO", "ativo"),
    ("DATA_APROVACAO", "data_aprovacao"),
    ("DATA_ATUALIZACAO", "data_atualizacao"),
    ("OBSERVACOES_INTERNAS", "observacoes"),
    (" Solicitar exclusão do perfil ", "solicitar_exclusao"),
    ("ID_RESPOSTA_FORM", "id_resposta_form"),
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
    "instagram": "",
    "email_administrativo": "contato@exemplo.com",
    "endereco": "Rua das Flores, 123",
    "consentimento": CONSENTIMENTO,
    "id": "",
    "status": "",
    "data_aprovacao": "",
    "data_atualizacao": "",
    "observacoes": "anotacao interna sensivel",
    "ativo": "",
    "solicitar_exclusao": "",
    "id_resposta_form": "",
}


def linha(**sobrescritas) -> list[str]:
    valores = dict(PADRAO)
    valores.update(sobrescritas)
    return [valores[chave] for _, chave in COLUNAS_MODELO]


def montar(linhas, mapa_identidades=None, ids_publicados=None, mapa_exclusoes=None):
    mapa = sync.mapa_colunas(CABECALHO)
    return sync.montar_catalogo(
        linhas, mapa, SEGREDO_TESTE, mapa_identidades or {}, ids_publicados or {},
        mapa_exclusoes or {},
    )


def escrever_csv(caminho: Path, linhas: list[list[str]]) -> None:
    import csv

    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        csv.writer(arquivo).writerows([CABECALHO, *linhas])


def executar(tmp_path: Path, linhas, *flags: str) -> int:
    csv_path = tmp_path / "planilha.csv"
    escrever_csv(csv_path, list(linhas))
    return sync.main([
        "--csv", str(csv_path), "--saida", str(tmp_path / "data"),
        "--dir-dados", str(tmp_path / "dados"),
        "--id-secret", SEGREDO_TESTE, *flags,
    ])


# ---------------------------------------------------------------------------
# 1. Novo cadastro: publicação automática
# ---------------------------------------------------------------------------

class TestNovoCadastro:
    def test_status_vazio_publica_automaticamente(self):
        catalogo, contagem, *_ = montar([linha()])
        assert contagem["publicados"] == 1
        registro = catalogo["profissionais"][0]
        assert registro["nome"] == "Maria da Silva"
        assert registro["uf"] == "SP" and registro["estado"] == "São Paulo"
        assert registro["whatsapp"] == "5519999990001"
        assert registro["atualizadoEm"] == "2026-10-01"

    def test_validacoes_essenciais_recusam(self):
        for campo, valor in [("whatsapp", "19 3232-0000"), ("uf", "XX - Lugar"),
                             ("municipio", "  "), ("descricao", ""),
                             ("consentimento", "concordo com tudo")]:
            _, contagem, *_ = montar([linha(**{campo: valor})])
            assert contagem["publicados"] == 0 and contagem["invalidos"] == 1, campo


# ---------------------------------------------------------------------------
# 2. Sinais fracos NÃO retêm; fortes retêm
# ---------------------------------------------------------------------------

class TestSinaisFracosVSFortes:
    def test_nome_de_uma_palavra_publica_com_sinal(self):
        _, contagem, avisos, _, eventos, _ = montar([linha(nome="Renata")])
        assert contagem["publicados"] == 1 and contagem["retidos"] == 0
        assert any("sinal fraco" in a for a in avisos)
        assert eventos["sinais_fracos"] and eventos["sinais_fracos"][0]["linha"] == 2

    def test_descricao_curta_publica_com_sinal(self):
        _, contagem, _, _, eventos, _ = montar([linha(descricao="Corto cabelo.")])
        assert contagem["publicados"] == 1
        assert any("descrição curta" in e["sinal"] for e in eventos["sinais_fracos"])

    def test_link_na_descricao_publica_com_sinal(self):
        _, contagem, _, _, eventos, _ = montar([
            linha(descricao="Meu portfólio em www.meustrabalhos.com.br com fotos reais.")
        ])
        assert contagem["publicados"] == 1
        assert any("link na descrição" in e["sinal"] for e in eventos["sinais_fracos"])

    def test_link_no_nome_retem(self):
        _, contagem, _, _, eventos, _ = montar([linha(nome="Maria www.promo.com")])
        assert contagem["retidos"] == 1 and contagem["publicados"] == 0
        assert any("link no nome" in ";".join(e["motivos"]) for e in eventos["retidos"])

    def test_sem_nenhum_email_retem(self):
        _, contagem, _, _, eventos, _ = montar([
            linha(email_verificado="", email_administrativo="")
        ])
        assert contagem["retidos"] == 1
        assert any("e-mail" in ";".join(e["motivos"]) for e in eventos["retidos"])

    def test_email_somente_administrativo_publica(self):
        _, contagem, *_ = montar([linha(email_verificado="", email_administrativo="eu@exemplo.com")])
        assert contagem["publicados"] == 1

    def test_telefone_em_tres_contas_retem(self):
        _, contagem, _, _, eventos, _ = montar([
            linha(email_verificado="a@exemplo.com", whatsapp="19999990001", municipio="Campinas"),
            linha(email_verificado="b@exemplo.com", nome="João Souza", whatsapp="19999990001",
                  municipio="Santos"),
            linha(email_verificado="c@exemplo.com", nome="Ana Lima", whatsapp="19999990001",
                  municipio="Jundiaí"),
        ])
        assert contagem["retidos"] == 3 and contagem["publicados"] == 0

    def test_aprovado_libera_de_retencao_por_sinal_forte(self):
        _, contagem, *_ = montar([
            linha(email_verificado="", email_administrativo="", status="APROVADO",
                  data_aprovacao="05/10/2026")
        ])
        assert contagem["publicados"] == 1 and contagem["retidos"] == 0


# ---------------------------------------------------------------------------
# 3. Identificadores estáveis e anti-apropriação
# ---------------------------------------------------------------------------

class TestIdentificadores:
    def test_troca_de_telefone_preserva_id(self):
        id_antes = montar([linha()])[0]["profissionais"][0]["id"]
        id_depois = montar([linha(whatsapp="11988887777")])[0]["profissionais"][0]["id"]
        assert id_antes == id_depois

    def test_id_nao_expoe_dados(self):
        registro = montar([linha()])[0]["profissionais"][0]
        assert "maria" not in registro["id"] and "19999990001" not in registro["id"]

    def test_id_publico_manual_tem_prioridade(self):
        catalogo, *_ = montar([linha(id="maria-campinas-001")])
        assert catalogo["profissionais"][0]["id"] == "maria-campinas-001"

    def test_migracao_preserva_id_publicado_por_telefone(self):
        # Perfil legado publicado com ID antigo e mesmo telefone -> mantém URL.
        ids_legado = {"5519999990001": ["id-antigo-abc"]}
        catalogo, *_ = montar([linha()], ids_publicados=ids_legado)
        assert catalogo["profissionais"][0]["id"] == "id-antigo-abc"

    def test_mapa_de_identidades_tem_prioridade_sobre_telefone(self):
        # Identidade já vinculada no mapa: telefone igual de outro cadastro
        # NÃO apropria o ID (mapa vence a migração por telefone).
        catalogo, *_ = montar([linha()], ids_publicados={"5519999990001": ["id-antigo-abc"]})
        id_maria = catalogo["profissionais"][0]["id"]  # vinculado na 1ª resolução
        mapa = sync.carregar_mapa_identidades(Path("_inexistente_"))
        mapa_teste = {
            # hash de identidade da Maria -> id que ela já tem
            sync._hmac(SEGREDO_TESTE, "identidade", "maria@exemplo.com"): "id-ja-vinculado",
        }
        catalogo2, *_ = montar(
            [linha(email_verificado="outra@exemplo.com", whatsapp="19999990001")],
            mapa_identidades=mapa_teste,
            ids_publicados={"5519999990001": ["id-ja-vinculado"]},
        )
        # "outra" é identidade distinta -> ID próprio derivado, não o vinculado
        assert catalogo2["profissionais"][0]["id"] != "id-ja-vinculado"
        assert id_maria == "id-antigo-abc"

    def test_telefone_com_dois_ids_publicados_nao_migra(self):
        # telefone ambíguo (2 perfis publicados) -> nada de reuso; ID derivado
        ids_legado = {"5519999990001": ["id-a", "id-b"]}
        catalogo, *_ = montar([linha()], ids_publicados=ids_legado)
        assert catalogo["profissionais"][0]["id"] not in {"id-a", "id-b"}


# ---------------------------------------------------------------------------
# 4. Bloqueio persistente e edição
# ---------------------------------------------------------------------------

class TestBloqueioEEdicao:
    @pytest.mark.parametrize("status", ["REJEITADO", "INATIVO"])
    def test_status_bloqueante_impede(self, status):
        _, contagem, _, _, eventos, _ = montar([linha(status=status)])
        assert contagem["publicados"] == 0 and contagem["bloqueados"] == 1
        assert eventos["bloqueados"] and eventos["bloqueados"][0]["linha"] == 2

    def test_ativo_nao_impede(self):
        _, contagem, *_ = montar([linha(ativo="NÃO")])
        assert contagem["publicados"] == 0 and contagem["bloqueados"] == 1

    def test_edicao_nao_reativa_bloqueio(self):
        _, contagem, *_ = montar([
            linha(status="REJEITADO", whatsapp="11977776666",
                  descricao="Novos serviços após edição."),
        ])
        assert contagem["publicados"] == 0 and contagem["bloqueados"] == 1

    def test_edicao_atualiza_publicado(self):
        antes = montar([linha()])[0]["profissionais"][0]
        depois = montar([linha(descricao="Agora também faz escova.")])[0]["profissionais"][0]
        assert depois["descricao"] != antes["descricao"]

    def test_exclusao_da_linha_remove_do_catalogo(self):
        com = montar([linha(), linha(email_verificado="outro@exemplo.com", nome="João Souza",
                                     whatsapp="31988880002", municipio="Belo Horizonte",
                                     uf="MG - Minas Gerais")])[0]
        sem = montar([linha()])[0]
        assert len(com["profissionais"]) == 2 and len(sem["profissionais"]) == 1

    def test_pendente_e_status_desconhecido_retidos(self):
        _, contagem, *_ = montar([linha(status="PENDENTE")])
        assert contagem["pendentes"] == 1 and contagem["publicados"] == 0
        _, contagem, *_ = montar([linha(status="QUALQUER")])
        assert contagem["pendentes"] == 1 and contagem["publicados"] == 0


# ---------------------------------------------------------------------------
# Duplicações
# ---------------------------------------------------------------------------

class TestDuplicacoes:
    def test_mesma_identidade_mantem_mais_recente(self):
        catalogo, contagem, *_ = montar([
            linha(timestamp="01/10/2026 09:00:00", descricao="Primeiro envio."),
            linha(timestamp="05/10/2026 09:00:00", descricao="Reenvio corrigido."),
        ])
        assert contagem["publicados"] == 1 and contagem["duplicados"] == 1
        assert catalogo["profissionais"][0]["descricao"] == "Reenvio corrigido."

    def test_mesmo_whatsapp_profissao_municipio(self):
        catalogo, contagem, *_ = montar([
            linha(email_verificado="a@exemplo.com", timestamp="01/10/2026 09:00:00"),
            linha(email_verificado="b@exemplo.com", timestamp="05/10/2026 09:00:00",
                  descricao="Outra conta, mesmo anúncio."),
        ])
        assert contagem["publicados"] == 1 and contagem["duplicados"] == 1


# ---------------------------------------------------------------------------
# Instagram: campo opcional — inválido não impede a publicação
# ---------------------------------------------------------------------------

class TestInstagramOpcional:
    def test_sem_instagram_publica_com_null(self):
        registro = montar([linha()])[0]["profissionais"][0]
        assert registro["instagram"] is None

    def test_instagram_com_arroba_normaliza_sem_arroba(self):
        registro = montar([linha(instagram="@maria.silva")])[0]["profissionais"][0]
        assert registro["instagram"] == "maria.silva"

    def test_instagram_invalido_publica_sem_o_campo_e_avisa(self):
        catalogo, contagem, avisos, *_ = montar([linha(instagram="instagram.com/maria")])
        assert contagem["publicados"] == 1
        assert catalogo["profissionais"][0]["instagram"] is None
        assert any("instagram" in a.lower() for a in avisos)

    def test_validador_rejeita_instagram_publicado_invalido(self):
        catalogo = montar([linha()])[0]
        for ruim in ["@maria", "https://instagram.com/maria", "a..b", "a" * 31]:
            catalogo["profissionais"][0]["instagram"] = ruim
            assert not sync.validar_catalogo(
                {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})[0], ruim


# ---------------------------------------------------------------------------
# Exclusão voluntária do perfil (coluna "Solicitar exclusão do perfil")
# ---------------------------------------------------------------------------

EXCLUSAO = "Solicito a remoção do meu perfil do catálogo público."

# Planilha antiga, sem a coluna de exclusão: comportamento anterior preservado.
COLUNAS_ANTIGAS = [(titulo, chave) for titulo, chave in COLUNAS_MODELO
                   if chave != "solicitar_exclusao"]
CABECALHO_ANTIGO = [titulo for titulo, _ in COLUNAS_ANTIGAS]


def linha_antiga(**sobrescritas) -> list[str]:
    valores = dict(PADRAO)
    valores.update(sobrescritas)
    return [valores[chave] for _, chave in COLUNAS_ANTIGAS]


class TestExclusaoVoluntaria:
    def test_planilha_sem_a_coluna_mantem_comportamento(self):
        mapa = sync.mapa_colunas(CABECALHO_ANTIGO)
        catalogo, contagem, *_ = sync.montar_catalogo(
            [linha_antiga()], mapa, SEGREDO_TESTE)
        assert contagem["publicados"] == 1
        assert contagem["exclusoes_solicitadas"] == 0 and contagem["excluidos"] == 0

    def test_campo_vazio_publica_normalmente(self):
        _, contagem, *_ = montar([linha()])
        assert contagem["publicados"] == 1 and contagem["excluidos"] == 0

    def test_campo_marcado_novo_cadastro_nao_publica(self):
        catalogo, contagem, *_ = montar([linha(solicitar_exclusao=EXCLUSAO)])
        assert contagem["publicados"] == 0 and contagem["excluidos"] == 1
        assert catalogo["profissionais"] == []

    def test_somente_a_frase_exata_autoriza(self):
        for ruim in ["sim", "remover perfil", EXCLUSAO + " por favor",
                     "quero sair do catalogo", "  "]:
            _, contagem, *_ = montar([linha(solicitar_exclusao=ruim)])
            assert contagem["publicados"] == 1, ruim
            assert contagem["excluidos"] == 0 and contagem["exclusoes_solicitadas"] == 0, ruim

    def test_perfil_publicado_e_removido_na_proxima_sincronizacao(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 1 and (saida / "uf" / "sp.json").exists()

        assert executar(tmp_path, [linha(solicitar_exclusao=EXCLUSAO)]) == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 0
        assert not (saida / "uf" / "sp.json").exists()  # JSON derivado também some

    def test_resposta_antiga_valida_nao_republica_apos_exclusao(self):
        # Mesma identidade: resposta antiga válida + posterior solicitando saída.
        # As DUAS respostas da identidade são suprimidas (contador por linha).
        _, contagem, *_ = montar([
            linha(timestamp="01/10/2026 09:00:00"),
            linha(timestamp="05/10/2026 09:00:00", solicitar_exclusao=EXCLUSAO),
        ])
        assert contagem["publicados"] == 0 and contagem["excluidos"] == 2

    def test_exclusao_persiste_e_desmarcar_nao_reativa(self, tmp_path):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha()]) == 0
        assert executar(tmp_path, [linha(solicitar_exclusao=EXCLUSAO)]) == 0
        # Terceira execução com a caixa DESMARCADA: continua excluído.
        assert executar(tmp_path, [linha()]) == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 0

        conteudo = (dados_dir / "exclusoes.json").read_text(encoding="utf-8")
        assert sync._hmac(SEGREDO_TESTE, "identidade", "maria@exemplo.com") in conteudo
        assert "@" not in conteudo and "maria" not in conteudo  # pseudonimizado

    def test_outros_profissionais_parecidos_nao_sao_excluidos(self):
        catalogo, contagem, *_ = montar([
            linha(email_verificado="sai@exemplo.com", solicitar_exclusao=EXCLUSAO),
            linha(email_verificado="fica@exemplo.com", nome="Maria da Silva Jr.",
                  whatsapp="19999990001", municipio="Sumaré"),
        ])
        assert contagem["publicados"] == 1
        assert catalogo["profissionais"][0]["nome"] == "Maria da Silva Jr."

    def test_mesmo_id_publico_em_outra_identidade_nao_remove_terceiro(self):
        catalogo, contagem, *_ = montar([
            linha(email_verificado="dono@exemplo.com", id="perfil-compartilhado-01"),
            linha(email_verificado="outro@exemplo.com", id="perfil-compartilhado-01",
                  municipio="Sumaré", solicitar_exclusao=EXCLUSAO),
        ])
        assert contagem["publicados"] == 1  # quem pediu saiu; o dono permanece
        assert catalogo["profissionais"][0]["id"] == "perfil-compartilhado-01"

    def test_identidade_ausente_vira_pendencia_sem_excluir_terceiros(self):
        _, contagem, avisos, _, eventos, _ = montar([
            linha(email_verificado="", email_administrativo="",
                  solicitar_exclusao=EXCLUSAO),
            linha(email_verificado="outra@exemplo.com", nome="Outra Pessoa",
                  municipio="Sumaré"),
        ])
        assert contagem["exclusoes_pendentes"] == 1
        assert contagem["excluidos"] == 0
        assert contagem["publicados"] == 1  # a outra identidade segue publicada
        assert eventos["exclusoes_pendentes"] and any("pendência" in a for a in avisos)

    def test_somente_email_administrativo_nao_autoriza_exclusao(self):
        _, contagem, *_ = montar([linha(email_verificado="", solicitar_exclusao=EXCLUSAO)])
        # A solicitação é identificada, mas sem e-mail verificado vira pendência:
        # o perfil não é excluído por causa dela.
        assert contagem["exclusoes_solicitadas"] == 1
        assert contagem["exclusoes_pendentes"] == 1
        assert contagem["excluidos"] == 0
        assert contagem["publicados"] == 1  # o cadastro em si segue a regra normal

    def test_exclusao_prevalece_sobre_status_aprovado(self):
        _, contagem, *_ = montar([
            linha(status="APROVADO", data_aprovacao="05/10/2026",
                  solicitar_exclusao=EXCLUSAO),
        ])
        assert contagem["publicados"] == 0 and contagem["excluidos"] == 1

    def test_contagem_de_perfis_removidos(self):
        catalogo, *_ = montar([linha()])
        id_publicado = catalogo["profissionais"][0]["id"]
        _, contagem, *_ = montar(
            [linha(solicitar_exclusao=EXCLUSAO)],
            ids_publicados={"5519999990001": [id_publicado]},
        )
        assert contagem["exclusoes_solicitadas"] == 1
        assert contagem["exclusoes_perfis_removidos"] == 1

    def test_mapa_de_exclusoes_e_pseudonimizado(self):
        *_, mapa_exclusoes = montar([linha(solicitar_exclusao=EXCLUSAO)])
        assert list(mapa_exclusoes) == [
            sync._hmac(SEGREDO_TESTE, "identidade", "maria@exemplo.com")
        ]
        assert mapa_exclusoes[sync._hmac(SEGREDO_TESTE, "identidade",
                                         "maria@exemplo.com")]["desde"] == "2026-10-01"

    def test_dry_run_nao_persiste_exclusao(self, tmp_path):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha(solicitar_exclusao=EXCLUSAO)]) == 0
        antes = (dados_dir / "exclusoes.json").read_text(encoding="utf-8")
        # Simulação com a caixa desmarcada: nada é gravado nem reativado.
        assert executar(tmp_path, [linha()], "--dry-run") == 0
        assert (dados_dir / "exclusoes.json").read_text(encoding="utf-8") == antes
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 0

    def test_falha_posterior_nao_corrompe_catalogo_nem_exclusoes(self, tmp_path):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha()]) == 0
        assert executar(tmp_path, [linha(solicitar_exclusao=EXCLUSAO)]) == 0
        catalogo_apos = (saida / "profissionais.json").read_text(encoding="utf-8")
        exclusoes_apos = (dados_dir / "exclusoes.json").read_text(encoding="utf-8")

        ruim = tmp_path / "ruim.csv"
        ruim.write_text("Coluna A,Coluna B\nv1,v2\n", encoding="utf-8")
        assert sync.main(["--csv", str(ruim), "--saida", str(saida),
                          "--dir-dados", str(dados_dir), "--id-secret", SEGREDO_TESTE]) == 1
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == catalogo_apos
        assert (dados_dir / "exclusoes.json").read_text(encoding="utf-8") == exclusoes_apos

    def test_json_publico_sem_dados_da_exclusao(self, tmp_path):
        assert executar(tmp_path, [
            linha(),
            linha(email_verificado="sai@exemplo.com", nome="Sai do Ar",
                  whatsapp="19999990002", municipio="Piracicaba",
                  solicitar_exclusao=EXCLUSAO),
        ]) == 0
        texto = (tmp_path / "data" / "profissionais.json").read_text(encoding="utf-8")
        principal = json.loads(texto)
        assert principal["total"] == 1  # os demais profissionais permanecem
        assert "sai@exemplo.com" not in texto and "Sai do Ar" not in texto
        assert "remoção do meu perfil" not in texto
        assert "solicitar_exclusao" not in texto
        assert set(principal["profissionais"][0].keys()) == set(sync.CAMPOS_PUBLICOS)


# ---------------------------------------------------------------------------
# Municípios múltiplos numa única coluna (aba consolidada pelo Apps Script)
# ---------------------------------------------------------------------------

class TestMunicipiosMultiplos:
    def test_lista_na_coluna_unica_primeiro_e_principal(self):
        registro = montar([linha(uf="AC - Acre", outros_municipios="",
                                 municipio="Acrelândia; Bujari; Cruzeiro do Sul; Xapuri")])[0]["profissionais"][0]
        assert registro["municipio"] == "Acrelândia"
        assert registro["municipioSlug"] == "acrelandia"
        assert registro["outros_municipios"] == ["Bujari", "Cruzeiro do Sul", "Xapuri"]
        assert registro["estado"] == "Acre"

    def test_municipio_unico_continua_igual(self):
        registro = montar([linha()])[0]["profissionais"][0]
        assert registro["municipio"] == "Campinas"
        assert registro["outros_municipios"] == ["Valinhos"]

    def test_outros_municipios_existentes_sao_fundidos_sem_duplicar(self):
        registro = montar([linha(municipio="Campinas; Valinhos; Vinhedo",
                                 outros_municipios="Valinhos; Sumaré")])[0]["profissionais"][0]
        assert registro["municipio"] == "Campinas"
        assert registro["outros_municipios"] == ["Valinhos", "Sumaré", "Vinhedo"]


# ---------------------------------------------------------------------------
# Matriz administrativa: STATUS × ATIVO (a exclusão voluntária vem depois
# e prevalece sobre todas as combinações)
# ---------------------------------------------------------------------------

class TestMatrizStatusAtivo:
    @pytest.mark.parametrize("status,ativo,esperado", [
        ("", "", "publicado"),          # publicação automática
        ("", "SIM", "publicado"),
        ("", "NÃO", "bloqueado"),
        ("APROVADO", "", "publicado"),
        ("APROVADO", "SIM", "publicado"),
        ("APROVADO", "NÃO", "bloqueado"),  # ATIVO=NÃO vence a aprovação
        ("PENDENTE", "", "pendente"),
        ("PENDENTE", "SIM", "pendente"),
        ("PENDENTE", "NÃO", "bloqueado"),
        ("REJEITADO", "SIM", "bloqueado"),
        ("REJEITADO", "NÃO", "bloqueado"),
        ("INATIVO", "SIM", "bloqueado"),
        ("INATIVO", "NÃO", "bloqueado"),
        ("QUALQUER", "", "pendente"),        # STATUS desconhecido: retido
        ("APROVADO", "TALVEZ", "pendente"),  # ATIVO desconhecido: retido
    ])
    def test_combinacao_status_ativo(self, status, ativo, esperado):
        _, contagem, *_ = montar([linha(status=status, ativo=ativo,
                                        data_aprovacao="05/10/2026")])
        assert contagem["publicados"] == (1 if esperado == "publicado" else 0)
        assert contagem["pendentes"] == (1 if esperado == "pendente" else 0)
        assert contagem["bloqueados"] == (1 if esperado == "bloqueado" else 0)

    def test_aprovado_nao_contorna_validacoes_essenciais(self):
        _, contagem, *_ = montar([
            linha(status="APROVADO", data_aprovacao="05/10/2026",
                  whatsapp="19 3232-0000"),
        ])
        assert contagem["publicados"] == 0 and contagem["invalidos"] == 1

    def test_bloqueio_diferenciado_por_origem_no_relatorio(self):
        _, contagem, _, _, eventos, _ = montar([
            linha(email_verificado="a@exemplo.com", whatsapp="19999990011",
                  status="REJEITADO"),
            linha(email_verificado="b@exemplo.com", whatsapp="19999990012",
                  municipio="Sumaré", status="INATIVO"),
            linha(email_verificado="c@exemplo.com", whatsapp="19999990013",
                  municipio="Vinhedo", ativo="NÃO"),
        ])
        assert contagem["bloqueados"] == 3
        assert contagem["rejeitados"] == 1
        assert contagem["inativos"] == 1
        assert contagem["bloqueados_por_ativo"] == 1
        assert eventos["rejeitados"][0]["motivo"] == "STATUS=REJEITADO"
        assert eventos["inativos"][0]["motivo"] == "STATUS=INATIVO"
        assert eventos["bloqueados_ativo"][0]["motivo"] == "ATIVO=NÃO"

    def test_valores_administrativos_desconhecidos_ficam_retidos(self):
        _, _, _, _, eventos, _ = montar([
            linha(email_verificado="a@exemplo.com", whatsapp="19999990011",
                  status="CONFERIR"),
            linha(email_verificado="b@exemplo.com", whatsapp="19999990012",
                  municipio="Sumaré", status="APROVADO", data_aprovacao="05/10/2026",
                  ativo="TALVEZ"),
        ])
        motivos = ";".join(e["motivo"] for e in eventos["pendentes"])
        assert "STATUS desconhecido (CONFERIR)" in motivos
        assert "ATIVO com valor desconhecido" in motivos

    @pytest.mark.parametrize("status,ativo", [
        ("", ""), ("APROVADO", "SIM"), ("PENDENTE", ""),
        ("REJEITADO", ""), ("INATIVO", ""), ("", "NÃO"), ("APROVADO", "NÃO"),
    ])
    def test_exclusao_prevalece_sobre_todas_as_combinacoes(self, status, ativo):
        # A supressão por identidade ocorre antes do processamento: a linha
        # nem chega a ser classificada como aprovada, pendente ou bloqueada.
        _, contagem, *_ = montar([
            linha(status=status, ativo=ativo, data_aprovacao="05/10/2026",
                  solicitar_exclusao=EXCLUSAO),
        ])
        assert contagem["publicados"] == 0
        assert contagem["excluidos"] == 1

    @pytest.mark.parametrize("status", ["REJEITADO", "INATIVO"])
    def test_rejeitado_ou_inativo_remove_perfil_publicado(self, status, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha()]) == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 1

        assert executar(tmp_path, [linha(status=status)]) == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 0  # removido do catálogo público
        assert not (saida / "uf" / "sp.json").exists()

    def test_id_resposta_form_e_privado(self, tmp_path):
        assert executar(tmp_path, [linha(id_resposta_form="resp-secreta-001")]) == 0
        texto = (tmp_path / "data" / "profissionais.json").read_text(encoding="utf-8")
        principal = json.loads(texto)
        assert "resp-secreta-001" not in texto
        assert "id_resposta_form" not in texto
        assert set(principal["profissionais"][0].keys()) == set(sync.CAMPOS_PUBLICOS)

        catalogo = montar([linha()])[0]
        catalogo["profissionais"][0]["id_resposta_form"] = "vazamento"
        assert not sync.validar_catalogo(
            {**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})[0]

    def test_instagram_exige_consentimento_valido(self):
        _, contagem, *_ = montar([
            linha(instagram="@maria.silva", consentimento="concordo com tudo"),
        ])
        # Sem consentimento válido nada publica — o campo Instagram incluso.
        assert contagem["publicados"] == 0 and contagem["invalidos"] == 1


# ---------------------------------------------------------------------------
# 5. Privacidade: allowlist estrita
# ---------------------------------------------------------------------------

class TestPrivacidade:
    def test_json_somente_campos_publicos(self):
        catalogo, *_ = montar([linha()])
        registro = catalogo["profissionais"][0]
        assert set(registro.keys()) == set(sync.CAMPOS_PUBLICOS)
        texto = json.dumps(catalogo, ensure_ascii=False)
        for proibido in ["maria@exemplo.com", "contato@exemplo.com",
                         "Rua das Flores", "anotacao interna", CONSENTIMENTO]:
            assert proibido not in texto, proibido

    def test_validador_rejeita_vazamento_e_campos_extras(self):
        catalogo, *_ = montar([linha()])
        catalogo["profissionais"][0]["email_verificado"] = "vazado@exemplo.com"
        assert not sync.validar_catalogo({**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})[0]
        catalogo2, *_ = montar([linha()])
        catalogo2["profissionais"][0]["campoNovo"] = "fora da allowlist"
        assert not sync.validar_catalogo({**catalogo2, "geradoEm": "2026-10-28T12:00:00Z"})[0]


# ---------------------------------------------------------------------------
# 6. Relatório de moderação e comparação (dry-run)
# ---------------------------------------------------------------------------

class TestRelatorioEComparacao:
    def test_dry_run_grava_relatorio_e_nao_publica(self, tmp_path, capsys):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha()]) == 0
        antes = (saida / "profissionais.json").read_text(encoding="utf-8")

        assert executar(
            tmp_path,
            [linha(descricao="Descrição nova."), linha(nome="Suspeito", email_verificado="",
                                                       email_administrativo="")],
            "--dry-run", "--verbose",
        ) == 0
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == antes

        relatorio = json.loads((dados_dir / "relatorio-moderacao.json").read_text(encoding="utf-8"))
        assert relatorio["modo"] == "SIMULACAO"
        assert relatorio["comparacaoComPublicado"] == {"novos": 0, "removidos": 0,
                                                       "alterados": 1, "mantidos": 0}
        assert relatorio["retidosParaRevisao"] and relatorio["retidosParaRevisao"][0]["linha"] == 3
        texto = json.dumps(relatorio, ensure_ascii=False)
        assert "Suspeito" not in texto and "@" not in texto  # sem dados pessoais

    def test_publicar_grava_relatorio_e_mapa(self, tmp_path):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha()]) == 0
        mapa = json.loads((dados_dir / "identidades.json").read_text(encoding="utf-8"))
        assert len(mapa["mapa"]) == 1  # hash -> id da Maria
        assert list(mapa["mapa"].values())[0] == \
            json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))["profissionais"][0]["id"]

    def test_contagens_novos_removidos_alterados(self, tmp_path):
        saida = tmp_path / "data"
        assert executar(tmp_path, [linha(), linha(
            email_verificado="joao@exemplo.com", nome="João Souza",
            whatsapp="31988880002", municipio="Belo Horizonte",
            uf="MG - Minas Gerais")]) == 0
        comparavel = montar([
            linha(descricao="Descrição nova após edição."),
            linha(email_verificado="ana@exemplo.com", nome="Ana Lima",
                  whatsapp="21988880003", municipio="Niterói", uf="RJ - Rio de Janeiro"),
        ], ids_publicados=sync.carregar_ids_publicados(saida))[0]
        assert sync.comparar_com_atual(saida, comparavel) == {
            "novos": 1, "removidos": 1, "alterados": 1, "mantidos": 0,
        }


# ---------------------------------------------------------------------------
# 7. Escrita, atomicidade e falhas
# ---------------------------------------------------------------------------

class TestEscritaEFalhas:
    def test_end_to_end_escreve_catalogo_blocos_e_mapa(self, tmp_path):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha(), linha(
            email_verificado="joao@exemplo.com", nome="João Souza",
            whatsapp="31988880002", municipio="Belo Horizonte",
            uf="MG - Minas Gerais")], "--verbose") == 0
        principal = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))
        assert principal["total"] == 2
        assert (saida / "uf" / "sp.json").exists() and (saida / "uf" / "mg.json").exists()
        assert (dados_dir / "identidades.json").exists()

    def test_segunda_execucao_preserva_id_por_mapa(self, tmp_path):
        saida, dados_dir = tmp_path / "data", tmp_path / "dados"
        assert executar(tmp_path, [linha()]) == 0
        id1 = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))["profissionais"][0]["id"]
        # troca o telefone; mapa de identidades garante o mesmo ID
        assert executar(tmp_path, [linha(whatsapp="11977776666")]) == 0
        id2 = json.loads((saida / "profissionais.json").read_text(encoding="utf-8"))["profissionais"][0]["id"]
        assert id1 == id2

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
        assert sync.main(["--csv", str(ruim), "--saida", str(saida),
                          "--dir-dados", str(tmp_path / "dados")]) == 1
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
        assert sync.main(["--saida", str(saida), "--dir-dados", str(tmp_path / "dados"),
                          "--id-secret", SEGREDO_TESTE]) == 1
        assert (saida / "profissionais.json").read_text(encoding="utf-8") == original

    def test_sem_id_secret_modo_publicar_falha(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PUBLIC_ID_SECRET", raising=False)
        csv_path = tmp_path / "p.csv"
        escrever_csv(csv_path, [linha()])
        assert sync.main(["--csv", str(csv_path), "--saida", str(tmp_path / "d"),
                          "--dir-dados", str(tmp_path / "dd"), "--publicar"]) == 1


# ---------------------------------------------------------------------------
# Normalização e estrutura
# ---------------------------------------------------------------------------

class TestNormalizacao:
    def test_cabecalhos_com_espacos_extras(self):
        mapa = sync.mapa_colunas(CABECALHO)
        for chave in sync.COLUNAS_OBRIGATORIAS:
            assert chave in mapa
        assert mapa["email_verificado"] == 1 and mapa["email_administrativo"] == 13
        assert mapa["id_resposta_form"] == len(CABECALHO) - 1

    def test_cabecalho_em_ordem_diferente_mapeia_por_nome(self):
        # O mapeamento é por cabeçalho normalizado, nunca por posição.
        deslocamento = 9
        embaralhado = CABECALHO[deslocamento:] + CABECALHO[:deslocamento]
        mapa = sync.mapa_colunas(embaralhado)
        assert set(mapa) == {chave for _, chave in COLUNAS_MODELO}
        catalogo, contagem, *_ = sync.montar_catalogo(
            [linha()[deslocamento:] + linha()[:deslocamento]], mapa, SEGREDO_TESTE)
        assert contagem["publicados"] == 1

    def test_uf_formato_do_formulario(self):
        assert sync.normalizar_uf("RJ - Rio de Janeiro") == "RJ"
        assert sync.normalizar_uf("São Paulo") == "SP"

    def test_whatsapp(self):
        assert sync.normalizar_whatsapp("21999999999") == "5521999999999"
        assert sync.normalizar_whatsapp("2122223333") is None

    def test_instagram(self):
        # Aceitos: com ou sem @, com pontos e sublinhados.
        for entrada, esperado in [("@maria.silva", "maria.silva"),
                                  ("profissional_rj", "profissional_rj"),
                                  ("@empresa123", "empresa123"),
                                  ("a" * 30, "a" * 30)]:
            assert sync.normalizar_instagram(entrada) == esperado, entrada
        # Rejeitados: links, @@, espaços, símbolos, pontos mal posicionados, >30.
        for entrada in ["https://instagram.com/meuservico",
                        "www.instagram.com/meuservico", "instagram.com/meuservico",
                        "@@meuservico", "@usuario com espacos", "usuario!",
                        ".usuario", "usuario.", "a..b", "a" * 31, ""]:
            assert sync.normalizar_instagram(entrada) is None, entrada

    def test_consentimento_exato(self):
        assert sync.consentimento_valido(CONSENTIMENTO)
        assert not sync.consentimento_valido("Concordo com tudo")


class TestValidacao:
    def base(self):
        catalogo = montar([linha()])[0]
        catalogo["geradoEm"] = "2026-10-28T12:00:00Z"
        return catalogo

    def test_valido(self):
        valido, erros = sync.validar_catalogo(self.base())
        assert valido, erros

    def test_total_incoerente(self):
        catalogo = self.base()
        catalogo["total"] = 99
        assert not sync.validar_catalogo(catalogo)[0]


class TestSemRegistros:
    def test_so_registros_retidos_gera_valido_e_vazio(self):
        catalogo, contagem, *_ = montar([
            linha(status="PENDENTE"), linha(status="REJEITADO"),
            linha(email_verificado="", email_administrativo=""),
        ])
        assert catalogo["profissionais"] == [] and catalogo["total"] == 0
        valido, erros = sync.validar_catalogo({**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert valido, erros

    def test_aviso_nao_expose_dados_pessoais(self):
        _, _, avisos, _, _, _ = montar([linha(whatsapp="1932320000", nome="Fulana Secreta",
                                               email_verificado="secreto@exemplo.com")])
        texto = " ".join(avisos)
        assert "Fulana" not in texto and "secreto" not in texto


class TestRepositorioSemDadosPessoais:
    """LGPD: dados pessoais jamais versionados — o catálogo real é gerado no
    CI a partir da planilha privada e publicado por upload direto; estado
    operacional vive no Cloudflare KV. O repositório guarda apenas código."""

    def test_nenhum_arquivo_de_dados_versionado(self):
        resultado = subprocess.run(
            ["git", "ls-files", "public/data", "dados"],
            capture_output=True, text=True, cwd=RAIZ, check=True,
        )
        rastreados = [linha for linha in resultado.stdout.splitlines() if linha.strip()]
        assert not rastreados, f"arquivos de dados versionados: {rastreados}"

    def test_modelo_de_planilha_processavel(self):
        linhas = sync.ler_csv(str(RAIZ / "scripts" / "modelo_planilha.csv"))
        mapa = sync.mapa_colunas(linhas[0])
        catalogo, contagem, *_ = sync.montar_catalogo(linhas[1:], mapa, SEGREDO_TESTE)
        assert contagem["publicados"] == 1 and contagem["pendentes"] == 1
        assert contagem["excluidos"] == 1
        assert catalogo["profissionais"][0]["instagram"] == "maria.silva"
        valido, erros = sync.validar_catalogo({**catalogo, "geradoEm": "2026-10-28T12:00:00Z"})
        assert valido, erros
