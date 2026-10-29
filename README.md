# RNDS para Python

Identificadores brasileiros e códigos da RNDS em uma biblioteca Python, CLI e servidor MCP. As ferramentas offline funcionam sem chamadas de rede.

Projeto de código aberto da Voa Health, **não afiliado ao Ministério da Saúde nem ao DATASUS**. O extra opcional `pip install "rnds[cliente]"` permite autenticação mTLS e consultas à RNDS via `rnds.cliente`; não envia recursos. O MCP permanece offline.

## Início rápido

```sh
pip install rnds
rnds cpf 987.654.321-00
rnds cns 712345678901236
rnds cnes 1234567
rnds codigos
```

Use a biblioteca para validar identificadores:

```python
from rnds import cns, cpf, cnes

cpf.valido("987.654.321-00")
cns.valido("712345678901236")
cnes.valido("1234567")
```

Liste CodeSystems e ValueSets ou consulte conceitos offline:

```python
from rnds.codigos import busca, conceitos, sistemas, valido

for sistema in sistemas():
    print(sistema.nome, sistema.total)

url = "https://rnds-fhir.saude.gov.br/CodeSystem/BRNacionalidade"
print(conceitos(url))
print(valido(url, "B"))

url = "https://rnds-fhir.saude.gov.br/ValueSet/BRResultadoQualitativoExame-2.0"
origem = "https://rnds-fhir.saude.gov.br/CodeSystem/BRTipoResultadoAVIDEZ"
print(busca(url, "1"))
print(valido(url, "1", origem=origem))
```

Converta um identificador local para o sistema oficial sem alterar seu valor:

```python
from rnds.sistemas import LOCAL_CPF, para_oficial

identificador = para_oficial({"system": LOCAL_CPF, "value": "98765432100"})
print(identificador)
```

Instale `pip install "rnds[mcp]"` para iniciar `rnds mcp` ou `rnds-mcp`. O servidor usa transporte stdio e consulta os mesmos dados locais da biblioteca, incluindo `rnds_validate` para validar Bundles.

Os valores nos exemplos são sintéticos. Apenas o cliente opcional acessa serviços hospedados.

## Validar um Bundle

Valide um Bundle FHIR localmente, sem conexão ou envio à RNDS:

```python
from rnds import validar

bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
achados = validar(bundle)
```

Também é possível validar um arquivo pela linha de comando ou ler da entrada padrão:

```sh
rnds validate bundle.json
cat bundle.json | rnds validate -
```

A validação verifica que a entrada seja um Bundle, que `fullUrl` não se repita,
que referências relativas (`Tipo/id` e `Tipo/id/_history/v`) ou URN
(`urn:uuid:` e `urn:oid:`) sejam resolvidas, que CPF, CNS e CNES sejam válidos para
seus sistemas, que sistemas `urn:voa:br:` mapeados indiquem o sistema oficial,
que códigos pertençam aos CodeSystems empacotados e que o display corresponda ao conceito.
Erros retornam código de saída `1`; somente avisos ou nenhum achado retornam `0`.
Problemas de leitura, JSON ou limites retornam `2`. O arquivo pode ter até 10 MB e
64 níveis de aninhamento.

A validação de referências não verifica referências absolutas `http(s)`, referências
contidas iniciadas por `#` nem formatos fora de `Tipo/id`, `Tipo/id/_history/v`,
`urn:uuid:` e `urn:oid:`.

Este recurso não verifica perfis completos de StructureDefinition, binding de ValueSet
por elemento, nem envia dados ou se conecta à RNDS.
