# Fontes de dados

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
