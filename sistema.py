# -*- coding: utf-8 -*-
"""Orquestra a visão computacional e o motor de inferência.

Equipe: <NOME DO INTEGRANTE 1>, <NOME DO INTEGRANTE 2>,
        <NOME DO INTEGRANTE 3>, <NOME DO INTEGRANTE 4>
"""

from dataclasses import dataclass
from typing import Dict, List

from analisador_imagem import AnalisadorBocaDeLobo
from base_conhecimento import diagnosticar


@dataclass
class Relatorio:
    """Reúne dados da imagem, resultado inferido e explicação das regras."""

    caminho_imagem: str
    imagem_anotada: str
    medidas: Dict[str, float]
    fatos: Dict[str, str]
    nivel: str
    causas: List[str]
    recomendacoes: List[dict]
    rastro: List[dict]


def analisar_imagem(caminho, pasta_saida="saida") -> Relatorio:
    """Executa o analisador visual e encaminha seus fatos ao Experta."""
    analisador = AnalisadorBocaDeLobo(pasta_saida=pasta_saida)
    resultado_imagem = analisador.analisar(caminho)
    fatos = resultado_imagem.para_fatos()
    resultado_motor = diagnosticar(fatos)
    return Relatorio(
        caminho_imagem=resultado_imagem.caminho,
        imagem_anotada=resultado_imagem.imagem_anotada,
        medidas=dict(resultado_imagem.medidas),
        fatos=fatos,
        nivel=resultado_motor["nivel"],
        causas=resultado_motor["causas"],
        recomendacoes=resultado_motor["recomendacoes"],
        rastro=resultado_motor["rastro"],
    )


def formatar_relatorio(rel: Relatorio) -> str:
    """Formata o relatório de forma legível para terminal, GUI e arquivo."""
    linhas = [
        "RELATÓRIO DE INSPEÇÃO DA BOCA DE LOBO",
        f"Imagem: {rel.caminho_imagem}",
        f"Nível de obstrução: {rel.nivel}",
        "Causas: " + (", ".join(rel.causas) if rel.causas else "não aplicável"),
        "",
        "Recomendações:",
    ]
    if rel.recomendacoes:
        for item in rel.recomendacoes:
            linhas.append(f"- [{item['prioridade']}] {item['acao']}")
    else:
        linhas.append("- Nenhuma recomendação disponível.")

    linhas.extend(["", "Por que este diagnóstico?"])
    if rel.rastro:
        for item in rel.rastro:
            linhas.append(f"- {item['regra']}: {item['descricao']}")
    else:
        linhas.append("- Nenhuma regra foi registrada.")

    if rel.imagem_anotada:
        linhas.extend(["", f"Imagem anotada: {rel.imagem_anotada}"])
    return "\n".join(linhas)
