<div align="center">
  <a href="https://github.com/Voa-Health/rnds">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/images/logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset=".github/images/logo-light.svg">
      <img alt="Voa" src="https://raw.githubusercontent.com/Voa-Health/rnds/main/.github/images/logo-light.svg" width="160">
    </picture>
  </a>
</div>

<div align="center">
  <h3>RNDS em Python, para pessoas e agentes de IA.</h3>
</div>

<div align="center">
  <a href="https://github.com/Voa-Health/rnds/actions/workflows/ci.yml"><img src="https://github.com/Voa-Health/rnds/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://pypi.org/project/rnds/"><img src="https://img.shields.io/pypi/v/rnds?label=PyPI" alt="Versão no PyPI"></a>
  <a href="https://pypi.org/project/rnds/"><img src="https://img.shields.io/pypi/pyversions/rnds" alt="Versões do Python"></a>
  <a href="https://github.com/Voa-Health/rnds/blob/main/LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-blue" alt="Licença Apache-2.0"></a>
</div>

<div align="center">
  <a href="https://pypi.org/project/rnds/">PyPI</a> ·
  <a href="https://github.com/Voa-Health/rnds/blob/main/docs/codigos.md">Códigos</a> ·
  <a href="https://github.com/Voa-Health/rnds/blob/main/DATA_SOURCES.md">Fontes de dados</a> ·
  <a href="https://rnds-guia.saude.gov.br">Guia RNDS</a>
</div>

<br>

Confira CPF, CNS e CNES, consulte os códigos da RNDS e valide Bundles FHIR antes
do envio, tudo em código aberto: uma biblioteca Python offline, uma CLI, um MCP
local para o seu agente de IA e um cliente opcional para a RNDS.

Projeto da Voa Health, **não afiliado ao Ministério da Saúde nem ao DATASUS**.

<!-- mcp-name: health.voa/rnds -->

> [!TIP]
> Usa Claude Code, Codex ou Cursor? Conecte o MCP e peça em português, por
> exemplo "valide este Bundle antes do envio à RNDS". Veja
> [Conectar agentes](#conectar-agentes).

## Início rápido

```sh
pip install rnds
```

```python
from rnds import cnes, cns, cpf, validar

cpf.valido("987.654.321-00")
cns.valido("712345678901236")
cnes.valido("1234567")

bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
[(achado.code, achado.severity) for achado in validar(bundle)]
```

Cada achado traz um código estável, a gravidade, o caminho no Bundle e uma
mensagem curta. Requer Python 3.10+ e nenhuma dependência de execução.

## Acesso e limites

A biblioteca offline, a CLI e o MCP locais não têm cota de uso.
O MCP hospedado em `https://api.voa.health/mcp/rnds/` aceita
`Authorization: Bearer <chave>` com chave de organização (`sk_voa_`) ou de
membro (`sk_user_`), com escopo `rnds:read`, criada no
[console](https://tiss-api.voa.health/org), ou OAuth.

A cota diária por organização é compartilhada entre Terminologia, RNDS e SNCR,
por chave e OAuth: 1.000 consultas com login, 10.000 para organizações
verificadas; organizações pessoais Pro/Trial/Ultra não têm limite.
Ao exceder a cota, HTTP `429` informa `retry_after` quando disponível e um link
para o console (o cabeçalho `Retry-After` também pode estar presente).
Quando a cobrança estiver habilitada, HTTP `402` traz
`error_name: "PAYMENT_REQUIRED"` e `metadata.billing_url` para pagamento.
Consulte os preços públicos via
[`GET /api/v2/product/rnds/pricing/`](https://api.voa.health/api/v2/product/rnds/pricing/).

## CLI

Instale a CLI com `pip install rnds` ou execute sem instalar com
`uvx rnds validate bundle.json`.

| Comando | Uso |
| --- | --- |
| `rnds cpf <valor>` | Normaliza e confere um CPF. |
| `rnds cns <valor>` | Normaliza e confere um CNS. |
| `rnds cnes <valor>` | Normaliza e confere um CNES. |
| `rnds codigos` | Lista os CodeSystems e ValueSets incluídos. |
| `rnds codigos <url>` | Lista os conceitos de um sistema. |
| `rnds codigos <url> <código>` | Confere um código pelo código de saída, sem saída JSON; `--origem URL` restringe o CodeSystem de um ValueSet. |
| `rnds validate <arquivo\|->` | Valida um Bundle de um arquivo ou da entrada padrão. |
| `rnds ambientes` | Lista os endereços RNDS de homologação e produção. |
| `rnds mcp` | Inicia o MCP local em stdio; requer `rnds[mcp]`. |

As consultas saem em JSON. Os códigos de saída são `0` para sucesso, `1` para
identificador ou código inválido e Bundle com erros, e `2` para uso inválido ou
entrada ilegível.

```sh
$ rnds cpf 987.654.321-00
{"identifica_pessoa": true, "sistema": "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf", "tipo": "cpf", "valido": true, "valor": "98765432100"}
```

## Para quem é

| Você é | O rnds ajuda a |
| --- | --- |
| **Desenvolvedor de prontuário ou sistema de saúde** | conferir identificadores e códigos e validar o Bundle antes de chamar a RNDS |
| **Estabelecimento credenciado na RNDS** | autenticar com o certificado ICP-Brasil, consultar cadastros e enviar documentos com o cliente opcional |
| **Agente de IA** | montar `Identifier` e `Coding` corretos com ferramentas MCP, sem inventar sistemas ou códigos |

## Como funciona

O ciclo antes do envio é sempre o mesmo:

1. **Confira** CPF, CNS e CNES com `rnds.cpf`, `rnds.cns` e `rnds.cnes`.
2. **Converta** sistemas locais para os oficiais com `rnds.sistemas.para_oficial`.
3. **Valide** os códigos com `rnds.codigos.valido`.
4. **Valide** o Bundle com `rnds.validar` até zerar os erros.
5. **Envie** com `ClienteEhr.enviar`, que valida de novo e bloqueia erros antes da rede.

## O que vem no pacote

- **[Biblioteca Python](#referência)**: CPF, CNS, CNES, sistemas oficiais,
  códigos e validação de Bundles, sem rede.
- **[Catálogo de códigos](https://github.com/Voa-Health/rnds/blob/main/docs/codigos.md)**:
  28 CodeSystems e 25 ValueSets do Guia de Implementação RNDS 1.0.0.
- **[MCP local](#conectar-agentes)**: 3 ferramentas em stdio para agentes.
- **[Cliente RNDS](#cliente-rnds-alpha)** (Alpha): autenticação mTLS, consultas
  FHIR e envio de Bundles com o extra `rnds[cliente]`.

## Por que confiar

- **Offline e determinístico:** biblioteca, CLI e MCP rodam na sua máquina, sem
  rede nem telemetria; a mesma entrada dá sempre a mesma saída.
- **Sem dependências:** o pacote base usa apenas a biblioteca padrão; MCP e
  cliente são extras opcionais.
- **Fontes versionadas:** os códigos vêm do Guia de Implementação RNDS e os
  endereços, do guia de integração, listados em
  [Fontes de dados](https://github.com/Voa-Health/rnds/blob/main/DATA_SOURCES.md).
- **À prova de prompt injection:** o texto dos conceitos é dado, nunca instrução.
- **Envio sem surpresa:** o cliente nunca repete operações nem segue
  redirecionamentos, e seus logs não contêm documentos nem identificadores.

## Conectar agentes

### ChatGPT via HTTP

O pacote [ChatGPT](plugins/chatgpt/) expõe somente `rnds_codigos` por HTTP
remoto com OAuth. Consulta códigos públicos incluídos no pacote, sem dados de
paciente ou identificadores; não valida Bundles nem envia documentos à RNDS.
O MCP local em stdio abaixo mantém todas as ferramentas.

Para gerar `dist/rnds-chatgpt-plugin.zip` com `plugin.json` na raiz, execute
na raiz do repositório:

```sh
mkdir -p dist
(cd plugins/chatgpt && zip -r ../../dist/rnds-chatgpt-plugin.zip .)
```

### MCP local em stdio

O MCP local roda offline e mantém os dados na máquina:

```sh
claude mcp add rnds -- uvx --from "rnds[mcp]" rnds mcp
```

| Ferramenta | Uso |
| --- | --- |
| `rnds_identificador` | Normaliza e confere CPF, CNS ou CNES e devolve o sistema oficial. |
| `rnds_codigos` | Lista sistemas, conceitos ou confere um código. |
| `rnds_validate` | Valida um Bundle FHIR e lista os achados. |

Agentes encontram instruções em
[AGENTS.md](https://github.com/Voa-Health/rnds/blob/main/AGENTS.md).

### Codex e Cursor

<details>
<summary>Ver detalhes</summary>

No Codex, adicione a `~/.codex/config.toml`:

```toml
[mcp_servers.rnds]
command = "uvx"
args = ["--from", "rnds[mcp]", "rnds", "mcp"]
```

No Cursor, adicione ao `mcp.json`:

```json
{
  "mcpServers": {
    "rnds": {
      "command": "uvx",
      "args": ["--from", "rnds[mcp]", "rnds", "mcp"]
    }
  }
}
```

</details>

## Validar um Bundle

```python
from rnds import validar

bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
achados = validar(bundle)
```

```sh
rnds validate bundle.json
cat bundle.json | rnds validate -
```

### O que é verificado

<details>
<summary>Ver detalhes</summary>

A validação verifica que a entrada seja um Bundle, que `fullUrl` não se repita,
que referências relativas (`Tipo/id` e `Tipo/id/_history/v`) ou URN
(`urn:uuid:` e `urn:oid:`) sejam resolvidas, que CPF, CNS e CNES sejam válidos para
seus sistemas, que sistemas `urn:voa:br:` mapeados indiquem o sistema oficial,
que códigos pertençam aos CodeSystems incluídos e que o display corresponda ao
conceito. O arquivo pode ter até 10 MB e 64 níveis de aninhamento.

Não são verificadas referências absolutas `http(s)`, referências contidas
iniciadas por `#`, perfis completos de StructureDefinition nem binding de
ValueSet por elemento.

| Código | Gravidade | Significado |
| --- | --- | --- |
| `RNDS-BUNDLE-001` | `error` | A entrada não é um Bundle FHIR. |
| `RNDS-BUNDLE-002` | `error` | O `fullUrl` aparece em mais de uma entrada. |
| `RNDS-REF-001` | `error` | A referência não foi resolvida no Bundle. |
| `RNDS-ID-001` | `error` | O CPF é inválido para o sistema informado. |
| `RNDS-ID-002` | `error` | O CNS é inválido para o sistema informado. |
| `RNDS-ID-003` | `error` | O CNES é inválido para o sistema informado. |
| `RNDS-ID-004` | `warning` | O sistema local pode ser convertido para o oficial. |
| `RNDS-CODE-001` | `error` | O código não existe no CodeSystem incluído. |
| `RNDS-CODE-002` | `warning` | O display difere do conceito incluído. |

</details>

## Cliente RNDS (Alpha)

Instale com `pip install "rnds[cliente]"`. O cliente foi testado somente com
respostas simuladas, sem homologação real. O credenciamento no DATASUS e o
certificado ICP-Brasil são responsabilidade do integrador. Produção não é
ambiente para testes.

Exemplo sintético de homologação, com autorização fictícia (não executável no serviço):

```python
from datetime import datetime, timedelta, timezone
from rnds.cliente import ClienteEhr, Token

autorizacao = Token("autorizacao-sintetica", datetime.now(timezone.utc) + timedelta(minutes=30))
bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
with ClienteEhr(autorizacao, "712345678901236", "homologacao") as cliente:
    envio = cliente.enviar(bundle)
    avisos = envio.avisos
```

O Bundle acima ilustra a chamada, não um documento completo aceito pela RNDS.
Para autenticação real, crie o contexto com `contexto_mtls(pfx, senha)` e obtenha
a autorização com `obter_token(contexto, ambiente)`. Em produção, informe a UF
em `ClienteEhr(..., "producao", uf="sp")`.

### Consultas, envio e erros

<details>
<summary>Ver detalhes</summary>

| Método | Uso |
| --- | --- |
| `paciente(cpf=...)` ou `paciente(cns=...)` | Consulta um paciente por exatamente um identificador. |
| `profissional(cns=...)` ou `profissional(cpf=...)` | Consulta um profissional por exatamente um identificador. |
| `lotacoes(cns, cnes)` | Consulta as lotações de um profissional no estabelecimento. |
| `estabelecimento(cnes_ou_cnpj)` | Consulta um estabelecimento. |
| `capacidades()` | Lê o CapabilityStatement do serviço. |
| `enviar(bundle)` | Valida e envia um Bundle. |
| `contexto_atendimento(cnes=..., cns_paciente=...)` | Consulta o contexto de atendimento. |

`enviar` valida localmente por padrão: erros bloqueiam a rede, avisos seguem em
`Envio.avisos`. `validar=False` desativa essa validação. O corpo não é
remodelado. Sucesso exige HTTP 201 e `Location`; `Envio.id_rnds` desconsidera
`/_history/...`. Nenhuma operação é repetida automaticamente e redirecionamentos
não são seguidos.

| Exceção | Quando repetir |
| --- | --- |
| `BundleInvalido` | Corrigir os achados em `.achados`; nada foi enviado |
| `ErroDeConexao` | Seguro: falha de conexão antes do envio, ou transporte de operação idempotente |
| `ResultadoIncerto` | Não repetir envio antes de reconciliar: pode ter sido aceito |
| `RedirecionamentoRecusado` | Corrigir o endereço, sem seguir automaticamente |
| `NaoAutenticado` | Corrigir autenticação antes de nova tentativa |
| `SemPermissao` | Corrigir permissão antes de nova tentativa |
| `NaoEncontrado` | Conferir o recurso antes de nova tentativa |
| `RequisicaoRecusada` | Corrigir a requisição; consultar `.codigo` e `.issues` explicitamente |
| `ErroRnds` | Consultas/contexto podem ser repetidos após diagnóstico; não reenviar documentos às cegas |

No envio, falhas de leitura/escrita, interrupções, HTTP 5xx e confirmação
incompleta geram `ResultadoIncerto`. `contexto_atendimento` é idempotente como
as consultas e devolve o objeto JSON sem remodelá-lo. Não registre esse retorno:
ele pode conter autorização de acesso. Os logs do cliente contêm somente
operação, status e duração.

</details>

### Substituir um documento

<details>
<summary>Ver detalhes</summary>

Não existe endpoint separado para substituição. Envie um **novo** Bundle contendo
na Composition o relacionamento abaixo, com o identificador RNDS anterior:

```python
relacionamento = {
    "code": "replaces",
    "targetReference": {"reference": "Composition/documento-sintetico-anterior"},
}
# Na nova Composition: "relatesTo": [relacionamento].
```

Isso corresponde a `Composition.relatesTo` com `code=replaces` e
`targetReference.reference = "Composition/<id_rnds anterior>"`.
O cliente não altera o Bundle do chamador.

</details>

## Referência

### Símbolos da biblioteca

<details>
<summary>Ver detalhes</summary>

| Símbolo | Uso |
| --- | --- |
| `cpf.normalizar` / `cpf.valido` | Normaliza e confere um CPF. |
| `cns.normalizar` / `cns.valido` | Normaliza e confere um CNS. |
| `cnes.normalizar` / `cnes.valido` | Normaliza e confere um CNES. |
| `cpf.identifica_pessoa` / `cns.identifica_pessoa` | Indica se o valor é plausível como identificador de pessoa. |
| `sistemas.CPF` / `sistemas.CNS` / `sistemas.CNES` | Sistemas oficiais dos identificadores. |
| `sistemas.para_oficial` / `sistemas.de_oficial` | Converte o sistema de um `Identifier` sem alterar o valor. |
| `sistemas.identificador_documento` | Monta o identificador documental `BRRNDS-<solicitante>`. |
| `codigos.sistemas` | Lista os CodeSystems e ValueSets incluídos. |
| `codigos.conceitos` | Lista os conceitos de um sistema. |
| `codigos.busca` / `codigos.valido` | Busca ou confere um código, com `origem` opcional. |
| `validar` | Valida um Bundle e retorna a lista de achados. |
| `cliente.ambientes` / `cliente.endereco` (extra `cliente`) | Lê os endereços RNDS incluídos, sem rede. |

```python
from rnds.codigos import busca, valido
from rnds.sistemas import LOCAL_CPF, para_oficial

para_oficial({"system": LOCAL_CPF, "value": "98765432100"})
valido("https://rnds-fhir.saude.gov.br/CodeSystem/BRNacionalidade", "B")

url = "https://rnds-fhir.saude.gov.br/ValueSet/BRResultadoQualitativoExame-2.0"
origem = "https://rnds-fhir.saude.gov.br/CodeSystem/BRTipoResultadoAVIDEZ"
busca(url, "1", origem=origem)
```

</details>

### Campos de um achado

<details>
<summary>Ver detalhes</summary>

| Campo | Significado |
| --- | --- |
| `code` | Código estável, como `RNDS-ID-001` |
| `severity` | `error` ou `warning` |
| `path` | Caminho no Bundle, como `Bundle.entry[0].resource.identifier[0].value` |
| `message` | Descrição concisa do achado |

</details>

## Mais

- [Catálogo de códigos](https://github.com/Voa-Health/rnds/blob/main/docs/codigos.md) · [Fontes de dados](https://github.com/Voa-Health/rnds/blob/main/DATA_SOURCES.md) ·
  [Changelog](https://github.com/Voa-Health/rnds/blob/main/CHANGELOG.md)
- [Contribuição](https://github.com/Voa-Health/rnds/blob/main/CONTRIBUTING.md) · [Código de conduta](https://github.com/Voa-Health/rnds/blob/main/CODE_OF_CONDUCT.md) ·
  [Segurança](https://github.com/Voa-Health/rnds/blob/main/SECURITY.md)
- [Licença Apache-2.0](https://github.com/Voa-Health/rnds/blob/main/LICENSE)
