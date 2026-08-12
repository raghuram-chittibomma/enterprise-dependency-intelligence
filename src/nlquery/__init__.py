"""FR11/FR13: the deterministic natural-language query layer (ADR-0004).

No LLM anywhere in this package. Intent classification (`intent.py`) and
entity resolution (`resolution.py`) are both closed, testable, and
deterministic; `engine.py` dispatches to the *same* FR1-FR10 query
templates a structured route would use, then `answering.py` formats the
result into a fixed-template sentence. Callers use `ask()`.
"""

from src.nlquery.ask import ask

__all__ = ["ask"]
