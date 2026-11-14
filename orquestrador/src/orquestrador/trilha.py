"""Trilha de execução: etapas e avisos devolvidos ao frontend."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Iterator


@dataclass
class Trilha:
    """Registra a sequência executada sem expor dados sensíveis."""

    etapas: list[dict[str, Any]] = field(default_factory=list)
    avisos: list[dict[str, str]] = field(default_factory=list)

    def registrar(
        self,
        etapa: str,
        status: str,
        *,
        detalhe: str | None = None,
        duracao_ms: int | None = None,
    ) -> None:
        item: dict[str, Any] = {"etapa": etapa, "status": status}
        if detalhe:
            item["detalhe"] = detalhe
        if duracao_ms is not None:
            item["duracao_ms"] = duracao_ms
        self.etapas.append(item)

    def aviso(self, codigo: str, detalhe: str) -> None:
        self.avisos.append({"codigo": codigo, "detalhe": detalhe})

    def como_dict(self) -> dict[str, Any]:
        return {"etapas": list(self.etapas), "avisos": list(self.avisos)}


@contextmanager
def etapa(trilha: Trilha, nome: str) -> Iterator[None]:
    """Registra sucesso/falha e a duração de uma etapa."""

    inicio = perf_counter()
    try:
        yield
    except Exception as exc:
        trilha.registrar(
            nome,
            "falha",
            detalhe=str(exc),
            duracao_ms=int((perf_counter() - inicio) * 1000),
        )
        raise
    else:
        trilha.registrar(
            nome,
            "ok",
            duracao_ms=int((perf_counter() - inicio) * 1000),
        )


__all__ = ["Trilha", "etapa"]
