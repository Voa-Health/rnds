from __future__ import annotations

import json
from pathlib import Path

import pytest

from rnds.codigos import (
    Conceito,
    Sistema,
    _indice_conceitos,
    busca,
    conceitos,
    sistemas,
    valido,
)

_FONTE = json.loads(
    (Path(__file__).parents[1] / "scripts/fontes/rnds-1.0.0.json").read_text(encoding="utf-8")
)
_PARIDADE = json.loads(
    Path(__file__).parent.joinpath("fixtures", "rnds_package.json").read_text(encoding="utf-8")
)
_DIVERGENCIAS = {
    ("tipo-identificador", "BRACONRERP"): (
        "Número de inscrição no Conselho Regional de Relações Públicas (CONRERP)",
        "Número de inscrição no Conselho Regional de Reçações Públicas (CONRERP)",
    ),
    ("tipo-identificador", "BRAOAB"): (
        "Número de inscrição na Ordem dos Advogados do Brasil (OAB)",
        "Número de inscrição na Ordem dos Advogados do BRAasil (OAB)",
    ),
    ("nome-exame-loinc", "94306-8"): (
        "SARS Coronavirus 2 Painel de RNA - Amostra Inespecifica por Amplificacao de "
        "acido nucleico com deteccao por sonda",
        "SARS Coronavírus 2 Painel de RNA - Amostra Inespecífica por Amplificação de "
        "ácido nucleico com detecção por sonda",
    ),
    ("nome-exame-loinc", "94500-6"): (
        "SARS Coronavirus 2, presenca de RNA em amostra respiratoria por amplificacao do "
        "acido nucleico com deteccao por sonda",
        "SARS Coronavírus 2, [presença de] RNA em amostra respiratória por amplificação "
        "do ácido nucleico com detecção por sonda",
    ),
    ("nome-exame-loinc", "94762-2"): (
        "SARS Coronavirus 2 Presenca de anticorpos em Soro ou Plasma por Imunoensaio",
        "SARS Coronavírus 2 [Presença de] anticorpos em Soro ou Plasma por Imunoensaio",
    ),
}


def test_catalogo_tem_dataclasses_imutaveis_e_ordenacao() -> None:
    itens = sistemas()
    assert all(isinstance(item, Sistema) for item in itens)
    assert [item.url for item in itens] == sorted(item.url for item in itens)
    assert len(itens) == 53
    with pytest.raises(AttributeError):
        itens[0].url = "urn:synthetic"
    conceitos_ig = conceitos("https://rnds-fhir.saude.gov.br/CodeSystem/BRNacionalidade")
    assert all(isinstance(item, Conceito) for item in conceitos_ig)


def test_consulta_valueset_e_falha_fechada() -> None:
    url = "https://rnds-fhir.saude.gov.br/ValueSet/BRUnidadeFederativa-1.0"
    estados = conceitos(url)
    assert estados
    assert valido(url, estados[0].codigo)
    assert not valido(url, "urn:missing")
    assert _indice_conceitos(url) is _indice_conceitos(url)
    with pytest.raises(ValueError, match="Sistema desconhecido"):
        conceitos("urn:synthetic")


def test_busca_preserva_conceitos_de_origens_distintas() -> None:
    url = "https://rnds-fhir.saude.gov.br/ValueSet/BRResultadoQualitativoExame-2.0"
    origem_a = "https://rnds-fhir.saude.gov.br/CodeSystem/BRResultadoQualitativoExame"
    origem_b = "https://rnds-fhir.saude.gov.br/CodeSystem/BRTipoResultadoAVIDEZ"
    encontrados = busca(url, "1")

    assert len(encontrados) >= 2
    assert len({item.sistema for item in encontrados}) >= 2
    pares = {(item.sistema, item.display) for item in encontrados}
    assert (origem_a, "Detectável") in pares
    assert (origem_b, "Baixa Avidez") in pares
    assert busca(url, "1", origem_a) == (
        next(item for item in encontrados if item.sistema == origem_a),
    )
    assert valido(url, "1", origem_a)
    assert not valido(url, "1", "urn:synthetic")
    assert busca(url, "inexistente") == ()
    with pytest.raises(ValueError, match="Sistema desconhecido"):
        busca("urn:synthetic", "1")


def test_expansao_aplica_filtros_e_exclusoes() -> None:
    base = "https://rnds-fhir.saude.gov.br/CodeSystem/BRDivisaoGeograficaBrasil"
    estados = conceitos("https://rnds-fhir.saude.gov.br/ValueSet/BRUnidadeFederativa-1.0")
    municipios = conceitos("https://rnds-fhir.saude.gov.br/ValueSet/BRMunicipio-1.0")
    tipos = conceitos("https://rnds-fhir.saude.gov.br/ValueSet/BRTipoDocumentoIndividuo-1.0")
    loinc = conceitos("https://rnds-fhir.saude.gov.br/ValueSet/BRNomeExame-2.0")

    assert all(item.sistema == base for item in (*estados, *municipios))
    assert len(estados) == 27
    assert len(municipios) > len(estados)
    assert "AUTH" not in {item.codigo for item in tipos}
    assert "94764-8" not in {item.codigo for item in loinc}


def test_paridade_com_pacote_reduzido() -> None:
    por_url = {item["url"]: item for item in _FONTE["codesystems"]}
    divergencias = {}
    totais = {"estabelecimento": 39, "nacionalidade": 3, "tipo-identificador": 28}
    for nome, total in totais.items():
        fixture = _PARIDADE["codesystems"][nome]
        pacote = por_url[fixture["canonical"]]
        esperado = {item["code"]: item["display"] for item in fixture["concepts"]}
        assert len(esperado) == total
        obtido = {item.codigo: item.display for item in conceitos(fixture["canonical"])}
        assert obtido.keys() == esperado.keys()
        divergencias.update(
            {
                (nome, codigo): (esperado[codigo], obtido[codigo])
                for codigo in esperado
                if esperado[codigo] != obtido[codigo]
            }
        )
        assert pacote["url"] == fixture["canonical"]

    fixture_loinc = _PARIDADE["codesystems"]["nome-exame-loinc"]
    loinc = conceitos(fixture_loinc["canonical"])
    assert len(fixture_loinc["concepts"]) == 3
    assert len(loinc) == 160
    codigos = {item.codigo: item.display for item in loinc}
    assert set(item["code"] for item in fixture_loinc["concepts"]) <= codigos.keys()
    divergencias.update(
        {
            ("nome-exame-loinc", item["code"]): (
                item["display"],
                codigos[item["code"]],
            )
            for item in fixture_loinc["concepts"]
            if item["display"] != codigos[item["code"]]
        }
    )
    assert divergencias == _DIVERGENCIAS
