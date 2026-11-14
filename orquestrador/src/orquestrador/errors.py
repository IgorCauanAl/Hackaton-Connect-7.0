"""Erros do orquestrador e mapeamento único para HTTP (ORQ-RF-06)."""

from __future__ import annotations


class ErroDeOrquestracao(Exception):
    """Erro controlado, sempre devolvido com ``detail``/``codigo``/``etapa``."""

    status: int = 500
    codigo: str = "erro_interno"

    def __init__(
        self,
        detalhe: str,
        *,
        etapa: str = "orquestracao",
        codigo: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(detalhe)
        self.detalhe = detalhe
        self.etapa = etapa
        if codigo is not None:
            self.codigo = codigo
        if status is not None:
            self.status = status


class ErroDeValidacao(ErroDeOrquestracao):
    """Violação de pré-condição de negócio (ORQ-RF-07)."""

    status = 409
    codigo = "regra_de_negocio"


class AcessoNegado(ErroDeOrquestracao):
    status = 403
    codigo = "acesso_negado"


class RequisicaoInvalida(ErroDeOrquestracao):
    status = 422
    codigo = "requisicao_invalida"


class ServicoIndisponivel(ErroDeOrquestracao):
    """Timeout/rede ao falar com um serviço externo."""

    status = 503
    codigo = "servico_indisponivel"


class FalhaNoBackend(ErroDeOrquestracao):
    """Backend respondeu 5xx."""

    status = 502
    codigo = "backend_indisponivel"


class RespostaInvalida(ErroDeOrquestracao):
    """Serviço respondeu 2xx, mas fora do contrato esperado."""

    status = 502
    codigo = "contrato_invalido"


class IAIndisponivel(Exception):
    """IA/MCP indisponível ou fora do contrato. Não é fatal: aciona fallback."""


__all__ = [
    "AcessoNegado",
    "ErroDeOrquestracao",
    "ErroDeValidacao",
    "FalhaNoBackend",
    "IAIndisponivel",
    "RequisicaoInvalida",
    "RespostaInvalida",
    "ServicoIndisponivel",
]
