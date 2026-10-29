"""Autenticação mTLS e operações RNDS explícitas, sem repetição automática."""

from __future__ import annotations

import json
import logging
import os
import re
import ssl
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Literal
from urllib.parse import urlsplit

try:
    import httpx
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        pkcs12,
    )
except ImportError:
    raise ImportError('Instale o extra: pip install "rnds[cliente]"') from None

from . import cnes, cns, cpf, sistemas, validacao
from ._ambientes import Endereco, ambientes, endereco
from .validacao import Achado

__all__ = [
    "BundleInvalido",
    "ClienteEhr",
    "Endereco",
    "Envio",
    "ErroDeConexao",
    "ErroRnds",
    "NaoAutenticado",
    "NaoEncontrado",
    "RedirecionamentoRecusado",
    "RequisicaoRecusada",
    "ResultadoIncerto",
    "SemPermissao",
    "Token",
    "ambientes",
    "contexto_mtls",
    "endereco",
    "obter_token",
]

_LOG = logging.getLogger(__name__)
Ambiente = Literal["homologacao", "producao"]


class ErroRnds(Exception):
    """Falha com mensagem segura e achados originais disponíveis explicitamente."""

    def __init__(
        self, mensagem: str, *, status: int | None = None, issues: list[Any] | None = None
    ) -> None:
        super().__init__(mensagem)
        self.status = status
        self.issues = issues if issues is not None else []
        self.codigo: str | None = None
        for achado in self.issues:
            if isinstance(achado, dict):
                diagnostico = achado.get("diagnostics")
                encontrado = (
                    re.match(r"\(?(EHR-ERR[0-9]{3})\)?", diagnostico or "")
                    if (isinstance(diagnostico, str))
                    else None
                )
                if encontrado:
                    self.codigo = encontrado[1]
                    break


class ErroDeConexao(ErroRnds):
    """Falha de transporte; repetir é seguro."""


class ResultadoIncerto(ErroRnds):
    """Envio pode ter sido processado; não repita sem reconciliação."""


class BundleInvalido(ErroRnds):
    """Bundle recusado localmente, sem envio."""

    def __init__(self, achados: tuple[Achado, ...]) -> None:
        super().__init__("Bundle inválido.")
        self.achados = achados


@dataclass(frozen=True)
class Envio:
    """Resultado do envio aceito pelo serviço."""

    id_rnds: str
    location: str
    avisos: tuple[Achado, ...]


class RedirecionamentoRecusado(ErroRnds):
    """Redirecionamento recusado sem reenvio dos cabeçalhos."""


class NaoAutenticado(ErroRnds):
    """Autenticação recusada."""


class SemPermissao(ErroRnds):
    """Operação sem permissão."""


class NaoEncontrado(ErroRnds):
    """Recurso não encontrado."""


class RequisicaoRecusada(ErroRnds):
    """Requisição recusada pelo serviço."""


@dataclass(frozen=True)
class Token:
    """Autorização em memória com vencimento em UTC."""

    valor: str = field(repr=False)
    expira_em: datetime

    def expirado(self, margem: timedelta = timedelta(seconds=30)) -> bool:
        """Verifique o vencimento considerando uma margem de segurança."""
        return datetime.now(timezone.utc) + margem >= self.expira_em


def contexto_mtls(pfx: bytes, senha: bytes) -> ssl.SSLContext:
    """Carregue PKCS#12 e remova imediatamente o PEM temporário privado."""
    try:
        chave, certificado, cadeia = pkcs12.load_key_and_certificates(pfx, senha)
        if chave is None or certificado is None:
            raise ValueError
        pem = chave.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        pem += certificado.public_bytes(Encoding.PEM)
        pem += b"".join(item.public_bytes(Encoding.PEM) for item in cadeia or [])
        contexto = ssl.create_default_context()
        descritor, nome = tempfile.mkstemp()
        try:
            with os.fdopen(descritor, "wb") as arquivo:
                os.fchmod(arquivo.fileno(), 0o600)
                arquivo.write(pem)
            contexto.load_cert_chain(nome)
        finally:
            os.unlink(nome)
        return contexto
    except (ValueError, OSError, ssl.SSLError):
        raise ValueError("Não foi possível carregar o certificado mTLS.") from None


def _requisicao(
    http: httpx.Client,
    url: str,
    op: str,
    *,
    idempotente: bool = True,
    metodo: str = "GET",
    **kwargs: Any,
) -> httpx.Response:
    inicio = perf_counter()
    status = None
    try:
        try:
            resposta = http.request(metodo, url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise ErroDeConexao("Falha de conexão; repetir é seguro.") from None
        except httpx.TransportError:
            erro_transporte = ErroDeConexao if idempotente else ResultadoIncerto
            raise erro_transporte("Falha de transporte na operação RNDS.") from None
        status = resposta.status_code
        try:
            dados = resposta.json()
        except ValueError:
            dados = None
        achados = dados.get("issue", []) if isinstance(dados, dict) else []
        achados = achados if isinstance(achados, list) else []
        erro: type[ErroRnds] | None = None
        if 300 <= status < 400:
            erro = RedirecionamentoRecusado
        elif 500 <= status < 600:
            erro = ErroRnds if idempotente else ResultadoIncerto
        elif status == 401:
            erro = NaoAutenticado
        elif status == 403 or any(
            isinstance(item, dict) and item.get("code") == "security" for item in achados
        ):
            erro = SemPermissao
        elif status == 404:
            erro = NaoEncontrado
        elif 400 <= status < 500:
            erro = RequisicaoRecusada
        elif not 200 <= status < 300:
            erro = ErroRnds
        if erro:
            raise erro("Operação RNDS não concluída.", status=status, issues=achados)
        return resposta
    finally:
        _LOG.info("op=%s status=%s duracao_ms=%.3f", op, status, (perf_counter() - inicio) * 1000)


def _get(http: httpx.Client, url: str, op: str, **kwargs: Any) -> dict[str, Any]:
    resposta = _requisicao(http, url, op, **kwargs)
    try:
        dados = resposta.json()
    except ValueError:
        dados = None
    if not isinstance(dados, dict):
        raise ErroRnds("Resposta RNDS inválida.", status=resposta.status_code)
    return dict(dados)


def obter_token(
    contexto: ssl.SSLContext,
    ambiente: Ambiente,
    *,
    timeout: float = 30.0,
    transport: httpx.BaseTransport | None = None,
) -> Token:
    """Obtenha autorização mTLS; expires_in é expresso em milissegundos."""
    if ambiente not in ("homologacao", "producao"):
        raise ValueError("Ambiente deve ser homologacao ou producao.")
    auth = ambientes()[ambiente]["auth"]
    inicio = datetime.now(timezone.utc)
    with httpx.Client(
        verify=contexto, timeout=timeout, transport=transport, follow_redirects=False
    ) as http:
        dados = _get(http, auth + "/token", "autenticacao")
    if (
        not isinstance(dados.get("access_token"), str)
        or not dados["access_token"]
        or type(dados.get("expires_in")) is not int
        or dados["expires_in"] <= 0
    ):
        raise ErroRnds("Resposta de autenticação inválida.")
    try:
        return Token(dados["access_token"], inicio + timedelta(milliseconds=dados["expires_in"]))
    except OverflowError:
        raise ErroRnds("Validade da autorização inválida.") from None


def _identificador(tipo: str, valor: str | None) -> str:
    modulo = {"cpf": cpf, "cns": cns, "cnes": cnes}[tipo]
    if not modulo.valido(valor):
        raise ValueError("Identificador inválido.")
    normalizado = modulo.normalizar(valor)
    assert isinstance(normalizado, str)
    return normalizado


def _pessoa(cpf_valor: str | None, cns_valor: str | None) -> tuple[str, str]:
    if (cpf_valor is None) == (cns_valor is None):
        raise ValueError("Informe exatamente um CPF ou CNS.")
    tipo = "cpf" if cpf_valor is not None else "cns"
    return tipo, _identificador(tipo, cpf_valor if tipo == "cpf" else cns_valor)


class ClienteEhr:
    """Operações explícitas com validação local e ciclo de vida controlado."""

    def __init__(
        self,
        token: Token,
        cns_requisitante: str,
        ambiente: Ambiente,
        uf: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        requisitante = _identificador("cns", cns_requisitante)
        self._ehr = endereco(ambiente, uf).ehr
        self._requisitante = requisitante
        self._base = self._ehr + "/fhir/r4/"
        self._http = httpx.Client(
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            headers={
                "X-Authorization-Server": f"Bearer {token.valor}",
                "Authorization": requisitante,
            },
        )

    def __enter__(self) -> ClienteEhr:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Feche as conexões do cliente."""
        self._http.close()

    def paciente(self, *, cpf: str | None = None, cns: str | None = None) -> dict[str, Any]:
        """Consulte por exatamente um identificador de pessoa."""
        tipo, valor = _pessoa(cpf, cns)
        sistema = sistemas.CPF if tipo == "cpf" else sistemas.CNS
        return _get(
            self._http,
            self._base + "Patient",
            "paciente",
            params={"identifier": f"{sistema}|{valor}"},
        )

    def profissional(self, *, cns: str | None = None, cpf: str | None = None) -> dict[str, Any]:
        """Consulte um profissional por CNS ou CPF."""
        tipo, valor = _pessoa(cpf, cns)
        if tipo == "cns":
            return _get(self._http, self._base + "Practitioner/" + valor, "profissional")
        return _get(
            self._http,
            self._base + "Practitioner",
            "profissional",
            params={"identifier": f"{sistemas.CPF}|{valor}"},
        )

    def lotacoes(self, cns: str, cnes: str) -> dict[str, Any]:
        """Consulte os vínculos entre profissional e estabelecimento."""
        return _get(
            self._http,
            self._base + "PractitionerRole",
            "lotacoes",
            params={
                "practitioner.identifier": f"{sistemas.CNS}|{_identificador('cns', cns)}",
                "organization.identifier": f"{sistemas.CNES}|{_identificador('cnes', cnes)}",
            },
        )

    def estabelecimento(self, cnes_ou_cnpj: str) -> dict[str, Any]:
        """Consulte por CNES válido ou CNPJ com 14 dígitos ASCII."""
        valor = cnes_ou_cnpj
        if not (len(valor) == 14 and valor.isascii() and valor.isdecimal()):
            valor = _identificador("cnes", valor)
        return _get(self._http, self._base + "Organization/" + valor, "estabelecimento")

    def capacidades(self) -> dict[str, Any]:
        """Consulte os metadados completos do serviço."""
        return _get(self._http, self._base + "metadata", "capacidades", params={"mode": "full"})

    def enviar(self, bundle: Mapping[str, Any], *, validar: bool = True) -> Envio:
        """Envie um Bundle uma única vez, validando-o localmente por padrão."""
        achados = tuple(validacao.validar(bundle)) if validar else ()
        if any(achado.severity == "error" for achado in achados):
            raise BundleInvalido(achados)
        resposta = _requisicao(
            self._http,
            self._base + "Bundle",
            "enviar",
            metodo="POST",
            idempotente=False,
            content=json.dumps(dict(bundle), separators=(",", ":")),
            headers={"Content-Type": "application/json"},
        )
        location = resposta.headers.get("Location", "")
        try:
            caminho = urlsplit(location.strip()).path.split("/_history/", 1)[0].rstrip("/")
        except ValueError:
            raise ResultadoIncerto("Confirmação de envio inválida.", status=201) from None
        id_rnds = caminho.rsplit("/", 1)[-1]
        if resposta.status_code != 201 or not id_rnds:
            raise ResultadoIncerto("Confirmação de envio incompleta.", status=resposta.status_code)
        return Envio(id_rnds, location, tuple(a for a in achados if a.severity == "warning"))

    def contexto_atendimento(self, *, cnes: str, cns_paciente: str) -> dict[str, Any]:
        """Obtenha o contexto de atendimento sem remodelar a resposta."""
        return _get(
            self._http,
            self._ehr + "/contexto-atendimento",
            "contexto_atendimento",
            metodo="POST",
            json={
                "cnes": _identificador("cnes", cnes),
                "cnsProfissional": self._requisitante,
                "cnsPaciente": _identificador("cns", cns_paciente),
            },
        )
