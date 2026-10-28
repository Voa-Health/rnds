"""Normalização e validação estrutural de CNS."""

from __future__ import annotations

import re

_DIGITOS = re.compile(r"\D+")
_PREFIXOS_DEFINITIVOS = ("1", "2")
_PREFIXOS_PROVISORIOS = ("7", "8", "9")


def normalizar(valor: str | None) -> str | None:
    """Retorne os dígitos do valor ou ``None`` quando não houver."""
    digitos = _DIGITOS.sub("", valor or "")
    return digitos or None


def valido(valor: str | None) -> bool:
    """Valide o CNS; no provisório o quinto dígito tem peso 11 e não altera o resto."""
    digitos = normalizar(valor)
    if digitos is None or len(digitos) != 15 or digitos == digitos[0] * 15:
        return False
    if digitos[0] in _PREFIXOS_PROVISORIOS:
        return _soma_ponderada(digitos) % 11 == 0
    if digitos[0] in _PREFIXOS_DEFINITIVOS:
        return _definitivo_valido(digitos)
    return False


def identifica_pessoa(valor: str | None) -> bool:
    """Verifique se o CNS tem comprimento e variedade de dígitos plausíveis."""
    digitos = normalizar(valor)
    return digitos is not None and len(digitos) == 15 and len(set(digitos)) > 2


def _soma_ponderada(digitos: str) -> int:
    """Some os dígitos com pesos decrescentes de 15 a 1."""
    return sum(int(digito) * (15 - indice) for indice, digito in enumerate(digitos))


def _definitivo_valido(digitos: str) -> bool:
    """Reconstrua o CNS definitivo a partir dos onze dígitos iniciais."""
    pis = digitos[:11]
    total = sum(int(digito) * (15 - indice) for indice, digito in enumerate(pis))
    verificacao = 11 - (total % 11)
    if verificacao == 11:
        verificacao = 0
    if verificacao == 10:
        total += 2
        verificacao = 11 - (total % 11)
        return digitos == f"{pis}001{verificacao}"
    return digitos == f"{pis}000{verificacao}"
