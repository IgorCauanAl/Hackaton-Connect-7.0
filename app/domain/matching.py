"""Motor de compatibilidade (BO-RF-05). Domínio puro: sem I/O, sem IA, determinístico.

Padrão Strategy: cada critério é uma estratégia que devolve uma pontuação 0..1.
O motor só combina pesos (configuráveis em config/matching.json) e ordena.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import inf

ORCAMENTOS = {"ate_100": (0, 100), "100_300": (100, 300), "300_800": (300, 800), "acima": (800, inf)}
PRAZOS_DIAS = {"ate_15_dias": 15, "ate_2_meses": 60, "sem_pressa": inf}


@dataclass(frozen=True)
class PerfilDemanda:
    objetivo: str
    dificuldade: str
    canais: frozenset[str]
    ferramentas: frozenset[str]
    orcamento: str
    urgencia: str
    ramo: str
    tags: frozenset[str]


@dataclass(frozen=True)
class PerfilStartup:
    id: int
    nome: str
    categoria: str
    objetivos: frozenset[str]
    dores: frozenset[str]
    tags: frozenset[str]
    segmentos: frozenset[str]
    canais: frozenset[str]
    preco_min: float
    preco_max: float
    dias_implantacao: int


@dataclass(frozen=True)
class ResultadoCriterio:
    criterio: str
    peso: int
    pontuacao: float  # 0..1
    pontos: float  # peso * pontuacao
    motivo: str

    def to_dict(self) -> dict:
        return {"criterio": self.criterio, "peso": self.peso, "pontuacao": round(self.pontuacao, 2),
                "pontos": round(self.pontos, 1), "motivo": self.motivo}


@dataclass(frozen=True)
class Recomendacao:
    startup_id: int
    nome: str
    indice: int
    motivo: str
    criterios: tuple[ResultadoCriterio, ...]


@dataclass(frozen=True)
class ResultadoMatching:
    recomendacoes: tuple[Recomendacao, ...]

    @property
    def sem_match(self) -> bool:
        return not self.recomendacoes


# ---------------------------------------------------------------- critérios
class Criterio(ABC):
    nome: str

    @abstractmethod
    def pontuar(self, d: PerfilDemanda, s: PerfilStartup) -> tuple[float, str]:
        """Retorna (pontuação 0..1, detalhe usado na frase de motivo)."""


class DorEspecifica(Criterio):
    nome = "dor_especifica"

    def pontuar(self, d, s):
        return (1.0 if d.dificuldade in s.dores else 0.0), d.dificuldade


class TagsIA(Criterio):
    nome = "tags_ia"

    def pontuar(self, d, s):
        if not d.tags:
            return 0.0, ""
        comuns = sorted(d.tags & s.tags)
        return len(comuns) / len(d.tags), ", ".join(comuns)


class Objetivo(Criterio):
    nome = "objetivo"

    def pontuar(self, d, s):
        return (1.0 if d.objetivo in s.objetivos else 0.0), d.objetivo


class Ramo(Criterio):
    nome = "ramo"

    def pontuar(self, d, s):
        if d.ramo in s.segmentos:
            return 1.0, d.ramo
        return (0.6 if "varejo" in s.segmentos else 0.0), d.ramo


class Canais(Criterio):
    nome = "canais"

    def pontuar(self, d, s):
        if not d.canais:
            return 0.5, ""
        return len(d.canais & s.canais) / len(d.canais), ""


class Preco(Criterio):
    nome = "preco"

    def pontuar(self, d, s):
        _, teto = ORCAMENTOS.get(d.orcamento, (0, inf))
        if s.preco_min > teto:
            return 0.0, ""
        if s.preco_max <= teto:
            return 1.0, ""
        return (teto - s.preco_min) / (s.preco_max - s.preco_min), ""


class FerramentaAtual(Criterio):
    nome = "ferramenta_atual"

    def pontuar(self, d, s):
        return (0.2 if s.categoria in d.ferramentas else 1.0), s.categoria


class Urgencia(Criterio):
    nome = "urgencia"

    def pontuar(self, d, s):
        prazo = PRAZOS_DIAS.get(d.urgencia, inf)
        if s.dias_implantacao <= prazo:
            return 1.0, ""
        return max(0.0, 1 - (s.dias_implantacao - prazo) / prazo), ""


CRITERIOS_PADRAO: tuple[Criterio, ...] = (
    DorEspecifica(), TagsIA(), Objetivo(), Ramo(), Canais(), Preco(), FerramentaAtual(), Urgencia(),
)


# -------------------------------------------------------------------- motor
@dataclass
class MotorMatching:
    pesos: dict[str, int]
    frases: dict[str, dict[str, str]]
    corte: int = 50
    max_recomendacoes: int = 3
    criterios: tuple[Criterio, ...] = field(default=CRITERIOS_PADRAO)

    def __post_init__(self):
        if sum(self.pesos.values()) != 100:
            raise ValueError("A soma dos pesos de matching deve ser 100.")
        faltando = {c.nome for c in self.criterios} - set(self.pesos)
        if faltando:
            raise ValueError(f"Critérios sem peso configurado: {faltando}")

    @classmethod
    def de_config(cls, cfg: dict) -> "MotorMatching":
        return cls(pesos=cfg["pesos"], frases=cfg["frases"], corte=cfg["corte"],
                   max_recomendacoes=cfg["max_recomendacoes"])

    def calcular(self, demanda: PerfilDemanda, startups: list[PerfilStartup]) -> ResultadoMatching:
        avaliadas = [self._avaliar(demanda, s) for s in startups]
        elegiveis = [r for r in avaliadas if r.indice >= self.corte]
        # desempate determinístico: índice desc, nome asc
        elegiveis.sort(key=lambda r: (-r.indice, r.nome))
        return ResultadoMatching(tuple(elegiveis[: self.max_recomendacoes]))

    def _avaliar(self, d: PerfilDemanda, s: PerfilStartup) -> Recomendacao:
        resultados = []
        for c in self.criterios:
            pont, detalhe = c.pontuar(d, s)
            peso = self.pesos[c.nome]
            nivel = "alto" if pont >= 0.8 else "medio" if pont >= 0.4 else "baixo"
            motivo = self.frases[c.nome][nivel].format(detalhe=detalhe)
            resultados.append(ResultadoCriterio(c.nome, peso, pont, peso * pont, motivo))
        indice = round(sum(r.pontos for r in resultados))
        return Recomendacao(s.id, s.nome, indice, self._motivo_resumido(resultados), tuple(resultados))

    @staticmethod
    def _motivo_resumido(resultados: list[ResultadoCriterio]) -> str:
        fortes = sorted((r for r in resultados if r.pontuacao >= 0.8), key=lambda r: -r.pontos)[:2]
        return "; ".join(r.motivo for r in fortes) or "Compatibilidade parcial"
