"""Erros do módulo IA/MCP e seu mapeamento para HTTP."""

from __future__ import annotations


class IAError(Exception):
    """Erro base do módulo."""


class ConfigurationError(IAError):
    """Configuração ausente ou inválida."""


class VocabularyError(IAError):
    """Vocabulário de tags inválido, ausente ou ilegível."""


class ProviderError(IAError):
    """Erro técnico de um provedor de IA."""


class ProviderUnavailableError(ProviderError):
    """Provedor indisponível: rede, timeout, erro HTTP ou serviço fora do ar."""


class InvalidProviderResponseError(ProviderError):
    """Provedor respondeu, mas o conteúdo não pôde ser interpretado."""


class ServiceUnavailableError(IAError):
    """Todos os provedores falharam tecnicamente (contrato HTTP 503)."""


class BackendUnavailableError(IAError):
    """API REST do backend operacional indisponível ou com resposta inválida."""


__all__ = [
    "BackendUnavailableError",
    "ConfigurationError",
    "IAError",
    "InvalidProviderResponseError",
    "ProviderError",
    "ProviderUnavailableError",
    "ServiceUnavailableError",
    "VocabularyError",
]
