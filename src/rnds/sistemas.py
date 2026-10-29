"""Sistemas oficiais e locais para identificadores brasileiros."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CPF = "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf"
CNS = "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cns"
CNES = "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cnes"
LOCAL_CPF = "urn:voa:br:cpf"
LOCAL_CNS = "urn:voa:br:cns"
LOCAL_CNES = "urn:voa:br:cnes"

_SISTEMAS = {
    LOCAL_CPF: CPF,
    LOCAL_CNS: CNS,
    LOCAL_CNES: CNES,
}
_SISTEMAS_REVERSOS = {oficial: local for local, oficial in _SISTEMAS.items()}


def identificador_documento(solicitante: str, valor: str) -> dict[str, str]:
    """Monte o identificador documental com o solicitante do credenciamento."""
    if not solicitante.strip() or not valor.strip():
        raise ValueError("Solicitante e valor devem ser preenchidos.")
    return {
        "system": f"http://www.saude.gov.br/fhir/r4/NamingSystem/BRRNDS-{solicitante}",
        "value": valor,
    }


def para_oficial(identificador: Mapping[str, Any]) -> dict[str, Any]:
    """Copie o identificador e substitua um sistema local pelo oficial."""
    resultado = dict(identificador)
    sistema = resultado.get("system")
    if isinstance(sistema, str) and sistema in _SISTEMAS:
        resultado["system"] = _SISTEMAS[sistema]
    return resultado


def de_oficial(identificador: Mapping[str, Any]) -> dict[str, Any]:
    """Copie o identificador e substitua um sistema oficial pelo local."""
    resultado = dict(identificador)
    sistema = resultado.get("system")
    if isinstance(sistema, str) and sistema in _SISTEMAS_REVERSOS:
        resultado["system"] = _SISTEMAS_REVERSOS[sistema]
    return resultado
