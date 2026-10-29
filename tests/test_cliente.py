from __future__ import annotations

import json
import logging
import ssl
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from rnds import cnes, cns, cpf, sistemas
from rnds.__main__ import main
from rnds._mcp_metadata import FERRAMENTAS
from rnds.cliente import (
    ClienteEhr,
    ErroDeConexao,
    ErroRnds,
    NaoAutenticado,
    NaoEncontrado,
    RedirecionamentoRecusado,
    RequisicaoRecusada,
    SemPermissao,
    Token,
    ambientes,
    contexto_mtls,
    endereco,
    obter_token,
)

_CNS = next(str(n) for n in range(712345678901230, 712345678901250) if cns.valido(str(n)))
_CPF = next(str(n) for n in range(98765432000, 98765432200) if cpf.valido(str(n)))
_CNES = "1234567"
_VALOR = "autorizacao-sintetica"
_TOKEN = Token(_VALOR, datetime.now(timezone.utc) + timedelta(minutes=30))


def test_enderecos_consultas_e_catalogo(capsys) -> None:
    assert cnes.valido(_CNES)
    assert len(ambientes()["ufs"]) == 27
    assert main(["ambientes"]) == 0
    assert json.loads(capsys.readouterr().out) == ambientes()
    assert list(FERRAMENTAS) == json.loads(Path("tests/ferramentas.json").read_text())
    assert sistemas.identificador_documento("laboratorio-sintetico", "exame-sintetico") == {
        "system": "http://www.saude.gov.br/fhir/r4/NamingSystem/BRRNDS-laboratorio-sintetico",
        "value": "exame-sintetico",
    }
    for vazio in ("", " "):
        with pytest.raises(ValueError):
            sistemas.identificador_documento(vazio, "x")
    for uf in ambientes()["ufs"]:
        assert endereco("producao", uf.upper()).ehr == ambientes()["ufs"][uf]
    for ambiente, uf in [("invalido", None), ("producao", None), ("producao", "xx")]:
        with pytest.raises(ValueError):
            endereco(ambiente, uf)
    assert endereco("homologacao", "xx") == endereco("homologacao")
    vistos = []

    def responder(req):
        vistos.append(req)
        assert req.headers["Authorization"] == _CNS
        assert req.headers["X-Authorization-Server"] == f"Bearer {_VALOR}"
        return httpx.Response(200, json={"resourceType": "Bundle", "entry": []})

    for ambiente, uf in [("homologacao", None), ("producao", "SP")]:
        with ClienteEhr(
            _TOKEN, _CNS, ambiente, uf, transport=httpx.MockTransport(responder)
        ) as cli:
            assert cli.paciente(cpf=_CPF) == {"resourceType": "Bundle", "entry": []}
            assert vistos[-1].url.params["identifier"] == f"{sistemas.CPF}|{_CPF}"
            cli.paciente(cns=_CNS)
            assert vistos[-1].url.params["identifier"] == f"{sistemas.CNS}|{_CNS}"
            cli.profissional(cns=_CNS)
            assert vistos[-1].url.path.endswith("/Practitioner/" + _CNS)
            cli.profissional(cpf=_CPF)
            assert vistos[-1].url.params["identifier"] == f"{sistemas.CPF}|{_CPF}"
            cli.lotacoes(_CNS, _CNES)
            assert dict(vistos[-1].url.params) == {
                "practitioner.identifier": f"{sistemas.CNS}|{_CNS}",
                "organization.identifier": f"{sistemas.CNES}|{_CNES}",
            }
            for valor in (_CNES, "12345678000100"):
                cli.estabelecimento(valor)
                assert vistos[-1].url.path.endswith("/Organization/" + valor)
            cli.capacidades()
            assert vistos[-1].url.params["mode"] == "full"
            assert str(vistos[-1].url).startswith(endereco(ambiente, uf).ehr + "/fhir/r4/")
            antes = len(vistos)
            for metodo in (cli.paciente, cli.profissional):
                for args in ({}, {"cpf": _CPF, "cns": _CNS}, {"cpf": ""}, {"cns": "x"}):
                    with pytest.raises(ValueError):
                        metodo(**args)
            for chamada in (
                lambda: cli.lotacoes("x", _CNES),
                lambda: cli.lotacoes(_CNS, ""),
                lambda: cli.estabelecimento(""),
                lambda: cli.estabelecimento("\uff11" * 14),
            ):
                with pytest.raises(ValueError):
                    chamada()
            assert len(vistos) == antes
    with pytest.raises(ValueError):
        ClienteEhr(_TOKEN, "x", "homologacao")


def test_autorizacao_e_validade() -> None:
    assert _VALOR not in repr(_TOKEN) and _VALOR not in str(_TOKEN)
    assert not _TOKEN.expirado()
    assert _TOKEN.expirado(timedelta(hours=1))
    assert Token("x", datetime.now(timezone.utc)).expirado(timedelta())
    for ambiente in ("homologacao", "producao"):

        def responder(req, ambiente=ambiente):
            assert str(req.url) == ambientes()[ambiente]["auth"] + "/token"
            assert "Authorization" not in req.headers
            return httpx.Response(
                200,
                json={
                    "access_token": _VALOR,
                    "scope": "read",
                    "token_type": "jwt",
                    "expires_in": 1800000,
                },
            )

        inicio = datetime.now(timezone.utc)
        obtido = obter_token(
            ssl.create_default_context(), ambiente, transport=httpx.MockTransport(responder)
        )
        assert obtido.valor == _VALOR
        assert (
            inicio + timedelta(minutes=29)
            < obtido.expira_em
            <= (datetime.now(timezone.utc) + timedelta(minutes=30))
        )
    for tipo in ({}, {"token_type": "Bearer"}):
        obtido = obter_token(
            ssl.create_default_context(),
            "homologacao",
            transport=httpx.MockTransport(
                lambda _, tipo=tipo: httpx.Response(
                    200, json={"access_token": _VALOR, "expires_in": 1800000, **tipo}
                )
            ),
        )
        assert isinstance(obtido, Token) and obtido.valor == _VALOR
    for corpo in (
        {},
        {"access_token": "", "expires_in": 1},
        {"access_token": 123, "expires_in": 1},
        *(
            {"access_token": _VALOR, "expires_in": valor}
            for valor in (True, 0, -1, "1800000", 1.5, 10**100)
        ),
    ):
        with pytest.raises(ErroRnds) as erro:
            obter_token(
                ssl.create_default_context(),
                "homologacao",
                transport=httpx.MockTransport(
                    lambda _, corpo=corpo: httpx.Response(200, json=corpo)
                ),
            )
        assert type(erro.value) is ErroRnds
    with pytest.raises(ValueError):
        obter_token(ssl.create_default_context(), "x")


def test_erros_redirecionamento_e_logs(caplog) -> None:
    caplog.set_level(logging.INFO, logger="rnds.cliente")
    casos = [
        (401, "882", "expired", NaoAutenticado),
        (403, "881", "security", SemPermissao),
        (422, "906", "security", SemPermissao),
        (422, "866", "invalid", RequisicaoRecusada),
        (422, "924", "invalid", RequisicaoRecusada),
        (404, None, "not-found", NaoEncontrado),
        (400, None, "invalid", RequisicaoRecusada),
        (500, None, "exception", ErroRnds),
        (503, None, "security", ErroRnds),
        (302, None, "invalid", RedirecionamentoRecusado),
    ]
    for status, codigo, tipo, classe in casos:
        achados = [
            {
                "code": tipo,
                "diagnostics": (f"(EHR-ERR{codigo}) " if codigo else "")
                + f"{_VALOR} {_CNS} {_CPF}",
            }
        ]
        chamadas = []

        def responder(req, chamadas=chamadas, status=status, achados=achados):
            chamadas.append(req)
            return httpx.Response(
                status,
                json={"resourceType": "OperationOutcome", "issue": achados},
                headers={"Location": "https://outro.example/"},
            )

        with (
            ClienteEhr(
                _TOKEN, _CNS, "homologacao", transport=httpx.MockTransport(responder)
            ) as cli,
            pytest.raises(classe) as erro,
        ):
            cli.paciente(cpf=_CPF)
        assert len(chamadas) == 1
        assert type(erro.value) is classe
        assert erro.value.status == status
        assert erro.value.codigo == (f"EHR-ERR{codigo}" if codigo else None)
        assert erro.value.issues == achados
        for valor in (_VALOR, _CNS, _CPF):
            assert valor not in str(erro.value) and valor not in repr(erro.value)
            assert valor not in caplog.text
    for status, corpo, classe in (
        (401, b"", NaoAutenticado),
        (422, b"html", RequisicaoRecusada),
        (200, b"", ErroRnds),
        (200, b"html", ErroRnds),
        (200, b"[]", ErroRnds),
        (503, b"", ErroRnds),
    ):
        with (
            ClienteEhr(
                _TOKEN,
                _CNS,
                "homologacao",
                transport=httpx.MockTransport(
                    lambda _, status=status, corpo=corpo: httpx.Response(status, content=corpo)
                ),
            ) as cli,
            pytest.raises(classe) as erro,
        ):
            cli.capacidades()
        assert type(erro.value) is classe
        assert erro.value.status == status
        with pytest.raises(classe) as erro:
            obter_token(
                ssl.create_default_context(),
                "homologacao",
                transport=httpx.MockTransport(
                    lambda _, status=status, corpo=corpo: httpx.Response(status, content=corpo)
                ),
            )
        assert type(erro.value) is classe
        assert erro.value.status == status
    for excecao, classe in (
        (httpx.ConnectTimeout, ErroDeConexao),
        (httpx.ConnectError, ErroDeConexao),
        (httpx.ReadTimeout, ErroDeConexao),
        (httpx.WriteError, ErroDeConexao),
        (httpx.ReadError, ErroDeConexao),
    ):
        chamadas = []

        def falhar(req, chamadas=chamadas, excecao=excecao):
            chamadas.append(req)
            raise excecao(f"{_VALOR} {_CNS} {_CPF}")

        with (
            ClienteEhr(_TOKEN, _CNS, "homologacao", transport=httpx.MockTransport(falhar)) as cli,
            pytest.raises(classe) as erro,
        ):
            cli.capacidades()
        assert len(chamadas) == 1
        assert all(valor not in str(erro.value) for valor in (_VALOR, _CNS, _CPF))
        with pytest.raises(ErroDeConexao):
            obter_token(
                ssl.create_default_context(),
                "homologacao",
                transport=httpx.MockTransport(falhar),
            )
        assert len(chamadas) == 2


def test_mtls_temporario_removido(monkeypatch) -> None:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sintetico.example")])
    agora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(1)
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=1))
        .sign(chave, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(
        b"sintetico",
        chave,
        certificado,
        None,
        serialization.BestAvailableEncryption(b"senha-sintetica"),
    )
    original = ssl.SSLContext.load_cert_chain
    caminhos = []
    falhar = False

    def carregar(self, caminho):
        arquivo = Path(caminho)
        caminhos.append(arquivo)
        assert stat.S_IMODE(arquivo.stat().st_mode) == 0o600
        if falhar:
            raise ssl.SSLError("falha sintetica")
        original(self, caminho)

    monkeypatch.setattr(ssl.SSLContext, "load_cert_chain", carregar)
    assert isinstance(contexto_mtls(pfx, b"senha-sintetica"), ssl.SSLContext)
    assert caminhos and not any(p.exists() for p in caminhos)
    falhar = True
    with pytest.raises(ValueError):
        contexto_mtls(pfx, b"senha-sintetica")
    assert not any(p.exists() for p in caminhos)
    for conteudo, senha in ((b"", b""), (pfx, b"errada")):
        with pytest.raises(ValueError):
            contexto_mtls(conteudo, senha)
