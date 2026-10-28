from __future__ import annotations

import json
from pathlib import Path

from rnds.sistemas import (
    CNES,
    CNS,
    CPF,
    LOCAL_CNES,
    LOCAL_CNS,
    LOCAL_CPF,
    de_oficial,
    para_oficial,
)

_FONTES = Path(__file__).parents[1] / "scripts" / "fontes"
_OFICIAIS = {
    LOCAL_CPF: CPF,
    LOCAL_CNS: CNS,
    LOCAL_CNES: CNES,
}


def test_sistemas_oficiais_correspondem_aos_namingsystems() -> None:
    for tipo, sistema in (("cpf", CPF), ("cns", CNS), ("cnes", CNES)):
        naming = json.loads((_FONTES / f"NamingSystem-{tipo}.json").read_text(encoding="utf-8"))
        identificadores = [item for item in naming["uniqueId"] if item["type"] == "uri"]
        assert [item["value"] for item in identificadores] == [sistema]


def test_para_oficial_copia_e_preserva_os_campos() -> None:
    identificador = {
        "system": LOCAL_CPF,
        "value": "987.654.321-00",
        "extension": [{"url": "urn:synthetic", "valueString": "Exemplo"}],
    }
    resultado = para_oficial(identificador)

    assert resultado == {**identificador, "system": CPF}
    assert resultado is not identificador
    assert identificador["system"] == LOCAL_CPF
    assert para_oficial(resultado) == resultado
    for local, oficial in _OFICIAIS.items():
        convertido = para_oficial({"system": local, "value": "sem normalizar"})
        assert convertido["system"] == oficial
        assert de_oficial(convertido)["system"] == local


def test_de_oficial_e_sistemas_nao_mapeados() -> None:
    identificador = {"system": CPF, "value": "sem normalizar"}
    resultado = de_oficial(identificador)

    assert resultado == {**identificador, "system": LOCAL_CPF}
    assert resultado is not identificador
    assert de_oficial(resultado) == resultado
    desconhecido = {"system": "urn:synthetic", "value": "A"}
    assert para_oficial(desconhecido) == desconhecido
    assert de_oficial(desconhecido) == desconhecido
    assert set(_OFICIAIS) == {LOCAL_CPF, LOCAL_CNS, LOCAL_CNES}
