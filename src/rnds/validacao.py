"""Validação offline de Bundles FHIR."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from types import MappingProxyType
from typing import Any, Literal

from . import cnes, cns, cpf, sistemas
from .codigos import busca
from .codigos import sistemas as sistemas_codigos

Severidade = Literal["error", "warning"]
LIMITE_BYTES = 10 * 1024 * 1024
LIMITE_PROFUNDIDADE = 64


@dataclass(frozen=True, slots=True)
class Achado:
    """Representa um achado da validação."""

    code: str
    severity: Severidade
    path: str
    message: str


CODIGOS: Mapping[str, tuple[Severidade, str]] = MappingProxyType(
    {
        "RNDS-BUNDLE-001": ("error", "A entrada não é um Bundle FHIR."),
        "RNDS-BUNDLE-002": ("error", "O fullUrl aparece em mais de uma entrada."),
        "RNDS-REF-001": ("error", "A referência não foi resolvida no Bundle."),
        "RNDS-ID-001": ("error", "O CPF é inválido para o sistema informado."),
        "RNDS-ID-002": ("error", "O CNS é inválido para o sistema informado."),
        "RNDS-ID-003": ("error", "O CNES é inválido para o sistema informado."),
        "RNDS-ID-004": ("warning", "O sistema local pode ser convertido para o oficial."),
        "RNDS-CODE-001": ("error", "O código não existe no CodeSystem empacotado."),
        "RNDS-CODE-002": ("warning", "O display difere do conceito empacotado."),
    }
)

_RELATIVA = re.compile(
    r"^[A-Z][A-Za-z]+/[A-Za-z0-9\-.]{1,64}"
    r"(?:/_history/[A-Za-z0-9\-.]{1,64})?$"
)
_IDENTIFICADORES = {
    sistemas.CPF: (cpf.valido, "RNDS-ID-001"),
    sistemas.LOCAL_CPF: (cpf.valido, "RNDS-ID-001"),
    sistemas.CNS: (cns.valido, "RNDS-ID-002"),
    sistemas.LOCAL_CNS: (cns.valido, "RNDS-ID-002"),
    sistemas.CNES: (cnes.valido, "RNDS-ID-003"),
    sistemas.LOCAL_CNES: (cnes.valido, "RNDS-ID-003"),
}


def _excede_profundidade(valor: object) -> bool:
    """Informe se uma estrutura JSON excede a profundidade permitida."""
    if not isinstance(valor, (dict, list)):
        return False
    pendentes: list[tuple[object, int]] = [(valor, 1)]
    while pendentes:
        atual, profundidade = pendentes.pop()
        if profundidade > LIMITE_PROFUNDIDADE:
            return True
        filhos: Iterable[object]
        if isinstance(atual, dict):
            filhos = atual.values()
        elif isinstance(atual, list):
            filhos = atual
        else:
            continue
        pendentes.extend(
            (filho, profundidade + 1) for filho in filhos if isinstance(filho, (dict, list))
        )
    return False


@cache
def _codesystems() -> frozenset[str]:
    """Armazene os endereços dos CodeSystems empacotados."""
    return frozenset(item.url for item in sistemas_codigos() if item.tipo == "CodeSystem")


def _entradas(bundle: Mapping[str, Any]) -> list[Any]:
    """Retorne as entradas do Bundle quando estiverem em uma lista."""
    entradas = bundle.get("entry")
    return entradas if isinstance(entradas, list) else []


def _referencias(bundle: Mapping[str, Any]) -> tuple[set[str], set[str], set[int]]:
    """Indexe fullUrls e identidades de recursos para resolver referências."""
    urls: set[str] = set()
    contagens: dict[str, int] = {}
    repetidos: set[int] = set()
    recursos: set[str] = set()
    for indice, entrada in enumerate(_entradas(bundle)):
        if not isinstance(entrada, dict):
            continue
        url = entrada.get("fullUrl")
        if isinstance(url, str):
            urls.add(url)
            contagens[url] = contagens.get(url, 0) + 1
            if contagens[url] > 1:
                repetidos.add(indice)
        recurso = entrada.get("resource")
        if isinstance(recurso, dict):
            tipo = recurso.get("resourceType")
            identificador = recurso.get("id")
            if isinstance(tipo, str) and isinstance(identificador, str):
                recursos.add(f"{tipo}/{identificador}")
    return urls, recursos, repetidos


def _resolvida(
    referencia: str,
    urls: set[str],
    recursos: set[str],
) -> bool | None:
    """Resolva uma referência suportada ou ignore formatos externos."""
    if referencia.startswith("#") or referencia.startswith(("http://", "https://")):
        return None
    if referencia.startswith(("urn:uuid:", "urn:oid:")):
        return referencia in urls
    if _RELATIVA.fullmatch(referencia) is None:
        return None
    tipo_e_id = "/".join(referencia.split("/")[:2])
    return tipo_e_id in recursos or any(url.endswith(f"/{tipo_e_id}") for url in urls)


def _achado(codigo: str, caminho: str, mensagem: str | None = None) -> Achado:
    """Monte um achado a partir do catálogo fechado."""
    severidade, descricao = CODIGOS[codigo]
    return Achado(codigo, severidade, caminho, mensagem or descricao)


def _validar_identificador(
    valor: dict[str, Any],
    caminho: str,
    achados: list[Achado],
) -> None:
    """Valide identificadores encontrados sob a chave identifier."""
    sistema = valor.get("system")
    identificador = valor.get("value")
    if not isinstance(sistema, str) or not isinstance(identificador, str):
        return
    regra = _IDENTIFICADORES.get(sistema)
    if regra is not None and not regra[0](identificador):
        achados.append(_achado(regra[1], f"{caminho}.value"))
    if sistema.startswith("urn:voa:br:"):
        oficial = sistemas.para_oficial({"system": sistema})["system"]
        if oficial == sistema:
            mensagem = "Não há sistema oficial conhecido para este sistema."
        else:
            mensagem = f"Use o sistema oficial {oficial}."
        achados.append(_achado("RNDS-ID-004", f"{caminho}.system", mensagem))


def _validar_coding(valor: dict[str, Any], caminho: str, achados: list[Achado]) -> None:
    """Confira códigos e displays de sistemas empacotados."""
    sistema = valor.get("system")
    codigo = valor.get("code")
    if not isinstance(sistema, str) or not isinstance(codigo, str):
        return
    if sistema not in _codesystems():
        return
    conceitos = busca(sistema, codigo)
    if not conceitos:
        achados.append(_achado("RNDS-CODE-001", f"{caminho}.code"))
        return
    display = valor.get("display")
    esperado = conceitos[0].display
    if isinstance(display, str) and esperado is not None and display.strip() != esperado.strip():
        achados.append(
            _achado(
                "RNDS-CODE-002",
                f"{caminho}.display",
                f"Display esperado: {esperado}.",
            )
        )


def _visitar(
    bundle: Mapping[str, Any],
    urls: set[str],
    recursos: set[str],
    repetidos: set[int],
) -> list[Achado]:
    """Percorra o documento em pré-ordem e colete os achados."""
    achados: list[Achado] = []
    pilha: list[tuple[object, str, str | None, bool, bool, int | None]] = [
        (bundle, "Bundle", None, False, False, None)
    ]
    while pilha:
        atual, caminho, chave, identificador, coding, indice_entrada = pilha.pop()
        if isinstance(atual, dict):
            if indice_entrada is not None and indice_entrada in repetidos:
                achados.append(_achado("RNDS-BUNDLE-002", f"{caminho}.fullUrl"))
            if identificador:
                _validar_identificador(atual, caminho, achados)
            if coding:
                _validar_coding(atual, caminho, achados)
            filhos = list(atual.items())
            for nome, filho in reversed(filhos):
                caminho_filho = f"{caminho}.{nome}"
                if isinstance(filho, list):
                    pilha.append((filho, caminho_filho, nome, False, False, None))
                else:
                    pilha.append(
                        (
                            filho,
                            caminho_filho,
                            nome,
                            nome == "identifier" and isinstance(filho, dict),
                            False,
                            None,
                        )
                    )
        elif isinstance(atual, list):
            for indice in range(len(atual) - 1, -1, -1):
                filho = atual[indice]
                caminho_filho = f"{caminho}[{indice}]"
                pilha.append(
                    (
                        filho,
                        caminho_filho,
                        chave,
                        chave == "identifier" and isinstance(filho, dict),
                        chave == "coding" and isinstance(filho, dict),
                        indice if caminho == "Bundle.entry" else None,
                    )
                )
        elif chave == "reference" and isinstance(atual, str):
            resolvida = _resolvida(atual, urls, recursos)
            if resolvida is False:
                achados.append(_achado("RNDS-REF-001", caminho))
    return achados


def validar(bundle: object) -> list[Achado]:
    """Valide um Bundle com as regras offline incluídas no pacote."""
    if (
        isinstance(bundle, dict)
        and bundle.get("resourceType") == "Bundle"
        and _excede_profundidade(bundle)
    ):
        raise ValueError("O Bundle excede 64 níveis de aninhamento.")
    if not isinstance(bundle, Mapping) or bundle.get("resourceType") != "Bundle":
        return [_achado("RNDS-BUNDLE-001", "Bundle")]
    urls, recursos, repetidos = _referencias(bundle)
    return _visitar(bundle, urls, recursos, repetidos)
