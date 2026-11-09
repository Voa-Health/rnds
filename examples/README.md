# Validar um Bundle offline

Todos os dados deste diretório são sintéticos. O CPF repete a massa de teste
existente e não representa um paciente. Não envie estes arquivos à RNDS real.

Na raiz do checkout, após `uv sync --all-extras --group dev`:

```sh
uv run rnds validate examples/bundle-laboratorial.json
uv run rnds validate - < examples/bundle-laboratorial.json
```

Ambas as formas retornam `{"achados": []}` e status 0. Não há acesso à rede,
certificados, autenticação nem necessidade de instalar o extra `cliente`.

O exemplo liga uma Observation laboratorial a um Patient por `fullUrl` e
`subject.reference`. A glicose usa [LOINC 2345-7](https://loinc.org/2345-7/) e
UCUM `mg/dL`. O valor serve apenas como dado de teste, sem interpretação clínica.

Experimente em uma cópia do arquivo:

| Alteração | Status | Achado esperado |
| --- | --- | --- |
| Trocar o CPF por `00000000000` | 1 | `RNDS-ID-001` |
| Trocar `subject.reference` por `Patient/ausente` | 1 | `RNDS-REF-001` |
| Remover uma chave de fechamento do JSON | 2 | Erro de leitura de JSON em stderr |

Os testes em `tests/test_cli.py` exercitam o arquivo, stdin e as duas
mutações semânticas. Os status da CLI são: 0 sem erros (pode haver warnings),
1 com achados de erro e 2 para uso/leitura inválidos.

## Limites

`rnds validate` verifica apenas as regras offline documentadas pela biblioteca.
Um resultado sem achados não certifica conformidade FHIR R4, BR-Core ou RNDS.
Este Bundle `collection` é didático, não um documento clínico pronto para envio.
O catálogo empacotado não valida códigos LOINC nem todos os campos obrigatórios
FHIR. Para produção, use também um validador de perfis apropriado e os requisitos
do modelo de informação aplicável.
