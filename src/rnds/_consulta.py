"""Funções compartilhadas pelas interfaces de consulta."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from . import cnes, cns, cpf
from . import sistemas as identificadores
from .codigos import conceitos, sistemas

_MODULOS = {"cpf": cpf, "cns": cns, "cnes": cnes}
_SISTEMAS = {
    "cpf": identificadores.CPF,
    "cns": identificadores.CNS,
    "cnes": identificadores.CNES,
}


def identificador_payload(tipo: object, valor: object) -> dict[str, Any]:
    """Valide os argumentos e monte o resultado do identificador."""
    if not isinstance(tipo, str):
        raise ValueError("Informe o tipo de identificador como texto.")
    if tipo not in _MODULOS:
        raise ValueError(f"Tipo de identificador desconhecido: {tipo}")
    if not isinstance(valor, str):
        raise ValueError("Informe o valor do identificador como texto.")
    if not valor.strip():
        raise ValueError("Informe um valor não vazio.")
    modulo = _MODULOS[tipo]
    normalizado = modulo.normalizar(valor)
    if normalizado is None:
        raise ValueError("O valor não contém dígitos.")
    resultado: dict[str, Any] = {
        "tipo": tipo,
        "valor": normalizado,
        "valido": modulo.valido(valor),
        "sistema": _SISTEMAS[tipo],
    }
    if tipo in {"cpf", "cns"}:
        resultado["identifica_pessoa"] = modulo.identifica_pessoa(valor)
    return resultado


def sistemas_json() -> list[dict[str, Any]]:
    """Converta os sistemas disponíveis em dados JSON."""
    return [asdict(item) for item in sistemas()]


def conceitos_json(sistema: str) -> list[dict[str, Any]]:
    """Converta os conceitos de um sistema em dados JSON."""
    return [asdict(item) for item in conceitos(sistema)]
