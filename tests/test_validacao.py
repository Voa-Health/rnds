from __future__ import annotations

import json
from pathlib import Path

import pytest

from rnds._consulta import validacao_json
from rnds.sistemas import CPF
from rnds.validacao import CODIGOS, LIMITE_BYTES, validar

_FIXTURAS = Path(__file__).parent / "fixtures" / "bundles"
_SISTEMA_CODIGO = "https://rnds-fhir.saude.gov.br/CodeSystem/BRTerminologiaSuspeitaDiagnostica"


def _fixture(nome: str) -> dict[str, object]:
    return json.loads((_FIXTURAS / nome).read_text(encoding="utf-8"))


def _bundle_com_niveis(niveis: int) -> dict[str, object]:
    bundle: dict[str, object] = {"resourceType": "Bundle"}
    atual = bundle
    for indice in range(niveis - 1):
        filho: dict[str, object] = {}
        atual[f"nivel{indice}"] = filho
        atual = filho
    return bundle


def test_fixtures_cobrem_catalogo_fechado_e_severidades() -> None:
    assert validar(_fixture("valido.json")) == []
    emitidos: set[str] = set()
    for caminho in sorted(_FIXTURAS.glob("rnds-*.json")):
        achados = validar(_fixture(caminho.name))
        esperados = {f"RNDS-{caminho.stem.removeprefix('rnds-').upper()}"}
        assert {achado.code for achado in achados} == esperados
        assert all(achado.severity == CODIGOS[achado.code][0] for achado in achados)
        emitidos.update(achado.code for achado in achados)
    assert emitidos == set(CODIGOS)
    assert emitidos <= set(CODIGOS)


def test_paths_e_ordem_de_achados_seguem_o_documento() -> None:
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "fullUrl": "urn:uuid:repetida",
                "resource": {
                    "identifier": [{"system": CPF, "value": "123"}],
                    "subject": {"reference": "Patient/ausente"},
                    "code": {"coding": [{"system": _SISTEMA_CODIGO, "code": "ausente"}]},
                },
            },
            {
                "fullUrl": "urn:uuid:repetida",
                "resource": {"resourceType": "Patient"},
            },
        ],
    }
    assert [(item.code, item.path) for item in validar(bundle)] == [
        ("RNDS-ID-001", "Bundle.entry[0].resource.identifier[0].value"),
        ("RNDS-REF-001", "Bundle.entry[0].resource.subject.reference"),
        ("RNDS-CODE-001", "Bundle.entry[0].resource.code.coding[0].code"),
        ("RNDS-BUNDLE-002", "Bundle.entry[1].fullUrl"),
    ]


def test_referencias_ignoradas_e_resolvidas_nao_geram_achados() -> None:
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "fullUrl": "https://exemplo.test/Patient/fora",
                "resource": {
                    "resourceType": "Patient",
                    "id": "local",
                    "extension": [
                        {"valueReference": {"reference": "#fragmento"}},
                        {"valueReference": {"reference": "https://externo.test/Patient/1"}},
                        {"valueReference": {"reference": "Patient/local"}},
                        {"valueReference": {"reference": "Patient/local/_history/1"}},
                        {"valueReference": {"reference": "Patient/fora"}},
                    ],
                },
            }
        ],
    }
    assert validar(bundle) == []


def test_limites_de_profundidade_e_tamanho() -> None:
    profundo: dict[str, object] = {"resourceType": "Bundle"}
    atual = profundo
    for indice in range(10_000):
        filho: dict[str, object] = {}
        atual[f"nivel{indice}"] = filho
        atual = filho
    with pytest.raises(ValueError, match="64 níveis"):
        validar(profundo)
    with pytest.raises(ValueError, match="64 níveis"):
        validacao_json(profundo)
    assert validar(_bundle_com_niveis(64)) == []
    assert validacao_json(_bundle_com_niveis(64)) == {"achados": []}
    with pytest.raises(ValueError, match="64 níveis"):
        validar(_bundle_com_niveis(65))
    with pytest.raises(ValueError, match="64 níveis"):
        validacao_json(_bundle_com_niveis(65))
    assert validacao_json("texto") == {
        "achados": [
            {
                "code": "RNDS-BUNDLE-001",
                "severity": "error",
                "path": "Bundle",
                "message": CODIGOS["RNDS-BUNDLE-001"][1],
            }
        ]
    }
    with pytest.raises(ValueError, match="10 MB"):
        validacao_json({"resourceType": "Bundle", "texto": "x" * (LIMITE_BYTES + 1)})
