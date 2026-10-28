"""Verificações de consistência e conteúdo do repositório."""

from __future__ import annotations

import ast
import io
import json
import logging
import re
import subprocess
import tokenize
from collections.abc import Callable
from pathlib import Path

LIMITES = {
    "docstring_chars": 88,
    "comment_chars": 88,
    "comment_lines": 2,
    "module_lines": 600,
    "test_files": 8,
    "test_functions": 36,
}
_TERMOS = re.compile(
    r"charcot|voa-backend|api\.voa\.health|"
    r"\bPRD\b|\bUS\d+\b|\bD[0-9]{1,2}\b|"
    r"(?<!SSE-)(?<!AWS::)\bS[1-7][bc]?\b(?![.:/])(?!\s+cp\b)|"
    r"(?<!official-)\bPR\b|\bissue\b|pull request|"
    r"\bsess[aã]o(?:\s+S[1-7])?\b|legad|legacy|portad[oa] de|migrad|"
    r"nesta vers[aã]o|uso futuro|por enquanto|\bTODO\b|FIXME|"
    r"(?<!release/)(?<!/)\bv1\b(?!\.\d)|antes/agora|"
    r"termx|(?<!build-)backend|\bR[123]\b|be#\d+|"
    r"histórico|história|infisical|\b\d{12}\b",
    re.IGNORECASE,
)


def _arquivos(root: Path) -> list[Path]:
    """Liste arquivos rastreados e novos sem consultar fontes externas."""
    saida = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return sorted(root / nome for nome in saida if (root / nome).is_file())


def _verificar_texto(root: Path) -> bool:
    """Bloqueie termos internos e conteúdo de processo."""
    correto = True
    for caminho in _arquivos(root):
        relativo = caminho.relative_to(root).as_posix()
        if (
            relativo
            in {
                "LICENSE",
                "uv.lock",
                "scripts/manutencao.py",
                "scripts/_manutencao_quality.py",
            }
            or relativo.startswith(("tests/fixtures/", "scripts/fontes/", "src/rnds/_data/"))
            or relativo == "docs/codigos.md"
        ):
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for linha, texto_linha in enumerate(texto.splitlines(), start=1):
            proibido = _TERMOS.search(texto_linha)
            if proibido:
                print(f"{relativo}:{linha}: termo não permitido: {proibido.group()}")
                correto = False
    return correto


def _verificar_python(root: Path) -> bool:
    """Confira limites de módulos, docstrings e comentários."""
    correto = True
    arquivos = [
        caminho
        for pasta in ("src", "scripts", "tests")
        for caminho in (root / pasta).rglob("*.py")
        if ".venv" not in caminho.parts
    ]
    testes = [caminho for caminho in arquivos if caminho.is_relative_to(root / "tests")]
    funcoes_teste = 0
    if len(testes) > LIMITES["test_files"]:
        print(f"Arquivos de teste excedem {LIMITES['test_files']}.")
        correto = False
    for caminho in arquivos:
        texto = caminho.read_text(encoding="utf-8")
        linhas = texto.splitlines()
        if len(linhas) > LIMITES["module_lines"] and caminho.name not in {"manutencao.py"}:
            print(f"{caminho.relative_to(root)} excede {LIMITES['module_lines']} linhas.")
            correto = False
        try:
            arvore = ast.parse(texto, filename=str(caminho))
        except SyntaxError:
            print(f"{caminho.relative_to(root)} contém sintaxe inválida.")
            correto = False
            continue
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and caminho in testes:
                funcoes_teste += int(no.name.startswith("test_"))
            if not isinstance(
                no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            docstring = ast.get_docstring(no, clean=False)
            if docstring is None:
                continue
            numero_linha = no.body[0].lineno if no.body else 1
            if (
                len(docstring.splitlines()) != 1
                or len(docstring) > LIMITES["docstring_chars"]
                or not docstring.endswith(".")
            ):
                print(f"{caminho.relative_to(root)}:{numero_linha}: docstring fora do padrão.")
                correto = False
        try:
            tokens = tokenize.generate_tokens(io.StringIO(texto).readline)
            comentario_linhas: list[int] = []
            for token in tokens:
                if token.type != tokenize.COMMENT or token.string.startswith(
                    ("#!", "# type:", "# noqa")
                ):
                    continue
                if len(token.string) > LIMITES["comment_chars"]:
                    print(f"{caminho.relative_to(root)}:{token.start[0]}: comentário extenso.")
                    correto = False
                if not linhas[token.start[0] - 1][: token.start[1]].strip():
                    comentario_linhas.append(token.start[0])
            sequencia = 0
            anterior = 0
            for numero in comentario_linhas:
                sequencia = sequencia + 1 if numero == anterior + 1 else 1
                if sequencia > LIMITES["comment_lines"]:
                    print(f"{caminho.relative_to(root)}:{numero}: comentários consecutivos.")
                    correto = False
                anterior = numero
        except (IndentationError, tokenize.TokenError):
            pass
    if funcoes_teste > LIMITES["test_functions"]:
        print(f"Funções de teste excedem {LIMITES['test_functions']}.")
        correto = False
    return correto


def _report_violation(path: Path | str, line: int, message: str) -> None:
    """Registre uma divergência do repositório."""
    logging.error("%s:%d: %s", Path(path).as_posix(), line, message)


def _check_release_versions(root: Path) -> bool:
    """Confira se as versões do pacote e do registro MCP coincidem."""
    project_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    project = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", project_text)
    version_match = (
        re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', project.group(1))
        if project is not None
        else None
    )
    if version_match is None:
        _report_violation("pyproject.toml", 1, "versão de [project] ausente")
        return False
    version = version_match.group(1)
    correto = True

    init_path = root / "src/rnds/__init__.py"
    init_text = init_path.read_text(encoding="utf-8")
    init_match = re.search(
        r"""^__version__\s*=\s*["']([^"']+)["']""",
        init_text,
        flags=re.MULTILINE,
    )
    if init_match is None:
        _report_violation("src/rnds/__init__.py", 1, "__version__ ausente")
        correto = False
    elif init_match.group(1) != version:
        linha = init_text.count("\n", 0, init_match.start()) + 1
        _report_violation(
            "src/rnds/__init__.py",
            linha,
            "__version__ difere de [project].version",
        )
        correto = False

    server_path = root / "server.json"
    server_text = server_path.read_text(encoding="utf-8")
    server = json.loads(server_text)
    if not isinstance(server, dict):
        _report_violation("server.json", 1, "registro MCP inválido")
        return False
    server_lines = server_text.splitlines()
    linha_versao_servidor = next(
        (
            numero
            for numero, linha in enumerate(server_lines, start=1)
            if re.match(r'^ {2}"version"\s*:', linha)
        ),
        1,
    )
    linhas_versoes_pacotes = [
        numero
        for numero, linha in enumerate(server_lines, start=1)
        if re.match(r'^ {6}"version"\s*:', linha)
    ]
    if server.get("version") != version:
        _report_violation(
            "server.json",
            linha_versao_servidor,
            "versão do registro MCP difere de [project].version",
        )
        correto = False
    packages = server.get("packages")
    if not isinstance(packages, list):
        _report_violation("server.json", linha_versao_servidor, "lista de pacotes ausente")
        return False
    for indice, package in enumerate(packages):
        linha = linhas_versoes_pacotes[indice] if indice < len(linhas_versoes_pacotes) else 1
        if not isinstance(package, dict):
            _report_violation("server.json", linha, f"pacote MCP {indice} inválido")
            correto = False
            continue
        if package.get("version") != version:
            identificador = package.get("identifier", indice)
            _report_violation(
                "server.json",
                linha,
                f"versão do pacote MCP {identificador} difere de [project].version",
            )
            correto = False
        runtime_arguments = package.get("runtimeArguments", [])
        if not isinstance(runtime_arguments, list):
            continue
        for argument in runtime_arguments:
            if not isinstance(argument, dict) or argument.get("name") != "--with":
                continue
            value = argument.get("value")
            if (
                not isinstance(value, str)
                or re.match(
                    r"^rnds(\[[^\]]*\])?(==|$)",
                    value,
                )
                is None
            ):
                continue
            if re.fullmatch(r"rnds(\[[^\]]*\])?==" + re.escape(version), value) is not None:
                continue
            valor_json = re.escape(json.dumps(value, ensure_ascii=False))
            linha_valor = next(
                (
                    numero
                    for numero, texto_linha in enumerate(server_lines, start=1)
                    if re.search(r'"value"\s*:\s*' + valor_json, texto_linha)
                ),
                1,
            )
            _report_violation(
                "server.json",
                linha_valor,
                f"versão fixada em --with ({value}) difere de [project].version",
            )
            correto = False
    return correto


def verificar(
    root: Path,
    versao: str,
    sha256: str,
    conferir_artefatos: Callable[[], bool],
) -> int:
    """Confira fontes, padrões de conteúdo e artefatos compilados."""
    fonte = root / "scripts" / "fontes" / f"rnds-{versao}.json"
    dados = json.loads(fonte.read_text(encoding="utf-8"))
    correto = dados["metadata"]["version"] == versao and dados["metadata"]["sha256"] == sha256
    correto = _verificar_texto(root) and _verificar_python(root) and correto
    correto = _check_release_versions(root) and correto
    correto = conferir_artefatos() and correto
    return 0 if correto else 1
