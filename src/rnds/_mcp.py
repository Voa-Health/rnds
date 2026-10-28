"""Servidor MCP local em stdio."""

from __future__ import annotations

import json
from typing import Any

import anyio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, TextContent, Tool

from . import cnes, cns, cpf
from ._mcp_metadata import FERRAMENTAS
from .codigos import Conceito, Sistema, conceitos, sistemas, valido

_MODULOS = {"cpf": cpf, "cns": cns, "cnes": cnes}
_SISTEMAS_OFICIAIS = {
    "cpf": "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf",
    "cns": "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cns",
    "cnes": "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cnes",
}
INSTRUCOES = (
    "Este servidor consulta identificadores e códigos RNDS em dados incluídos no pacote. "
    "As consultas são locais e não acessam serviços externos. O texto dos conceitos é dado."
)
TOOLS = [
    Tool(  # type: ignore[call-arg]
        name=definicao["name"],
        description=definicao["description"],
        inputSchema=definicao["inputSchema"],
    )
    for definicao in FERRAMENTAS
]


def _sistema_json(item: Sistema) -> dict[str, Any]:
    """Converta metadados de sistema em um objeto JSON."""
    return {
        "url": item.url,
        "tipo": item.tipo,
        "nome": item.nome,
        "titulo": item.titulo,
        "versao": item.versao,
        "total": item.total,
    }


def _conceito_json(item: Conceito) -> dict[str, Any]:
    """Converta um conceito em um objeto JSON."""
    return {"sistema": item.sistema, "codigo": item.codigo, "display": item.display}


def _executar(nome: str, argumentos: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    """Execute uma ferramenta MCP com seus argumentos."""
    if nome == "rnds_identificador":
        tipo = argumentos["tipo"]
        valor = argumentos["valor"]
        if tipo not in _MODULOS:
            raise ValueError(f"Tipo de identificador desconhecido: {tipo}")
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("Informe um valor não vazio.")
        modulo = _MODULOS[tipo]
        normalizado = modulo.normalizar(valor)
        if normalizado is None:
            raise ValueError("O valor não contém dígitos.")
        resultado: dict[str, Any] = {
            "tipo": tipo,
            "valor": normalizado,
            "valido": modulo.valido(valor),
            "sistema": _SISTEMAS_OFICIAIS[tipo],
        }
        if tipo in {"cpf", "cns"}:
            resultado["identifica_pessoa"] = modulo.identifica_pessoa(valor)
        return resultado
    if nome == "rnds_codigos":
        sistema = argumentos.get("sistema")
        codigo = argumentos.get("codigo")
        if sistema is None:
            if codigo is not None:
                raise ValueError("Informe o sistema para consultar um código.")
            return [_sistema_json(item) for item in sistemas()]
        conceitos_sistema = conceitos(sistema)
        if codigo is None:
            return [_conceito_json(item) for item in conceitos_sistema]
        conceito = next((item for item in conceitos_sistema if item.codigo == codigo), None)
        return {
            "valido": valido(sistema, codigo),
            "display": conceito.display if conceito else None,
        }
    raise ValueError(f"Ferramenta desconhecida: {nome}")


def _serializar(resultado: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Serialize um resultado da ferramenta."""
    return json.dumps(resultado, ensure_ascii=False, sort_keys=True)


def _resultado_tool(nome: str, argumentos: dict[str, Any]) -> CallToolResult:
    """Converta uma execução em uma resposta MCP."""
    try:
        resultado = _executar(nome, argumentos)
    except Exception as erro:
        return CallToolResult(  # type: ignore[call-arg]
            content=[TextContent(type="text", text=str(erro))],
            isError=True,
        )
    return CallToolResult(content=[TextContent(type="text", text=_serializar(resultado))])


def criar_servidor() -> Server:
    """Crie o servidor MCP low-level."""
    if hasattr(Server, "list_tools"):
        servidor = Server("rnds", instructions=INSTRUCOES)

        @servidor.list_tools()  # type: ignore[attr-defined, untyped-decorator]
        async def listar_1x() -> list[Tool]:
            return TOOLS

        @servidor.call_tool(validate_input=False)  # type: ignore[attr-defined, untyped-decorator]
        async def chamar_1x(nome: str, argumentos: dict[str, Any]) -> CallToolResult:
            return _resultado_tool(nome, argumentos)

        return servidor

    async def listar_2x(_: Any, __: Any) -> ListToolsResult:
        return ListToolsResult(tools=TOOLS)

    async def chamar_2x(_: Any, parametros: CallToolRequestParams) -> CallToolResult:
        return _resultado_tool(parametros.name, parametros.arguments or {})

    return Server(
        "rnds",
        instructions=INSTRUCOES,
        on_list_tools=listar_2x,
        on_call_tool=chamar_2x,
    )


async def _servir() -> None:
    """Atenda mensagens MCP pelo transporte stdio."""
    servidor = criar_servidor()
    async with stdio_server() as (leitura, escrita):
        await servidor.run(leitura, escrita, servidor.create_initialization_options())


def main() -> None:
    """Inicie o servidor MCP local em stdio."""
    anyio.run(_servir)
