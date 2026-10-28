"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from typing import Any, NoReturn

from . import __version__, cnes, cns, cpf
from ._consulta import (
    conceitos_json,
    identificador_payload,
    sistemas_json,
)
from .codigos import valido

_iniciar_mcp: Callable[[], None] | None
try:
    from ._mcp import main as _iniciar_mcp
except ImportError:
    _iniciar_mcp = None

_TIPOS = {"cpf": cpf, "cns": cns, "cnes": cnes}
_CODIGO_USO = 2


class _ArgumentParser(argparse.ArgumentParser):
    def format_usage(self) -> str:
        """Exiba a linha de uso em português."""
        return super().format_usage().replace("usage:", "uso:", 1)

    def error(self, message: str) -> NoReturn:
        """Mostre erros de argumentos em português."""
        if message.startswith("the following arguments are required:"):
            message = f"Informe os argumentos obrigatórios: {message.split(':', maxsplit=1)[1]}."
        elif message.startswith("unrecognized arguments:"):
            message = f"Argumentos não reconhecidos: {message.split(':', maxsplit=1)[1]}."
        elif "invalid choice:" in message:
            message = "Comando inválido."
        self.print_usage(sys.stderr)
        self.exit(_CODIGO_USO, f"{self.prog}: erro: {message}\n")


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    """Interprete os argumentos da linha de comando."""
    parser = _ArgumentParser(prog="rnds")
    parser.add_argument("--version", action="version", version=__version__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    for nome in _TIPOS:
        comando = comandos.add_parser(nome, help=f"verificar identificador {nome.upper()}")
        comando.add_argument("valor")
    codigos = comandos.add_parser("codigos", help="consultar os códigos disponíveis")
    codigos.add_argument("sistema", nargs="?")
    codigos.add_argument("codigo", nargs="?")
    codigos.add_argument("--origem")
    comandos.add_parser("mcp", help="iniciar o servidor MCP local em stdio")
    return parser.parse_args(argv)


def _emitir(dados: Any) -> None:
    """Escreva JSON em formato estável."""
    sys.stdout.write(json.dumps(dados, ensure_ascii=False, sort_keys=True) + "\n")


def _codigos(sistema: str | None, codigo: str | None, origem: str | None) -> int:
    """Liste sistemas, conceitos ou valide um código."""
    if origem is not None and sistema is None:
        raise ValueError("Informe o sistema para consultar uma origem.")
    if origem is not None and codigo is None:
        raise ValueError("Informe o código para consultar uma origem.")
    if sistema is None:
        if codigo is not None:
            raise ValueError("Informe o sistema para consultar um código.")
        _emitir(sistemas_json())
        return 0
    if codigo is None:
        _emitir(conceitos_json(sistema))
        return 0
    return 0 if valido(sistema, codigo, origem) else 1


def mcp_main() -> int:
    """Inicie o servidor MCP ou informe como instalar o extra."""
    if _iniciar_mcp is None:
        sys.stderr.write('Instale o extra MCP: pip install "rnds[mcp]"\n')
        return _CODIGO_USO
    _iniciar_mcp()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute a interface de linha de comando."""
    try:
        args = _argumentos(argv)
    except SystemExit as erro:
        return erro.code if isinstance(erro.code, int) else 0
    try:
        if args.comando in _TIPOS:
            payload = identificador_payload(args.comando, args.valor)
            _emitir(payload)
            return 0 if payload["valido"] else 1
        if args.comando == "codigos":
            return _codigos(args.sistema, args.codigo, args.origem)
        return mcp_main()
    except ValueError as erro:
        sys.stderr.write(f"{erro}\n")
        return _CODIGO_USO


if __name__ == "__main__":
    raise SystemExit(main())
