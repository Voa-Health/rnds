"""Normalização e validação estrutural de CNES."""

from __future__ import annotations

import re

_DIGITOS = re.compile(r"\D+")


def normalizar(valor: str | None) -> str | None:
    """Retorne os dígitos do valor ou ``None`` quando não houver."""
    digitos = _DIGITOS.sub("", valor or "")
    return digitos or None


def valido(valor: str | None) -> bool:
    """Valide os sete dígitos do CNES, que não dispõe de dígito verificador."""
    digitos = normalizar(valor)
    return digitos is not None and len(digitos) == 7 and digitos != digitos[0] * 7
