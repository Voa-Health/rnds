# Registro de alterações

## Não lançado

- Cliente opcional para autenticação mTLS e consultas FHIR, sem repetição automática.
- Endereços RNDS versionados e comando offline `rnds ambientes`.
- Identificador documental com o solicitante do credenciamento.

## 0.1.0

- Biblioteca offline para normalizar e validar CPF, CNS e CNES.
- Sistemas locais e oficiais de identificadores brasileiros.
- Catálogo offline de CodeSystems e ValueSets do Guia de Implementação RNDS 1.0.0.
- Busca de códigos por origem com `rnds.codigos.busca` e `rnds.codigos.valido(..., origem=...)`.
- Interface de linha de comando e servidor MCP local em stdio.
- Validação offline de Bundles com `rnds validate` e a ferramenta MCP `rnds_validate`.
