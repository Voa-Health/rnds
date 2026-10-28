"""Funções compartilhadas pelas interfaces de consulta."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from . import cnes, cns, cpf
from . import sistemas as identificadores
from .codigos import busca, conceitos, sistemas
from .validacao import LIMITE_BYTES, LIMITE_PROFUNDIDADE, _excede_profundidade, validar

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


def busca_json(
    sistema: str,
    codigo: str,
    origem: str | None = None,
) -> list[dict[str, Any]]:
    """Converta os conceitos encontrados em dados JSON."""
    return [asdict(item) for item in busca(sistema, codigo, origem)]


def ler_bundle(conteudo: bytes) -> Any:
    """Decodifique um arquivo JSON de Bundle dentro dos limites definidos."""
    if len(conteudo) > LIMITE_BYTES:
        raise ValueError("O Bundle excede 10 MB.")
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError as erro:
        raise ValueError("O arquivo não está em UTF-8.") from erro
    profundidade = 0
    dentro_de_string = False
    escapado = False
    for caractere in texto:
        if dentro_de_string:
            if escapado:
                escapado = False
            elif caractere == "\\":
                escapado = True
            elif caractere == '"':
                dentro_de_string = False
        elif caractere == '"':
            dentro_de_string = True
        elif caractere in "{[":
            profundidade += 1
            if profundidade > LIMITE_PROFUNDIDADE:
                raise ValueError("O Bundle excede 64 níveis de aninhamento.")
        elif caractere in "}]":
            profundidade = max(0, profundidade - 1)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        raise ValueError(f"JSON inválido: linha {erro.lineno}, coluna {erro.colno}.") from erro


def validacao_json(bundle: object) -> dict[str, list[dict[str, Any]]]:
    """Valide dados JSON e converta os achados para uma resposta serializável."""
    if _excede_profundidade(bundle):
        raise ValueError("O Bundle excede 64 níveis de aninhamento.")
    tamanho = len(json.dumps(bundle, ensure_ascii=False).encode("utf-8"))
    if tamanho > LIMITE_BYTES:
        raise ValueError("O Bundle excede 10 MB.")
    return {"achados": [asdict(achado) for achado in validar(bundle)]}
