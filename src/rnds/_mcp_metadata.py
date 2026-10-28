"""Definições estáveis das ferramentas MCP."""

from typing import Any

FERRAMENTAS: tuple[dict[str, Any], ...] = (
    {
        "name": "rnds_identificador",
        "description": "Normalize e confira um identificador brasileiro.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["cpf", "cns", "cnes"]},
                "valor": {"type": "string"},
            },
            "required": ["tipo", "valor"],
        },
    },
    {
        "name": "rnds_codigos",
        "description": "Consulte sistemas e códigos incluídos na RNDS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sistema": {"type": "string"},
                "codigo": {"type": "string"},
            },
        },
    },
)
