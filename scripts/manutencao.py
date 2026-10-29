"""Gere dados locais e verifique os padrões do repositório."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from _manutencao_quality import verificar as verificar_repositorio
from _rnds_data import (
    FONTE,
    IG_VERSION,
    NOMES,
    NOMES_PATH,
    PACOTE_SHA256,
    PACOTE_URL,
    _json_bytes,
    compilar,
    extrair_pacote,
)

from rnds._mcp_metadata import FERRAMENTAS
from rnds.validacao import CODIGOS

OUT_CODIGOS = ROOT / "src" / "rnds" / "_data" / "codigos.json"
OUT_DOC = ROOT / "docs" / "codigos.md"
OUT_FERRAMENTAS = ROOT / "tests" / "ferramentas.json"
URL_NAMINGSYSTEM = "https://rnds-fhir.saude.gov.br/NamingSystem-{}.json"


def _verificar_ambientes() -> bool:
    """Confira a estrutura e as 27 bases estaduais versionadas."""
    dados = json.loads((ROOT / "src/rnds/_data/ambientes.json").read_text(encoding="utf-8"))
    ufs = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to"
    esperado = {
        "homologacao": {
            "auth": "https://ehr-auth-hmg.saude.gov.br/api",
            "ehr": "https://ehr-services.hmg.saude.gov.br/api",
        },
        "producao": {"auth": "https://ehr-auth.saude.gov.br/api"},
        "ufs": {uf: f"https://{uf}-ehr-services.saude.gov.br/api" for uf in ufs.split()},
    }
    if dados != esperado:
        logging.error("Endereços RNDS inválidos.")
        return False
    return True


def _baixar(url: str) -> bytes:
    """Baixe uma fonte pública com limite de tempo."""
    with urllib.request.urlopen(url, timeout=120) as resposta:
        return resposta.read()


def _escrever_ou_comparar(path: Path, esperado: bytes, *, check: bool) -> bool:
    """Grave bytes determinísticos ou confira o arquivo existente."""
    if check:
        if not path.is_file() or path.read_bytes() != esperado:
            logging.error("Artefato desatualizado: %s", path.relative_to(ROOT))
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(esperado)
    return True


def _artefatos(*, check: bool) -> bool:
    """Compile os índices locais a partir da fonte versionada."""
    fonte = json.loads(FONTE.read_text(encoding="utf-8"))
    dados, documento = compilar(fonte)
    linhas = [
        "",
        "## Achados da validação",
        "",
        "| Código | Severidade | Descrição |",
        "| --- | --- | --- |",
    ]
    linhas.extend(
        f"| `{codigo}` | {severidade} | {descricao} |"
        for codigo, (severidade, descricao) in CODIGOS.items()
    )
    documento = documento.rstrip() + "\n" + "\n".join(linhas) + "\n"
    resultados = (
        (OUT_CODIGOS, _json_bytes(dados)),
        (OUT_DOC, documento.encode("utf-8")),
        (OUT_FERRAMENTAS, _json_bytes(list(FERRAMENTAS))),
    )
    return all(_escrever_ou_comparar(path, conteudo, check=check) for path, conteudo in resultados)


def fonte() -> int:
    """Atualize a fonte versionada com o pacote oficial fixado."""
    pacote = _baixar(PACOTE_URL)
    if hashlib.sha256(pacote).hexdigest() != PACOTE_SHA256:
        raise ValueError("O SHA-256 do pacote baixado não corresponde ao valor fixado.")
    extraido = extrair_pacote(pacote)
    nomeacoes: dict[str, bytes] = {}
    for nome in NOMES:
        conteudo = _baixar(URL_NAMINGSYSTEM.format(nome))
        naming = json.loads(conteudo)
        if naming.get("resourceType") != "NamingSystem":
            raise ValueError(f"Fonte NamingSystem inválida: {nome}")
        nomeacoes[nome] = _json_bytes(naming)
    _escrever_ou_comparar(FONTE, _json_bytes(extraido), check=False)
    for nome, conteudo in nomeacoes.items():
        _escrever_ou_comparar(NOMES_PATH / f"NamingSystem-{nome}.json", conteudo, check=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute uma operação de manutenção."""
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("fonte", help="atualizar as fontes oficiais versionadas")
    artefatos = comandos.add_parser("artefatos", help="gerar os índices offline")
    artefatos.add_argument("--check", action="store_true")
    comandos.add_parser("verificar", help="verificar os padrões e os artefatos")
    args = parser.parse_args(argv)
    try:
        if args.comando == "fonte":
            return fonte()
        if args.comando == "artefatos":
            return 0 if _artefatos(check=args.check) else 1
        return verificar_repositorio(
            ROOT,
            IG_VERSION,
            PACOTE_SHA256,
            lambda: _artefatos(check=True) and _verificar_ambientes(),
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as erro:
        logging.error("%s", erro)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
