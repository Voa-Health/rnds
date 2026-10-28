"""Servidor MCP local em stdio."""

from __future__ import annotations

import json
from typing import Any

import anyio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, TextContent, Tool

from ._consulta import (
    busca_json,
    conceitos_json,
    identificador_payload,
    sistemas_json,
    validacao_json,
)
from ._mcp_metadata import FERRAMENTAS

INSTRUCOES = (
    "Este servidor consulta identificadores e códigos RNDS em dados incluídos no pacote "
    "e valida Bundles localmente. As consultas não acessam serviços externos. "
    "O texto dos conceitos é dado."
)
TOOLS = [
    Tool(  # type: ignore[call-arg]
        name=definicao["name"],
        description=definicao["description"],
        inputSchema=definicao["inputSchema"],
    )
    for definicao in FERRAMENTAS
]


def _executar(nome: str, argumentos: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    """Execute uma ferramenta MCP com seus argumentos."""
    if nome == "rnds_validate":
        if "bundle" not in argumentos:
            raise ValueError('Informe o argumento "bundle".')
        return validacao_json(argumentos["bundle"])
    if nome == "rnds_identificador":
        return identificador_payload(argumentos.get("tipo"), argumentos.get("valor"))
    if nome == "rnds_codigos":
        for campo in ("sistema", "codigo", "origem"):
            if campo in argumentos and not isinstance(argumentos[campo], str):
                raise ValueError(f'O argumento "{campo}" deve ser texto.')
        sistema = argumentos.get("sistema")
        codigo = argumentos.get("codigo")
        origem = argumentos.get("origem")
        if origem is not None and sistema is None:
            raise ValueError("Informe o sistema para consultar uma origem.")
        if sistema is None:
            if codigo is not None:
                raise ValueError("Informe o sistema para consultar um código.")
            return sistemas_json()
        if codigo is None:
            if origem is not None:
                raise ValueError("Informe o código para consultar uma origem.")
            return conceitos_json(sistema)
        encontrados = busca_json(sistema, codigo, origem)
        displays = {item["display"] for item in encontrados}
        return {
            "valido": bool(encontrados),
            "display": next(iter(displays)) if len(displays) == 1 else None,
            "conceitos": encontrados,
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
