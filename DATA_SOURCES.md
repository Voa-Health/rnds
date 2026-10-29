# Fontes de dados

## Guia de integração RNDS

- Ambientes: https://rnds-guia.saude.gov.br/docs/rnds/ambientes
- Serviços: https://rnds-guia.saude.gov.br/docs/rnds/servicos
- Consultas: https://rnds-guia.saude.gov.br/docs/publico-alvo/ti/conhecer
- Erros: https://rnds-guia.saude.gov.br/docs/publico-alvo/ti/erros
- Autenticação: https://rnds-guia.saude.gov.br/docs/publico-alvo/ti/autenticacao
- Identificador: https://rnds-guia.saude.gov.br/docs/publico-alvo/gestor/identificador

São registrados apenas fatos técnicos, sem reprodução dos exemplos das fontes.
O guia de integração prevalece sobre o manual SOA-RNDS de 2020.

| Tema | Manual SOA-RNDS 2020 | Guia de integração adotado |
| --- | --- | --- |
| Bases de produção | Referência anterior | Auth único `ehr-auth.saude.gov.br`; EHR por UF |
| Bases de homologação | Referência anterior | `ehr-auth-hmg.saude.gov.br`; `ehr-services.hmg.saude.gov.br` |
| Validade da autorização | Unidade não usada pelo cliente | `expires_in=1800000`, milissegundos |
| Identificador documental | Não inferir do estabelecimento | `BRRNDS-<solicitante>` do credenciamento |

Todas as bases usam HTTPS e caminho `/api`. Autenticação: GET `/token` com
certificado de cliente, sem cabeçalho `Authorization`. Consultas usam
`X-Authorization-Server: Bearer <valor>` e `Authorization: <CNS requisitante>`.
As consultas FHIR usam `/fhir/r4/`. Diagnósticos podem conter `EHR-ERR881`,
`EHR-ERR866`, `EHR-ERR882`, `EHR-ERR906` e `EHR-ERR924`.

### Envio e contexto de atendimento

- Coleção Postman referenciada pelo guia: https://raw.githubusercontent.com/kyriosdata/rnds/master/tools/postman/rnds-postman-collection.json
- Documentação da coleção: https://documenter.getpostman.com/view/215332/TVewY47S
- Serviços e métodos: https://rnds-guia.saude.gov.br/docs/rnds/servicos

Fatos adotados: envio por POST `/api/fhir/r4/Bundle`, sucesso 201 com
identificador documental em `Location`. A substituição usa o mesmo endereço e um
novo Bundle com `Composition.relatesTo`, `code` igual a `replaces` e
`targetReference.reference` igual a `Composition/<identificador anterior>`.
O serviço descrito como obtenção de autorização para contexto de atendimento usa
POST `/api/contexto-atendimento`, fora do caminho FHIR, com campos `cnes`,
`cnsProfissional` e `cnsPaciente` no objeto JSON. Os cabeçalhos de segurança
são os mesmos das consultas. Nenhum exemplo da coleção é reproduzido.

## Guia de Implementação RNDS 1.0.0

- Fonte: pacote público do Guia de Implementação da RNDS.
- URL: https://rnds-fhir.saude.gov.br/package.tgz
- Versão do FHIR: 4.0.1.
- SHA-256 do pacote: `2888bec577dd55c748c2b5aee70050a65b5e4e57c7464b7be23819410ab61bd8`.
- Data de captura: 2026-10-28.
- Atribuição: Ministério da Saúde do Brasil.
- O manifesto do pacote declara `CC0-1.0`; o site do guia não publica uma licença explícita. Por isso, a distribuição contém somente códigos, displays, sistemas e versões. Códigos HL7 enumerados em ValueSets acompanham o display publicado no guia.

O recorte está versionado em `scripts/fontes/rnds-1.0.0.json`. A geração dos dados incluídos no pacote é offline e usa esse arquivo.

## NamingSystems

- CPF: https://rnds-fhir.saude.gov.br/NamingSystem-cpf.json
- CNS: https://rnds-fhir.saude.gov.br/NamingSystem-cns.json
- CNES: https://rnds-fhir.saude.gov.br/NamingSystem-cnes.json
- O campo `uniqueId` de tipo URI define o valor esperado em `Identifier.system`.
