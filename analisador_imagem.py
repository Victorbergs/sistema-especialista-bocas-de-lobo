# -*- coding: utf-8 -*-
"""
==============================================================================
 SISTEMA ESPECIALISTA PARA INSPEÇÃO DE BOCAS DE LOBO
 Módulo: analisador_imagem.py  (visão computacional com OpenCV)
==============================================================================
 Equipe: <NOME DO INTEGRANTE 1>, <NOME DO INTEGRANTE 2>,
         <NOME DO INTEGRANTE 3>, <NOME DO INTEGRANTE 4>

 Papel deste módulo no sistema:
   1. Receber o caminho de uma imagem de uma boca de lobo.
   2. Extrair características numéricas (percentuais de cor, bordas,
      aberturas livres, nitidez, etc.) usando OpenCV.
   3. Discretizar essas medidas em categorias qualitativas
      ("baixa", "media", "alta"...), que é o formato ideal de "fato" para
      a base de conhecimentos da shell Experta.
   4. Gerar uma imagem anotada para o usuário conferir o que foi detectado.

 O módulo NÃO toma decisões de diagnóstico. A decisão (ex.: "boca de lobo
 obstruída por lixo") é responsabilidade do motor de inferência (Experta),
 que usará o dicionário retornado por `AnalisadorBocaDeLobo.analisar()`.

 Dependências:  pip install opencv-python numpy
==============================================================================
"""

import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, Tuple

import cv2
import numpy as np


# ------------------------------------------------------------------------------
# CONFIGURAÇÕES (limiares calibráveis)
# ------------------------------------------------------------------------------
# Todos os limiares ficam aqui para facilitar o ajuste pela equipe depois de
# testar com imagens reais. Os valores abaixo são um ponto de partida.

# Largura máxima para a qual a imagem é redimensionada (acelera e padroniza).
LARGURA_PADRAO = 640

# Faixas HSV (H: 0-179, S: 0-255, V: 0-255 no OpenCV).
HSV_VEGETACAO = ((30, 40, 40), (90, 255, 255))     # tons de verde
HSV_TERRA = ((8, 40, 40), (25, 255, 220))          # marrons / sedimento
HSV_COLORIDO = ((0, 120, 80), (179, 255, 255))     # cores muito saturadas
                                                   # (típico de plásticos/lixo)

# Pixel é considerado "escuro" (possível abertura livre / vazio) abaixo disso.
LIMIAR_ESCURO = 50

# Cortes (fração 0..1) usados para transformar números em categorias.
# Formato: (limite_baixa_media, limite_media_alta)
CORTES_PADRAO = (0.10, 0.30)
CORTES_BORDAS = (0.05, 0.15)

# Qualidade da imagem
LIMIAR_NITIDEZ = 60.0       # variância do Laplaciano abaixo disso = borrada
LIMIAR_ESCURA = 60.0        # brilho médio abaixo disso = muito escura
LIMIAR_CLARA = 200.0        # brilho médio acima disso = estourada


# ------------------------------------------------------------------------------
# ESTRUTURA DE RESULTADO
# ------------------------------------------------------------------------------
@dataclass
class ResultadoAnalise:
    """Guarda tudo que foi extraído da imagem."""
    caminho: str = ""
    # Medidas numéricas (valores brutos)
    medidas: Dict[str, float] = field(default_factory=dict)
    # Categorias qualitativas (serão os FATOS da base de conhecimentos)
    categorias: Dict[str, str] = field(default_factory=dict)
    # Caminho da imagem anotada gerada (se houver)
    imagem_anotada: str = ""

    def para_fatos(self) -> Dict[str, str]:
        """Retorna o dicionário que será convertido em Fact() no Experta."""
        return dict(self.categorias)

    def para_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------------------
# CLASSE PRINCIPAL
# ------------------------------------------------------------------------------
class AnalisadorBocaDeLobo:
    """Extrai características visuais de uma imagem de boca de lobo."""

    def __init__(self, pasta_saida: str = "saida"):
        self.pasta_saida = pasta_saida

    # ------------------------------------------------------------------
    # Passo 1: carregar e padronizar a imagem
    # ------------------------------------------------------------------
    @staticmethod
    def carregar(caminho: str) -> np.ndarray:
        """Lê a imagem do disco e a redimensiona mantendo a proporção."""
        if not os.path.isfile(caminho):
            raise FileNotFoundError(f"Imagem não encontrada: {caminho}")

        # np.fromfile + imdecode funciona com caminhos com acentos no Windows.
        dados = np.fromfile(caminho, dtype=np.uint8)
        img = cv2.imdecode(dados, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Arquivo não é uma imagem válida: {caminho}")

        altura, largura = img.shape[:2]
        if largura > LARGURA_PADRAO:
            escala = LARGURA_PADRAO / largura
            img = cv2.resize(img, (LARGURA_PADRAO, int(altura * escala)),
                             interpolation=cv2.INTER_AREA)
        return img

    # ------------------------------------------------------------------
    # Passo 2: região de interesse (ROI)
    # ------------------------------------------------------------------
    @staticmethod
    def definir_roi(img: np.ndarray) -> Tuple[int, int, int, int]:
        """
        Define a região onde a boca de lobo é esperada.
        Versão inicial: recorte central (80% da imagem) para ignorar
        calçada/asfalto nas bordas. Pode ser trocada futuramente por uma
        detecção automática da grade (ex.: contornos retangulares grandes).
        Retorna (x, y, largura, altura).
        """
        h, w = img.shape[:2]
        mx, my = int(w * 0.10), int(h * 0.10)
        return mx, my, w - 2 * mx, h - 2 * my

    # ------------------------------------------------------------------
    # Passo 3: extração das medidas
    # ------------------------------------------------------------------
    def extrair_medidas(self, img: np.ndarray, roi: Tuple[int, int, int, int]
                        ) -> Tuple[Dict[str, float], Dict[str, np.ndarray]]:
        """
        Calcula as medidas numéricas dentro da ROI.
        Retorna (medidas, mascaras) - as máscaras servem para anotar a imagem.
        """
        x, y, w, h = roi
        recorte = img[y:y + h, x:x + w]
        area_total = float(w * h)

        cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
        cinza_suave = cv2.GaussianBlur(cinza, (5, 5), 0)
        hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)

        # Elemento estruturante usado para limpar ruído nas máscaras
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        def limpar(mascara: np.ndarray) -> np.ndarray:
            """Abertura + fechamento: remove pontinhos e fecha buracos."""
            m = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
            return cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel)

        # --- Vegetação (verde) ---
        m_veg = limpar(cv2.inRange(hsv, np.array(HSV_VEGETACAO[0]),
                                   np.array(HSV_VEGETACAO[1])))
        # --- Terra / sedimento (marrom) ---
        m_terra = limpar(cv2.inRange(hsv, np.array(HSV_TERRA[0]),
                                     np.array(HSV_TERRA[1])))
        # --- Cores saturadas (plásticos, sacolas, embalagens) ---
        m_color = limpar(cv2.inRange(hsv, np.array(HSV_COLORIDO[0]),
                                     np.array(HSV_COLORIDO[1])))
        # Remove da máscara "colorido" o que já foi classificado como vegetação
        m_color = cv2.bitwise_and(m_color, cv2.bitwise_not(m_veg))

        # --- Áreas escuras: possíveis aberturas livres (vãos da grade) ---
        _, m_escuro = cv2.threshold(cinza_suave, LIMIAR_ESCURO, 255,
                                    cv2.THRESH_BINARY_INV)
        m_escuro = limpar(m_escuro)

        # Contornos das aberturas escuras (ignora ruído < 0,05% da ROI)
        contornos, _ = cv2.findContours(m_escuro, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        contornos = [c for c in contornos
                     if cv2.contourArea(c) > 0.0005 * area_total]

        # --- Bordas (textura): lixo e folhas geram muitas bordas ---
        bordas = cv2.Canny(cinza_suave, 60, 160)

        # --- Qualidade da imagem ---
        nitidez = float(cv2.Laplacian(cinza, cv2.CV_64F).var())
        brilho = float(np.mean(cinza))

        medidas = {
            "prop_vegetacao": cv2.countNonZero(m_veg) / area_total,
            "prop_terra": cv2.countNonZero(m_terra) / area_total,
            "prop_colorido": cv2.countNonZero(m_color) / area_total,
            "prop_aberturas_livres": cv2.countNonZero(m_escuro) / area_total,
            "num_aberturas": float(len(contornos)),
            "densidade_bordas": cv2.countNonZero(bordas) / area_total,
            "nitidez": nitidez,
            "brilho_medio": brilho,
        }
        # Proporção total estimada de obstrução (soma dos materiais,
        # limitada a 1.0 para evitar sobreposição entre máscaras).
        medidas["prop_obstrucao_estimada"] = min(
            1.0, medidas["prop_vegetacao"] + medidas["prop_terra"]
            + medidas["prop_colorido"])

        mascaras = {
            "vegetacao": m_veg, "terra": m_terra, "colorido": m_color,
            "escuro": m_escuro, "contornos": contornos,  # type: ignore
        }
        return medidas, mascaras

    # ------------------------------------------------------------------
    # Passo 4: discretização (números -> categorias)
    # ------------------------------------------------------------------
    @staticmethod
    def _nivel(valor: float, cortes: Tuple[float, float]) -> str:
        """Converte um valor em 'baixa' / 'media' / 'alta'."""
        if valor < cortes[0]:
            return "baixa"
        if valor < cortes[1]:
            return "media"
        return "alta"

    def categorizar(self, m: Dict[str, float]) -> Dict[str, str]:
        """
        Traduz as medidas em categorias. Os nomes das chaves viram os campos
        dos Facts do Experta, ex.: Fact(vegetacao='alta', terra='baixa').
        """
        cat = {
            "vegetacao": self._nivel(m["prop_vegetacao"], CORTES_PADRAO),
            "terra": self._nivel(m["prop_terra"], CORTES_PADRAO),
            "residuos_coloridos": self._nivel(m["prop_colorido"], CORTES_PADRAO),
            "aberturas_livres": self._nivel(m["prop_aberturas_livres"],
                                            CORTES_PADRAO),
            "textura": self._nivel(m["densidade_bordas"], CORTES_BORDAS),
            "obstrucao_total": self._nivel(m["prop_obstrucao_estimada"],
                                           (0.20, 0.50)),
        }

        # Qualidade da imagem (o sistema pode pedir nova foto se for ruim)
        if m["nitidez"] < LIMIAR_NITIDEZ:
            cat["qualidade_imagem"] = "borrada"
        elif m["brilho_medio"] < LIMIAR_ESCURA:
            cat["qualidade_imagem"] = "escura"
        elif m["brilho_medio"] > LIMIAR_CLARA:
            cat["qualidade_imagem"] = "estourada"
        else:
            cat["qualidade_imagem"] = "boa"
        return cat

    # ------------------------------------------------------------------
    # Passo 5: imagem anotada
    # ------------------------------------------------------------------
    def anotar(self, img: np.ndarray, roi: Tuple[int, int, int, int],
               mascaras: dict, medidas: Dict[str, float]) -> np.ndarray:
        """Desenha sobre a imagem o que o programa detectou."""
        saida = img.copy()
        x, y, w, h = roi
        sobreposicao = saida[y:y + h, x:x + w].copy()

        # Pinta cada tipo de material com uma cor (BGR)
        sobreposicao[mascaras["vegetacao"] > 0] = (0, 200, 0)      # verde
        sobreposicao[mascaras["terra"] > 0] = (30, 90, 160)        # marrom
        sobreposicao[mascaras["colorido"] > 0] = (0, 0, 255)       # vermelho
        # Mistura 50% com a imagem original para manter visibilidade
        saida[y:y + h, x:x + w] = cv2.addWeighted(
            saida[y:y + h, x:x + w], 0.5, sobreposicao, 0.5, 0)

        # Contorno das aberturas livres (ciano)
        for c in mascaras["contornos"]:
            c_deslocado = c + np.array([[x, y]])
            cv2.drawContours(saida, [c_deslocado], -1, (255, 255, 0), 2)

        # Retângulo da ROI
        cv2.rectangle(saida, (x, y), (x + w, y + h), (255, 255, 255), 2)

        # Legenda
        linhas = [
            f"Vegetacao: {medidas['prop_vegetacao']:.0%}",
            f"Terra: {medidas['prop_terra']:.0%}",
            f"Residuos: {medidas['prop_colorido']:.0%}",
            f"Aberturas livres: {medidas['prop_aberturas_livres']:.0%}",
        ]
        for i, texto in enumerate(linhas):
            cv2.putText(saida, texto, (10, 25 + 22 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
            cv2.putText(saida, texto, (10, 25 + 22 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return saida

    # ------------------------------------------------------------------
    # Interface pública: pipeline completo
    # ------------------------------------------------------------------
    def analisar(self, caminho: str, salvar_anotada: bool = True
                 ) -> ResultadoAnalise:
        """
        Executa todo o pipeline em uma imagem e devolve um ResultadoAnalise.
        É este método que a interface/motor de inferência vai chamar.
        """
        img = self.carregar(caminho)
        roi = self.definir_roi(img)
        medidas, mascaras = self.extrair_medidas(img, roi)
        categorias = self.categorizar(medidas)

        resultado = ResultadoAnalise(caminho=caminho, medidas=medidas,
                                     categorias=categorias)

        if salvar_anotada:
            os.makedirs(self.pasta_saida, exist_ok=True)
            nome = os.path.splitext(os.path.basename(caminho))[0]
            destino = os.path.join(self.pasta_saida, f"{nome}_anotada.png")
            anotada = self.anotar(img, roi, mascaras, medidas)
            # imencode + tofile: seguro para caminhos com acentos
            ok, buf = cv2.imencode(".png", anotada)
            if ok:
                buf.tofile(destino)
                resultado.imagem_anotada = destino
        return resultado


# ------------------------------------------------------------------------------
# EXECUÇÃO DIRETA (teste rápido pela linha de comando)
#   python analisador_imagem.py caminho/da/imagem.jpg
# ------------------------------------------------------------------------------
def _main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python analisador_imagem.py <imagem>")
        return 1
    res = AnalisadorBocaDeLobo().analisar(sys.argv[1])
    print("\n== Medidas ==")
    for k, v in res.medidas.items():
        print(f"  {k:26s} {v:8.3f}")
    print("\n== Fatos para o Experta ==")
    for k, v in res.para_fatos().items():
        print(f"  {k:26s} {v}")
    print(f"\nImagem anotada: {res.imagem_anotada}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())