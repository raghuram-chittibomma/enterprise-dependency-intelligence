from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthCheckResult(BaseModel):
    ok: bool
    backend: Literal["neo4j", "fallback"]
    detail: str

    def __str__(self) -> str:
        status = "OK" if self.ok else "FAILED"
        return f"[{status}] backend={self.backend} - {self.detail}"
