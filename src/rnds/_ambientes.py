"""Endereços públicos dos serviços RNDS, disponíveis offline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Literal


@dataclass(frozen=True)
class Endereco:
    """Bases de autenticação e consulta, incluindo o caminho da API."""

    auth: str
    ehr: str


def ambientes() -> dict[str, dict[str, str]]:
    """Leia os endereços versionados sem conexão de rede."""
    dados: dict[str, dict[str, str]] = json.loads(
        files("rnds").joinpath("_data/ambientes.json").read_text(encoding="utf-8")
    )
    return dados


def endereco(ambiente: Literal["homologacao", "producao"], uf: str | None = None) -> Endereco:
    """Resolva as bases; produção exige uma UF brasileira."""
    dados = ambientes()
    if ambiente == "homologacao":
        return Endereco(**dados[ambiente])
    if ambiente != "producao":
        raise ValueError("Ambiente deve ser homologacao ou producao.")
    sigla = uf.lower() if isinstance(uf, str) else ""
    if sigla not in dados["ufs"]:
        raise ValueError("Produção exige uma das 27 UFs brasileiras.")
    return Endereco(dados[ambiente]["auth"], dados["ufs"][sigla])
