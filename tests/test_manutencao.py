import json
from pathlib import Path

from scripts._manutencao_quality import _check_release_versions


def _criar_repositorio_teste(root: Path, pin: str) -> None:
    pacote = root / "src" / "rnds"
    pacote.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "rnds"\nversion = "0.2.0"\n',
        encoding="utf-8",
    )
    (pacote / "__init__.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    (root / "server.json").write_text(
        json.dumps(
            {
                "version": "0.2.0",
                "packages": [
                    {
                        "identifier": "rnds",
                        "version": "0.2.0",
                        "runtimeArguments": [
                            {"name": "--with", "value": pin},
                            {"name": "--with", "value": "outro-pacote==9.9.9"},
                        ],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_versoes_inconsistentes_no_registro_sao_rejeitadas(tmp_path: Path) -> None:
    pacote = tmp_path / "src" / "rnds"
    pacote.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "rnds"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (pacote / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    (tmp_path / "server.json").write_text(
        json.dumps(
            {
                "version": "0.1.0",
                "packages": [{"identifier": "rnds", "version": "0.1.1"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert not _check_release_versions(tmp_path)


def test_pin_desatualizado_e_rejeitado_com_versoes_alinhadas(tmp_path: Path) -> None:
    _criar_repositorio_teste(tmp_path, "rnds[mcp]==0.1.0")

    assert not _check_release_versions(tmp_path)


def test_pin_alinhado_e_outro_pacote_sao_aceitos(tmp_path: Path) -> None:
    _criar_repositorio_teste(tmp_path, "rnds[mcp]==0.2.0")

    assert _check_release_versions(tmp_path)
