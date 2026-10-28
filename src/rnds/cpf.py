"""Normalização e validação estrutural de CPF."""

from __future__ import annotations

import re

_DIGITOS = re.compile(r"\D+")


def normalizar(valor: str | None) -> str | None:
    """Retorne os dígitos do valor ou ``None`` quando não houver."""
    digitos = _DIGITOS.sub("", valor or "")
    return digitos or None


def valido(valor: str | None) -> bool:
    """Valide o comprimento e os dígitos verificadores do CPF."""
    digitos = normalizar(valor)
    if digitos is None or len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    return all(_digito_verificador(digitos, posicao) == digitos[posicao] for posicao in (9, 10))


def identifica_pessoa(valor: str | None) -> bool:
    """Verifique se o CPF tem comprimento e variedade de dígitos plausíveis."""
    digitos = normalizar(valor)
    return digitos is not None and len(digitos) == 11 and len(set(digitos)) > 2


def _digito_verificador(digitos: str, posicao: int) -> str:
    """Calcule o dígito verificador do CPF."""
    total = sum(
        int(digito) * peso
        for digito, peso in zip(digitos[:posicao], range(posicao + 1, 1, -1), strict=True)
    )
    resto = total % 11
    return "0" if resto < 2 else str(11 - resto)
