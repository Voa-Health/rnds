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
from rnds.codigos import conceitos, sistemas, valido

for sistema in sistemas():
    print(sistema.nome, sistema.total)

url = "https://rnds-fhir.saude.gov.br/CodeSystem/BRNacionalidade"
print(conceitos(url))
print(valido(url, "B"))
```

Instale `pip install "rnds[mcp]"` para iniciar `rnds mcp` ou `rnds-mcp`. O servidor usa transporte stdio e consulta os mesmos dados locais da biblioteca.

Os valores nos exemplos são sintéticos. A biblioteca não valida Bundles FHIR nem acessa serviços hospedados.
