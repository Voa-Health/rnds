from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from rnds._mcp import TOOLS, _executar, _resultado_tool, criar_servidor
from rnds._mcp_metadata import FERRAMENTAS
from rnds.codigos import conceitos

_MANIFESTO = json.loads(Path(__file__).with_name("ferramentas.json").read_text(encoding="utf-8"))


def test_manifesto_corresponde_ao_servidor() -> None:
    assert list(FERRAMENTAS) == _MANIFESTO
    assert [tool.name for tool in TOOLS] == [item["name"] for item in _MANIFESTO]
    for tool, esperado in zip(TOOLS, _MANIFESTO, strict=True):
        assert tool.model_dump(by_alias=True)["inputSchema"] == esperado["inputSchema"]


def test_servidor_e_respostas_das_ferramentas() -> None:
    assert criar_servidor() is not None
    identificador = _executar("rnds_identificador", {"tipo": "cns", "valor": "712345678901236"})
    assert identificador["valido"] is True
    assert _executar("rnds_codigos", {})[0]["tipo"] == "CodeSystem"
    url = "https://rnds-fhir.saude.gov.br/CodeSystem/BRNacionalidade"
    esperado = next(item for item in conceitos(url) if item.codigo == "B")
    resultado = _executar("rnds_codigos", {"sistema": url, "codigo": "B"})
    assert resultado["valido"] is True
    assert resultado["display"] == esperado.display


def test_erro_mcp_para_valores_vazios_e_sistemas_desconhecidos() -> None:
    vazio = _resultado_tool("rnds_identificador", {"tipo": "cpf", "valor": ""})
    desconhecido = _resultado_tool("rnds_codigos", {"sistema": "urn:synthetic", "codigo": "X"})
    assert vazio.model_dump(by_alias=True)["isError"]
    assert "não vazio" in vazio.content[0].text
    assert desconhecido.model_dump(by_alias=True)["isError"]
    assert "Sistema desconhecido" in desconhecido.content[0].text


def test_erro_mcp_para_argumentos_ausentes_ou_nao_textuais() -> None:
    casos = (
        ("rnds_identificador", {}, "tipo"),
        ("rnds_identificador", {"tipo": "cpf"}, "valor"),
        ("rnds_identificador", {"tipo": 1, "valor": "98765432100"}, "tipo"),
        ("rnds_identificador", {"tipo": "cpf", "valor": 1}, "valor"),
        ("rnds_codigos", {"sistema": 1}, "sistema"),
        ("rnds_codigos", {"sistema": "urn:synthetic", "codigo": 1}, "codigo"),
    )
    for nome, argumentos, campo in casos:
        resposta = _resultado_tool(nome, argumentos)
        assert resposta.model_dump(by_alias=True)["isError"]
        assert campo in resposta.content[0].text
        assert "KeyError" not in resposta.content[0].text


def test_servidor_stdio_com_cliente_mcp() -> None:
    raiz = Path(__file__).parents[1]
    parametros = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rnds", "mcp"],
        env=dict(os.environ, PYTHONPATH=str(raiz / "src")),
    )

    async def consultar() -> None:
        async with (
            stdio_client(parametros) as (leitura, escrita),
            ClientSession(leitura, escrita) as cliente,
        ):
            await cliente.initialize()
            ferramentas = await cliente.list_tools()
            resultado = await cliente.call_tool(
                "rnds_identificador",
                {"tipo": "cns", "valor": "712345678901236"},
            )
            assert {item.name for item in ferramentas.tools} == {
                "rnds_identificador",
                "rnds_codigos",
            }
            assert json.loads(resultado.content[0].text)["valido"] is True

    anyio.run(consultar)
