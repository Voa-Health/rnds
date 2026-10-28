"""Extração e compilação determinística das fontes da RNDS."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

IG_VERSION = "1.0.0"
PACOTE_URL = "https://rnds-fhir.saude.gov.br/package.tgz"
PACOTE_SHA256 = "2888bec577dd55c748c2b5aee70050a65b5e4e57c7464b7be23819410ab61bd8"
DATA_CAPTURA = "2026-10-28"
NOMES = ("cpf", "cns", "cnes")
RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / "scripts" / "fontes" / f"rnds-{IG_VERSION}.json"
NOMES_PATH = RAIZ / "scripts" / "fontes"


def _json_bytes(dados: Any) -> bytes:
    """Serialize JSON com ordenação estável e quebra de linha final."""
    return (json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _propriedade_tipo(conceito: dict[str, Any]) -> str | None:
    """Encontre o valor da propriedade ``type`` de um conceito."""
    for propriedade in conceito.get("property", []):
        if propriedade.get("code") == "type":
            for chave in ("valueCode", "valueString", "valueInteger", "valueBoolean"):
                if chave in propriedade:
                    return str(propriedade[chave])
    return None


def _achatar_conceitos(conceitos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Achate conceitos hierárquicos sem perder a propriedade de tipo."""
    resultado: list[dict[str, Any]] = []
    pendentes = list(conceitos)
    while pendentes:
        atual = pendentes.pop(0)
        item: dict[str, Any] = {"code": atual["code"], "display": atual.get("display")}
        tipo = _propriedade_tipo(atual)
        if tipo is not None:
            item["type"] = tipo
        resultado.append(item)
        pendentes[0:0] = atual.get("concept", [])
    return sorted(resultado, key=lambda item: item["code"])


def _composicao_fonte(compose: dict[str, Any]) -> dict[str, Any]:
    """Reduza a composição a referências e critérios de expansão."""
    resultado: dict[str, Any] = {}
    for direcao in ("include", "exclude"):
        componentes = []
        for componente in compose.get(direcao, []):
            reduzido: dict[str, Any] = {}
            for chave in ("system", "version", "valueSet"):
                if chave in componente:
                    valor = componente[chave]
                    reduzido[chave] = sorted(valor) if chave == "valueSet" else valor
            if "concept" in componente:
                reduzido["concept"] = sorted(
                    [
                        {
                            campo: conceito[campo]
                            for campo in ("code", "display")
                            if campo in conceito
                        }
                        for conceito in componente["concept"]
                    ],
                    key=lambda conceito: conceito["code"],
                )
            if "filter" in componente:
                reduzido["filter"] = sorted(
                    [
                        {campo: filtro[campo] for campo in ("property", "op", "value")}
                        for filtro in componente["filter"]
                    ],
                    key=lambda filtro: (filtro["property"], filtro["op"], filtro["value"]),
                )
            componentes.append(reduzido)
        resultado[direcao] = sorted(
            componentes,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return resultado


def extrair_pacote(conteudo: bytes) -> dict[str, Any]:
    """Extraia os metadados, CodeSystems e ValueSets da publicação."""
    digest = hashlib.sha256(conteudo).hexdigest()
    if digest != PACOTE_SHA256:
        raise ValueError(f"SHA-256 do pacote não confere: {digest}")
    with tarfile.open(fileobj=io.BytesIO(conteudo), mode="r:gz") as arquivo:
        manifesto_membro = arquivo.extractfile("package/package.json")
        if manifesto_membro is None:
            raise ValueError("Manifesto do pacote ausente.")
        manifesto = json.load(manifesto_membro)
        code_systems: list[dict[str, Any]] = []
        value_sets: list[dict[str, Any]] = []
        for membro in arquivo.getmembers():
            if not membro.name.startswith(("package/CodeSystem-", "package/ValueSet-")):
                continue
            recurso_membro = arquivo.extractfile(membro)
            if recurso_membro is None:
                raise ValueError(f"Recurso sem conteúdo: {membro.name}")
            recurso = json.load(recurso_membro)
            if recurso["resourceType"] == "CodeSystem":
                code_systems.append(
                    {
                        "url": recurso["url"],
                        "version": recurso.get("version"),
                        "name": recurso["name"],
                        "title": recurso.get("title", recurso["name"]),
                        "concepts": _achatar_conceitos(recurso.get("concept", [])),
                    }
                )
            else:
                value_sets.append(
                    {
                        "url": recurso["url"],
                        "version": recurso.get("version"),
                        "name": recurso["name"],
                        "title": recurso.get("title", recurso["name"]),
                        "compose": _composicao_fonte(recurso.get("compose", {})),
                    }
                )
    return {
        "metadata": {
            "ig": "rnds",
            "version": IG_VERSION,
            "fhir": "4.0.1",
            "canonical": manifesto["canonical"],
            "source_url": PACOTE_URL,
            "sha256": digest,
            "capture_date": DATA_CAPTURA,
            "declared_license": manifesto["license"],
        },
        "codesystems": sorted(code_systems, key=lambda item: item["url"]),
        "valuesets": sorted(value_sets, key=lambda item: item["url"]),
    }


def _lookup_code_systems(fonte: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Indexe os CodeSystems pelo endereço canônico."""
    return {item["url"]: item for item in fonte["codesystems"]}


def _lookup_value_sets(fonte: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Indexe os ValueSets pelo endereço canônico."""
    return {item["url"]: item for item in fonte["valuesets"]}


def _conceitos_codigo_sistema(code_system: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Mapeie os conceitos de um CodeSystem por sistema e código."""
    url = code_system["url"]
    return {
        (url, conceito["code"]): {
            "sistema": url,
            "codigo": conceito["code"],
            "display": conceito.get("display"),
            **({"type": conceito["type"]} if "type" in conceito else {}),
        }
        for conceito in code_system["concepts"]
    }


def _componentes(
    componente: dict[str, Any],
    code_systems: dict[str, dict[str, Any]],
    value_sets: dict[str, dict[str, Any]],
    trilha: tuple[str, ...],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Resolva um componente de inclusão ou exclusão."""
    resultado: dict[tuple[str, str], dict[str, Any]] = {}
    if "valueSet" in componente:
        for url in componente["valueSet"]:
            resultado.update(
                _expandir_valueset(url.split("|", maxsplit=1)[0], code_systems, value_sets, trilha)
            )
    if "system" not in componente:
        if "valueSet" not in componente:
            raise ValueError(f"Componente de ValueSet sem sistema ou referência: {componente}")
        return resultado
    url = componente["system"]
    if url not in code_systems:
        if "concept" not in componente:
            raise ValueError(f"Não é possível expandir offline o sistema: {url}")
        for conceito in componente["concept"]:
            code = conceito["code"]
            resultado[(url, code)] = {
                "sistema": url,
                "codigo": code,
                "display": conceito.get("display"),
            }
        return resultado
    do_sistema = _conceitos_codigo_sistema(code_systems[url])
    if "concept" in componente:
        for conceito in componente["concept"]:
            chave = (url, conceito["code"])
            original = do_sistema.get(chave, {"sistema": url, "codigo": conceito["code"]})
            resultado[chave] = {
                **original,
                "display": conceito.get("display", original.get("display")),
            }
    else:
        selecionados = do_sistema
        for filtro in componente.get("filter", []):
            if filtro["op"] != "=" or filtro["property"] != "type":
                raise ValueError(f"Filtro não suportado para expansão offline: {filtro}")
            selecionados = {
                chave: conceito
                for chave, conceito in selecionados.items()
                if conceito.get("type") == filtro["value"]
            }
        resultado.update(selecionados)
    return resultado


def _expandir_valueset(
    url: str,
    code_systems: dict[str, dict[str, Any]],
    value_sets: dict[str, dict[str, Any]],
    trilha: tuple[str, ...] = (),
) -> dict[tuple[str, str], dict[str, Any]]:
    """Expanda recursivamente um ValueSet sem depender de rede."""
    if url in trilha:
        raise ValueError(f"Referência circular de ValueSet: {url}")
    if url not in value_sets:
        raise ValueError(f"Não é possível expandir offline o ValueSet: {url}")
    valueset = value_sets[url]
    proxima_trilha = (*trilha, url)
    compose = valueset["compose"]
    incluidos: dict[tuple[str, str], dict[str, Any]] = {}
    excluidos: set[tuple[str, str]] = set()
    for componente in compose.get("include", []):
        incluidos.update(_componentes(componente, code_systems, value_sets, proxima_trilha))
    for componente in compose.get("exclude", []):
        excluidos.update(_componentes(componente, code_systems, value_sets, proxima_trilha))
    return {chave: conceito for chave, conceito in incluidos.items() if chave not in excluidos}


def compilar(fonte: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Gere o índice de códigos e sua página de referência."""
    code_systems = _lookup_code_systems(fonte)
    value_sets = _lookup_value_sets(fonte)
    conceitos: dict[str, list[dict[str, Any]]] = {}
    sistemas: list[dict[str, Any]] = []
    for item in fonte["codesystems"]:
        conceitos[item["url"]] = sorted(
            _conceitos_codigo_sistema(item).values(),
            key=lambda conceito: (conceito["sistema"], conceito["codigo"]),
        )
        sistemas.append(
            {
                "url": item["url"],
                "tipo": "CodeSystem",
                "nome": item["name"],
                "titulo": item["title"],
                "versao": item.get("version"),
                "total": len(conceitos[item["url"]]),
            }
        )
    for item in fonte["valuesets"]:
        expandidos = _expandir_valueset(item["url"], code_systems, value_sets)
        conceitos[item["url"]] = sorted(
            expandidos.values(),
            key=lambda conceito: (conceito["sistema"], conceito["codigo"]),
        )
        sistemas.append(
            {
                "url": item["url"],
                "tipo": "ValueSet",
                "nome": item["name"],
                "titulo": item["title"],
                "versao": item.get("version"),
                "total": len(conceitos[item["url"]]),
            }
        )
    sistemas.sort(key=lambda item: item["url"])
    conteudo = {
        "ig_version": fonte["metadata"]["version"],
        "source_sha256": fonte["metadata"]["sha256"],
        "sistemas": sistemas,
        "conceitos": {url: conceitos[url] for url in sorted(conceitos)},
    }
    tabela = [
        "# Sistemas de códigos RNDS",
        "",
        "| Tipo | Nome | Versão | Conceitos | URL |",
        "| --- | --- | --- | ---: | --- |",
    ]
    tabela.extend(
        f"| {item['tipo']} | `{item['nome']}` | {item['versao'] or '—'} | "
        f"{item['total']} | {item['url']} |"
        for item in sistemas
    )
    return conteudo, "\n".join(tabela) + "\n"
