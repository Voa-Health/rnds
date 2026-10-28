import json
from pathlib import Path

from scripts._manutencao_quality import _check_release_versions


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
