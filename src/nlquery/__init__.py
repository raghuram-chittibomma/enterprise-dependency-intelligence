"""FR11/FR13/FR14: the deterministic natural-language query layer (ADR-0004)
plus MVP2 open-ended Graph RAG (ADR-0005).

No LLM on closed templates. Callers use `ask()`.
"""

from src.nlquery.ask import ask

__all__ = ["ask"]
