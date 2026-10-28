# RNDS para Python

Identificadores brasileiros e códigos da RNDS em uma biblioteca Python, CLI e servidor MCP. Tudo funciona localmente, sem chamadas de rede.

Projeto de código aberto da Voa Health, **não afiliado ao Ministério da Saúde nem ao DATASUS**. Este pacote não se conecta à RNDS, não autentica e não envia recursos.

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

Instale `pip install "rnds[mcp]"` para iniciar `rnds mcp` ou `rnds-mcp`. O servidor usa transporte stdio e consulta os mesmos dados locais da biblioteca.

Os valores nos exemplos são sintéticos. A biblioteca não valida Bundles FHIR nem acessa serviços hospedados.
