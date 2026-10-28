from __future__ import annotations

import json
from pathlib import Path

from rnds import cnes, cns, cpf

_CASOS = json.loads(
    Path(__file__).parent.joinpath("fixtures", "identificadores.json").read_text(encoding="utf-8")
)


def test_normalizar_aceita_mascaras_e_ausencia_de_digitos() -> None:
    assert cpf.normalizar("987.654.321-00") == "98765432100"
    assert cns.normalizar("712 3456-7890 1236") == "712345678901236"
    assert cnes.normalizar("12.345-67") == "1234567"
    assert cpf.normalizar(None) is None
    assert cns.normalizar("abc") is None
    assert cnes.normalizar("") is None


def test_validacao_cpf() -> None:
    for valor in _CASOS["cpf"]["validos"]:
        assert cpf.valido(valor)
    for valor in _CASOS["cpf"]["invalidos"]:
        assert not cpf.valido(valor)


def test_validacao_cns_definitivo_provisorio_e_invalidos() -> None:
    for valor in _CASOS["cns"]["definitivos"] + _CASOS["cns"]["provisorios"]:
        assert cns.valido(valor)
    for valor in _CASOS["cns"]["invalidos"]:
        assert not cns.valido(valor)


def test_cns_definitivo_com_separador_001() -> None:
    valido, invalido = "100000000060018", "100000000060008"
    assert valido[:11] == invalido[:11]
    assert valido[11:14] == "001"
    assert invalido[11:14] == "000"
    assert cns.valido(valido)
    assert not cns.valido(invalido)


def test_validacao_cnes() -> None:
    for valor in _CASOS["cnes"]["validos"]:
        assert cnes.valido(valor)
    for valor in _CASOS["cnes"]["invalidos"]:
        assert not cnes.valido(valor)


def test_identifica_pessoa_exige_comprimento_e_variedade() -> None:
    for valor, esperado in _CASOS["cpf"]["plausibilidade"]:
        assert cpf.identifica_pessoa(valor) is esperado
    for valor, esperado in _CASOS["cns"]["plausibilidade"]:
        assert cns.identifica_pessoa(valor) is esperado


def test_quinto_digito_cns_nao_altera_resto_modular() -> None:
    primeiro, segundo = _CASOS["cns"]["quinto_digito"]
    assert primeiro[:4] == segundo[:4]
    assert primeiro[5:] == segundo[5:]
    assert primeiro[4] != segundo[4]
    assert cns.valido(primeiro)
    assert cns.valido(segundo)
