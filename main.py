# -*- coding: utf-8 -*-
"""Interface de linha de comando para análise de uma imagem ou pasta.

Equipe: <NOME DO INTEGRANTE 1>, <NOME DO INTEGRANTE 2>,
        <NOME DO INTEGRANTE 3>, <NOME DO INTEGRANTE 4>
"""

import argparse
from pathlib import Path

from sistema import analisar_imagem, formatar_relatorio


EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def main():
    parser = argparse.ArgumentParser(description="Analisa obstrução em bocas de lobo.")
    parser.add_argument("caminho", help="Caminho de uma imagem ou pasta de imagens")
    argumentos = parser.parse_args()
    origem = Path(argumentos.caminho)

    if origem.is_dir():
        caminhos = sorted(
            caminho for caminho in origem.rglob("*")
            if caminho.is_file() and caminho.suffix.lower() in EXTENSOES_IMAGEM
        )
        if not caminhos:
            parser.error(f"A pasta não contém imagens reconhecidas: {origem}")
    elif origem.is_file():
        caminhos = [origem]
    else:
        parser.error(f"Caminho não encontrado: {origem}")

    falhas = 0
    for indice, caminho in enumerate(caminhos):
        if indice:
            print("\n" + "=" * 72 + "\n")
        try:
            relatorio = analisar_imagem(str(caminho))
            print(formatar_relatorio(relatorio))
        except (FileNotFoundError, ValueError, OSError) as erro:
            falhas += 1
            print(f"Erro ao analisar {caminho}: {erro}")

    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
