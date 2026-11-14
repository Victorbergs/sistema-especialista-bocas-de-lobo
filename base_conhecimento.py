# -*- coding: utf-8 -*-
"""Base de conhecimento e motor de inferência Experta.

Equipe: <NOME DO INTEGRANTE 1>, <NOME DO INTEGRANTE 2>,
        <NOME DO INTEGRANTE 3>, <NOME DO INTEGRANTE 4>
"""

import compat  # O remendo precisa ser aplicado antes da importação do Experta.

from experta import AS, NOT, Fact, KnowledgeEngine, L, Rule


# As ações são sugestões editáveis pela equipe, sem caráter de norma técnica.
ACOES_NIVEL = {
    "livre": ("baixa", "Manter a inspeção periódica de rotina."),
    "parcial": ("media", "Programar limpeza preventiva e reinspecionar depois."),
    "severa": ("alta", "Realizar limpeza com urgência e inspecionar a rede a jusante."),
    "total": ("urgente", "Realizar desobstrução imediata e sinalizar o risco de alagamento."),
    "indeterminado": ("media", "Realizar inspeção presencial ou obter nova foto."),
}

ACOES_CAUSA = {
    "vegetacao": (
        "Remover manualmente folhas e galhos.",
        "Podar a vegetação próxima.",
        "Avaliar a instalação de tela de proteção.",
    ),
    "sedimento": (
        "Remover o sedimento com equipamento de sucção ou pá.",
        "Verificar possível erosão a montante.",
    ),
    "residuos": (
        "Remover manualmente os resíduos com EPI.",
        "Destinar corretamente o lixo recolhido.",
        "Considerar ações de educação ambiental no local.",
    ),
}

CAMPOS_IMAGEM = {
    "vegetacao", "terra", "residuos_coloridos", "aberturas_livres",
    "textura", "obstrucao_total", "qualidade_imagem",
}
_CATEGORIAS = {"baixa", "media", "alta"}
_QUALIDADES = {"boa", "borrada", "escura", "estourada"}


class Imagem(Fact):
    """Fato com as categorias extraídas pelo analisador de imagem."""


class Diagnostico(Fact):
    """Fato com o nível de obstrução inferido."""


class Causa(Fact):
    """Fato com uma causa predominante ou agrupada."""


class Recomendacao(Fact):
    """Fato com uma ação sugerida e sua prioridade."""


class MotorBocaDeLobo(KnowledgeEngine):
    """Executa as regras e conserva o resultado da inferência por imagem."""

    def __init__(self):
        super().__init__()
        self.nivel = None
        self.causas = []
        self.recomendacoes = []
        self.rastro = []

    def _registrar(self, regra, descricao):
        """Guarda cada decisão disparada para explicar o resultado."""
        self.rastro.append({"regra": regra, "descricao": descricao})

    def _adicionar_recomendacao(self, acao, prioridade):
        recomendacao = {"acao": acao, "prioridade": prioridade}
        if recomendacao not in self.recomendacoes:
            self.recomendacoes.append(recomendacao)
            self.declare(Recomendacao(**recomendacao))

    def _adicionar_causa(self, tipo):
        if tipo not in self.causas:
            self.causas.append(tipo)
            self.declare(Causa(tipo=tipo))

    @Rule(AS.imagem << Imagem(
        qualidade_imagem=L("borrada") | L("escura") | L("estourada")
    ),
          salience=100)
    def qualidade_inadequada(self, imagem):
        """Interrompe a inferência quando a foto não permite diagnóstico."""
        qualidade = imagem["qualidade_imagem"]
        nivel = "indeterminado"
        acao = f"Tirar nova foto: imagem {qualidade}."
        prioridade = ACOES_NIVEL[nivel][0]
        self.nivel = nivel
        self.declare(Diagnostico(nivel=nivel))
        self._adicionar_recomendacao(acao, prioridade)
        self._registrar(
            "qualidade_inadequada",
            f"A imagem está {qualidade}; as demais regras não serão executadas.",
        )
        self.halt()

    @Rule(Imagem(qualidade_imagem=L("boa"), obstrucao_total=L("baixa"),
                 aberturas_livres=L("baixa")), salience=50)
    def nivel_indeterminado_revisao(self):
        self._definir_nivel(
            "indeterminado", "Obstrução estimada baixa com poucas aberturas livres; requer revisão manual."
        )

    @Rule(Imagem(qualidade_imagem=L("boa"), obstrucao_total=L("baixa"),
                 aberturas_livres=L("media") | L("alta")), salience=50)
    def nivel_livre(self):
        self._definir_nivel("livre", "Obstrução estimada baixa e aberturas livres em nível médio ou alto.")

    @Rule(Imagem(qualidade_imagem=L("boa"), obstrucao_total=L("media"),
                 aberturas_livres=L("baixa")), salience=50)
    def nivel_severo_obstrucao_media(self):
        self._definir_nivel("severa", "Obstrução estimada média e poucas aberturas livres.")

    @Rule(Imagem(qualidade_imagem=L("boa"), obstrucao_total=L("media"),
                 aberturas_livres=L("media") | L("alta")), salience=50)
    def nivel_parcial(self):
        self._definir_nivel("parcial", "Obstrução estimada média com aberturas livres médias ou altas.")

    @Rule(Imagem(qualidade_imagem=L("boa"), obstrucao_total=L("alta"),
                 aberturas_livres=L("baixa")), salience=50)
    def nivel_total(self):
        self._definir_nivel("total", "Obstrução estimada alta e poucas aberturas livres.")

    @Rule(Imagem(qualidade_imagem=L("boa"), obstrucao_total=L("alta"),
                 aberturas_livres=L("media") | L("alta")), salience=50)
    def nivel_severo_obstrucao_alta(self):
        self._definir_nivel(
            "severa", "Obstrução estimada alta apesar das aberturas livres; adotado o lado conservador."
        )

    def _definir_nivel(self, nivel, descricao):
        self.nivel = nivel
        self.declare(Diagnostico(nivel=nivel))
        self._registrar(f"nivel_{nivel}", descricao)

    @Rule(Imagem(qualidade_imagem=L("boa"), vegetacao=L("media") | L("alta")),
          Diagnostico(nivel=L("parcial") | L("severa") | L("total")), salience=31)
    def causa_vegetacao(self):
        self._adicionar_causa("vegetacao")
        self._registrar("causa_vegetacao", "Vegetação em nível médio ou alto.")

    @Rule(Imagem(qualidade_imagem=L("boa"), terra=L("media") | L("alta")),
          Diagnostico(nivel=L("parcial") | L("severa") | L("total")), salience=31)
    def causa_sedimento(self):
        self._adicionar_causa("sedimento")
        self._registrar("causa_sedimento", "Terra ou sedimento em nível médio ou alto.")

    @Rule(Imagem(qualidade_imagem=L("boa"), residuos_coloridos=L("media") | L("alta")),
          Diagnostico(nivel=L("parcial") | L("severa") | L("total")), salience=31)
    def causa_residuos(self):
        self._adicionar_causa("residuos")
        self._registrar("causa_residuos", "Resíduos coloridos em nível médio ou alto.")

    @Rule(Diagnostico(nivel=L("parcial") | L("severa") | L("total")),
          Causa(tipo="vegetacao"), Causa(tipo="sedimento"), salience=30)
    def causas_mistas_vegetacao_sedimento(self):
        self._adicionar_causa("mista")
        self._registrar("causa_mista", "Mais de uma categoria de causa foi identificada.")

    @Rule(Diagnostico(nivel=L("parcial") | L("severa") | L("total")),
          Causa(tipo="vegetacao"), Causa(tipo="residuos"), salience=30)
    def causas_mistas_vegetacao_residuos(self):
        self._adicionar_causa("mista")
        self._registrar("causa_mista", "Mais de uma categoria de causa foi identificada.")

    @Rule(Diagnostico(nivel=L("parcial") | L("severa") | L("total")),
          Causa(tipo="sedimento"), Causa(tipo="residuos"), salience=30)
    def causas_mistas_sedimento_residuos(self):
        self._adicionar_causa("mista")
        self._registrar("causa_mista", "Mais de uma categoria de causa foi identificada.")

    @Rule(Diagnostico(nivel=L("parcial") | L("severa") | L("total")),
          NOT(Causa(tipo="vegetacao")), NOT(Causa(tipo="sedimento")),
          NOT(Causa(tipo="residuos")), salience=29)
    def causa_nao_identificada(self):
        self._adicionar_causa("nao_identificada")
        self._registrar("causa_nao_identificada", "Nenhuma causa atingiu nível médio.")

    @Rule(Diagnostico(nivel=L("livre")), salience=10)
    def recomendar_nivel_livre(self):
        self._recomendar_nivel("livre")

    @Rule(Diagnostico(nivel=L("parcial")), salience=10)
    def recomendar_nivel_parcial(self):
        self._recomendar_nivel("parcial")

    @Rule(Diagnostico(nivel=L("severa")), salience=10)
    def recomendar_nivel_severo(self):
        self._recomendar_nivel("severa")

    @Rule(Diagnostico(nivel=L("total")), salience=10)
    def recomendar_nivel_total(self):
        self._recomendar_nivel("total")

    @Rule(Diagnostico(nivel=L("indeterminado")), salience=10)
    def recomendar_nivel_indeterminado(self):
        self._recomendar_nivel("indeterminado")

    def _recomendar_nivel(self, nivel):
        prioridade, acao = ACOES_NIVEL[nivel]
        self._adicionar_recomendacao(acao, prioridade)
        self._registrar(f"recomendacao_nivel_{nivel}", f"Ação geral para o nível {nivel}.")

    @Rule(Causa(tipo=L("vegetacao")), NOT(Causa(tipo="mista")), salience=10)
    def recomendar_vegetacao(self):
        self._recomendar_causa("vegetacao")

    @Rule(Causa(tipo=L("sedimento")), NOT(Causa(tipo="mista")), salience=10)
    def recomendar_sedimento(self):
        self._recomendar_causa("sedimento")

    @Rule(Causa(tipo=L("residuos")), NOT(Causa(tipo="mista")), salience=10)
    def recomendar_residuos(self):
        self._recomendar_causa("residuos")

    @Rule(Causa(tipo="mista"), salience=10)
    def recomendar_causas_mistas(self):
        # A ordem permite tratar primeiro o lixo, depois o material mineral e a vegetação.
        for tipo in ("residuos", "sedimento", "vegetacao"):
            for acao in ACOES_CAUSA[tipo]:
                self._adicionar_recomendacao(acao, "media")
        self._registrar("recomendacao_mista", "Ações combinadas na ordem resíduos, sedimento e vegetação.")

    def _recomendar_causa(self, tipo):
        for acao in ACOES_CAUSA[tipo]:
            self._adicionar_recomendacao(acao, "media")
        self._registrar(f"recomendacao_{tipo}", f"Ações específicas para a causa {tipo}.")


def diagnosticar(fatos: dict) -> dict:
    """Executa uma inferência isolada e devolve o resultado em tipos simples."""
    if set(fatos) != CAMPOS_IMAGEM:
        faltantes = sorted(CAMPOS_IMAGEM - set(fatos))
        extras = sorted(set(fatos) - CAMPOS_IMAGEM)
        raise ValueError(f"Fatos inválidos; faltantes: {faltantes}; extras: {extras}")
    for campo in CAMPOS_IMAGEM - {"qualidade_imagem"}:
        if fatos[campo] not in _CATEGORIAS:
            raise ValueError(f"Categoria inválida para {campo}: {fatos[campo]!r}")
    if fatos["qualidade_imagem"] not in _QUALIDADES:
        raise ValueError(f"Qualidade de imagem inválida: {fatos['qualidade_imagem']!r}")

    motor = MotorBocaDeLobo()
    motor.reset()
    motor.declare(Imagem(**fatos))
    motor.run()
    return {
        "nivel": motor.nivel,
        "causas": list(motor.causas),
        "recomendacoes": list(motor.recomendacoes),
        "rastro": list(motor.rastro),
    }
