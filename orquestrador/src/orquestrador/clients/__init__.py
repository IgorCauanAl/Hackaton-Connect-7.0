"""Clientes dos serviços externos (backend operacional e IA/MCP)."""

from orquestrador.clients.backend import BackendClient
from orquestrador.clients.ia import IAClient

__all__ = ["BackendClient", "IAClient"]
