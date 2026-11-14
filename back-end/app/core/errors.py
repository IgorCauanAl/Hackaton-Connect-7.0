"""Exceções de domínio. A camada HTTP as traduz para status codes."""


class ErroDeDominio(Exception):
    status_code = 400

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontrado(ErroDeDominio):
    status_code = 404


class AcessoNegado(ErroDeDominio):
    status_code = 403


class RegraDeNegocio(ErroDeDominio):
    status_code = 422


class IAIndisponivel(Exception):
    """Falha do serviço de IA/MCP. Sempre tratada com fallback."""
