from __future__ import annotations

import io
import json
from pathlib import Path

import rnds.__main__ as cli
import rnds._consulta as consulta
from rnds.__main__ import main
from rnds.sistemas import CNS, CPF
from rnds.validacao import LIMITE_BYTES


def test_cli_identificadores_json_e_status(capsys) -> None:
    assert main(["cpf", "987.654.321-00"]) == 0
    cpf = json.loads(capsys.readouterr().out)
    assert cpf == {
        "tipo": "cpf",
        "valor": "98765432100",
        "valido": True,
        "sistema": CPF,
        "identifica_pessoa": True,
    }
    assert main(["cns", "712345678901237"]) == 1
    cns = json.loads(capsys.readouterr().out)
    assert cns["sistema"] == CNS
    assert cns["valido"] is False
    assert "identifica_pessoa" in cns
    assert main(["cnes", "1234567"]) == 0
    assert json.loads(capsys.readouterr().out)["valido"] is True


def test_cli_erros_de_uso_e_valor_vazio(capsys) -> None:
    assert main([]) == 2
    assert "uso:" in capsys.readouterr().err
    assert main(["cpf"]) == 2
    assert "obrigatórios" in capsys.readouterr().err
    assert main(["desconhecido"]) == 2
    assert "Comando inválido" in capsys.readouterr().err
    assert main(["cpf", ""]) == 2
    assert "não vazio" in capsys.readouterr().err
    assert main(["cpf", "abc"]) == 2
    assert "não contém dígitos" in capsys.readouterr().err


def test_cli_consulta_catalogo_e_codigos(capsys) -> None:
    assert main(["codigos"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 53
    url = "https://rnds-fhir.saude.gov.br/CodeSystem/BRNacionalidade"
    assert main(["codigos", url]) == 0
    assert json.loads(capsys.readouterr().out)
    assert main(["codigos", url, "B"]) == 0
    assert main(["codigos", url, "inexistente"]) == 1
    assert main(["codigos", "urn:synthetic"]) == 2
    assert "Sistema desconhecido" in capsys.readouterr().err
    url = "https://rnds-fhir.saude.gov.br/ValueSet/BRResultadoQualitativoExame-2.0"
    origem = "https://rnds-fhir.saude.gov.br/CodeSystem/BRTipoResultadoAVIDEZ"
    assert main(["codigos", url, "1", "--origem", origem]) == 0
    assert main(["codigos", url, "1", "--origem", "urn:synthetic"]) == 1
    assert main(["codigos", url, "--origem", origem]) == 2
    assert "Informe o código" in capsys.readouterr().err


def test_cli_mcp_sem_extra_explica_instalacao(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_iniciar_mcp", None)
    assert main(["mcp"]) == 2
    assert 'pip install "rnds[mcp]"' in capsys.readouterr().err


def test_cli_validacao_arquivo_stdin_e_erros(tmp_path: Path, monkeypatch, capsys) -> None:
    fixtures = Path(__file__).parent / "fixtures" / "bundles"
    assert main(["validate", str(fixtures / "valido.json")]) == 0
    assert json.loads(capsys.readouterr().out) == {"achados": []}
    assert main(["validate", str(fixtures / "rnds-id-001.json")]) == 1
    assert json.loads(capsys.readouterr().out)["achados"][0]["code"] == "RNDS-ID-001"
    assert main(["validate", str(fixtures / "rnds-id-004.json")]) == 0
    assert json.loads(capsys.readouterr().out)["achados"][0]["severity"] == "warning"
    dados = (fixtures / "valido.json").read_bytes()
    monkeypatch.setattr(cli.sys, "stdin", io.TextIOWrapper(io.BytesIO(dados)))
    assert main(["validate", "-"]) == 0
    assert json.loads(capsys.readouterr().out) == {"achados": []}
    assert main(["validate"]) == 2
    assert "uso:" in capsys.readouterr().err
    assert main(["validate", str(tmp_path / "ausente.json")]) == 2
    assert "Arquivo não encontrado" in capsys.readouterr().err
    invalido = tmp_path / "invalido.json"
    invalido.write_text("{", encoding="utf-8")
    assert main(["validate", str(invalido)]) == 2
    assert "JSON inválido: linha 1, coluna 2." in capsys.readouterr().err
    profundo = tmp_path / "profundo.json"
    profundo.write_text("[" * 10_000 + "]" * 10_000, encoding="utf-8")
    assert main(["validate", str(profundo)]) == 2
    erro = capsys.readouterr().err
    assert "64 níveis" in erro
    assert "Traceback" not in erro
    grande = tmp_path / "grande.json"
    grande.write_bytes(b"x" * (LIMITE_BYTES + 1))
    assert main(["validate", str(grande)]) == 2
    erro = capsys.readouterr().err
    assert "10 MB" in erro
    assert "Traceback" not in erro
    bundle_compacto = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"subject": {"reference": "Patient/ausente"}}},
        ],
    }
    conteudo_compacto = json.dumps(bundle_compacto, separators=(",", ":"))
    limite = len(conteudo_compacto.encode("utf-8"))
    assert len(json.dumps(bundle_compacto).encode("utf-8")) > limite
    monkeypatch.setattr(consulta, "LIMITE_BYTES", limite)
    monkeypatch.setattr(cli, "LIMITE_BYTES", limite)
    compacto = tmp_path / "compacto.json"
    compacto.write_text(conteudo_compacto, encoding="utf-8")
    assert consulta.validacao_json(bundle_compacto)["achados"][0]["code"] == "RNDS-REF-001"
    assert main(["validate", str(compacto)]) == 1
    assert json.loads(capsys.readouterr().out)["achados"][0]["code"] == "RNDS-REF-001"
