"""Consulta offline de CodeSystems e ValueSets da RNDS."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any, Literal, cast


@dataclass(frozen=True, slots=True)
class Sistema:
    """Metadados de um CodeSystem ou ValueSet."""

    url: str
    tipo: Literal["CodeSystem", "ValueSet"]
    nome: str
    titulo: str
    versao: str | None
    total: int


@dataclass(frozen=True, slots=True)
class Conceito:
    """Código e display de um CodeSystem de origem."""

    sistema: str
    codigo: str
    display: str | None


@cache
def _dados() -> dict[str, Any]:
    """Carregue o artefato incluído no pacote."""
    conteudo = (
        resources.files("rnds")
        .joinpath("_data")
        .joinpath("codigos.json")
        .read_text(encoding="utf-8")
    )
    return cast(dict[str, Any], json.loads(conteudo))


def sistemas() -> tuple[Sistema, ...]:
    """Liste os sistemas disponíveis, ordenados por URL."""
    return tuple(
        Sistema(
            url=item["url"],
            tipo=item["tipo"],
            nome=item["nome"],
            titulo=item["titulo"],
            versao=item.get("versao"),
            total=item["total"],
        )
        for item in _dados()["sistemas"]
    )


def conceitos(sistema: str) -> tuple[Conceito, ...]:
    """Liste os conceitos de um CodeSystem ou ValueSet conhecido."""
    if sistema not in _dados()["conceitos"]:
        raise ValueError(f"Sistema desconhecido: {sistema}")
    return tuple(
        Conceito(
            sistema=item["sistema"],
            codigo=item["codigo"],
            display=item.get("display"),
        )
        for item in _dados()["conceitos"][sistema]
    )


def valido(sistema: str, codigo: str, origem: str | None = None) -> bool:
    """Confira se o código pertence ao sistema e, se informada, à origem."""
    return bool(busca(sistema, codigo, origem))


def busca(sistema: str, codigo: str, origem: str | None = None) -> tuple[Conceito, ...]:
    """Liste os conceitos do código, opcionalmente filtrados pela origem."""
    encontrados = _indice_conceitos(sistema).get(codigo, ())
    if origem is None:
        return encontrados
    return tuple(item for item in encontrados if item.sistema == origem)


@cache
def _indice_conceitos(sistema: str) -> dict[str, tuple[Conceito, ...]]:
    agrupados: dict[str, list[Conceito]] = {}
    for item in conceitos(sistema):
        agrupados.setdefault(item.codigo, []).append(item)
    return {codigo: tuple(itens) for codigo, itens in agrupados.items()}
