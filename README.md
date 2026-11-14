# Sistema especialista para bocas de lobo

Aplicação acadêmica que combina medidas visuais calculadas com OpenCV e regras de inferência implementadas com Experta. O resultado apresenta o nível estimado de obstrução, causas, recomendações e o rastro das regras disparadas. As recomendações são sugestões e não substituem uma inspeção técnica.

## Requisitos

- Python 3.9 ou superior.
- Tkinter para a interface gráfica.

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Executar

Interface gráfica:

```powershell
python interface_grafica.py
```

Linha de comando, com uma imagem ou uma pasta:

```powershell
python main.py caminho\para\imagem.jpg
python main.py caminho\para\pasta_de_imagens
```

Formatos reconhecidos: JPG, JPEG, PNG, BMP, TIF, TIFF e WEBP. Imagens anotadas são salvas em `saida/`.

## Dependências importantes

Experta 1.9.4 usa aliases de `collections` removidos em versões recentes do Python. `compat.py` restaura esses aliases; mantenha a importação feita antes de Experta em `base_conhecimento.py`.

## Conteúdo deste repositório

Este repositório contém apenas os fontes da aplicação e suas dependências. Imagens, datasets, rótulos, resultados de calibração e arquivos gerados não estão incluídos.
