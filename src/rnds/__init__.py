"""Biblioteca offline para identificadores e códigos da RNDS."""

from .codigos import Conceito, Sistema, conceitos, valido

__version__ = "0.1.0"

__all__ = ["Conceito", "Sistema", "__version__", "conceitos", "valido"]
