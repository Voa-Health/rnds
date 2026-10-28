# Contribuindo

## Ambiente

Instale [uv](https://docs.astral.sh/uv/) e prepare o projeto:

```sh
uv sync --all-extras --group dev
uvx pre-commit install
```

## Padrões

- Escreva textos curtos em português do Brasil.
- Comente apenas intenções que não sejam evidentes no código.
- Use somente dados sintéticos em testes e exemplos.
- Mantenha a biblioteca sem dependências de execução; MCP é opcional.
- Atualize fontes e artefatos somente pelos comandos de manutenção.

## Como contribuir

Para contribuir, execute:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run python scripts/manutencao.py verificar
uv run python scripts/manutencao.py artefatos --check
uv build
```

Confira também a instalação do wheel em um ambiente virtual limpo e a consulta de um CNS sintético.
