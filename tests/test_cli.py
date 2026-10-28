from __future__ import annotations

import json

import rnds.__main__ as cli
from rnds.__main__ import main
from rnds.sistemas import CNS, CPF


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


def test_cli_mcp_sem_extra_explica_instalacao(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_iniciar_mcp", None)
    assert main(["mcp"]) == 2
    assert 'pip install "rnds[mcp]"' in capsys.readouterr().err
