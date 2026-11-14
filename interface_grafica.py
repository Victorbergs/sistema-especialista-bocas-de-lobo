# -*- coding: utf-8 -*-
"""Interface gráfica Tkinter para inspecionar uma boca de lobo.

Equipe: <NOME DO INTEGRANTE 1>, <NOME DO INTEGRANTE 2>,
        <NOME DO INTEGRANTE 3>, <NOME DO INTEGRANTE 4>
"""

import base64
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np

from analisador_imagem import AnalisadorBocaDeLobo
from sistema import Relatorio, analisar_imagem


CORES_NIVEL = {
    "livre": "#2e7d32",
    "parcial": "#d6a400",
    "severa": "#e97817",
    "total": "#c62828",
    "indeterminado": "#616161",
}


class InterfaceBocaDeLobo:
    """Coordena a seleção da imagem, análise em segundo plano e relatório."""

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("Inspeção de bocas de lobo")
        self.raiz.geometry("1050x780")
        self.relatorio = None
        self.referencias_imagem = []

        barra = ttk.Frame(raiz, padding=(12, 10))
        barra.pack(fill="x")
        self.botao_escolher = ttk.Button(
            barra, text="Escolher imagem", command=self.escolher_imagem
        )
        self.botao_escolher.pack(side="left")
        self.botao_salvar = ttk.Button(
            barra, text="Salvar relatório (.txt)", command=self.salvar_relatorio,
            state="disabled",
        )
        self.botao_salvar.pack(side="left", padx=(8, 0))
        self.status = ttk.Label(barra, text="Selecione uma imagem para analisar.")
        self.status.pack(side="left", padx=14)

        imagens = ttk.Frame(raiz, padding=(12, 0, 12, 8))
        imagens.pack(fill="x")
        imagens.columnconfigure((0, 1), weight=1, uniform="imagens")
        self.rotulo_original = self._quadro_imagem(imagens, "Imagem original", 0)
        self.rotulo_anotada = self._quadro_imagem(imagens, "Imagem anotada", 1)

        self.rotulo_nivel = tk.Label(
            raiz, text="Nível: aguardando análise", anchor="w", padx=12, pady=8,
            font=("Segoe UI", 14, "bold"), fg="white", bg=CORES_NIVEL["indeterminado"],
        )
        self.rotulo_nivel.pack(fill="x", padx=12, pady=(0, 8))

        detalhes = ttk.Frame(raiz, padding=(12, 0, 12, 12))
        detalhes.pack(fill="both", expand=True)
        detalhes.columnconfigure((0, 1), weight=1, uniform="detalhes")
        detalhes.rowconfigure(1, weight=1)
        self.caixa_causas = self._caixa_texto(detalhes, "Causas", 0, 0, altura=5)
        self.caixa_recomendacoes = self._caixa_texto(
            detalhes, "Recomendações", 0, 1, altura=5
        )
        self.caixa_rastro = self._caixa_texto(
            detalhes, "Por que este diagnóstico?", 1, 0, coluna_span=2, altura=8
        )

    @staticmethod
    def _quadro_imagem(pai, titulo, coluna):
        quadro = ttk.LabelFrame(pai, text=titulo, padding=6)
        quadro.grid(row=0, column=coluna, sticky="nsew", padx=4)
        quadro.columnconfigure(0, weight=1)
        rotulo = ttk.Label(quadro, text="Nenhuma imagem carregada", anchor="center")
        rotulo.grid(row=0, column=0, sticky="nsew")
        rotulo.configure(width=60)
        return rotulo

    @staticmethod
    def _caixa_texto(pai, titulo, linha, coluna, coluna_span=1, altura=4):
        quadro = ttk.LabelFrame(pai, text=titulo, padding=6)
        quadro.grid(
            row=linha, column=coluna, columnspan=coluna_span,
            sticky="nsew", padx=4, pady=4,
        )
        caixa = tk.Text(quadro, height=altura, wrap="word", state="disabled")
        barra = ttk.Scrollbar(quadro, orient="vertical", command=caixa.yview)
        caixa.configure(yscrollcommand=barra.set)
        caixa.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return caixa

    def escolher_imagem(self):
        caminho = filedialog.askopenfilename(
            title="Escolher imagem da boca de lobo",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
                       ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        self.botao_escolher.configure(state="disabled")
        self.botao_salvar.configure(state="disabled")
        self.status.configure(text="Analisando imagem...")
        threading.Thread(target=self._processar, args=(caminho,), daemon=True).start()

    def _processar(self, caminho):
        try:
            relatorio = analisar_imagem(caminho)
            original = AnalisadorBocaDeLobo.carregar(caminho)
            dados = np.fromfile(relatorio.imagem_anotada, dtype=np.uint8)
            anotada = cv2.imdecode(dados, cv2.IMREAD_COLOR)
            if anotada is None:
                raise ValueError("Não foi possível abrir a imagem anotada gerada.")
            self.raiz.after(0, self._mostrar_resultado, relatorio, original, anotada)
        except (FileNotFoundError, ValueError, OSError) as erro:
            self.raiz.after(0, self._mostrar_erro, str(erro))

    def _mostrar_resultado(self, relatorio: Relatorio, original, anotada):
        self.relatorio = relatorio
        self.referencias_imagem = [
            self._criar_imagem_tk(original), self._criar_imagem_tk(anotada)
        ]
        self.rotulo_original.configure(image=self.referencias_imagem[0], text="")
        self.rotulo_anotada.configure(image=self.referencias_imagem[1], text="")
        self.rotulo_nivel.configure(
            text=f"Nível de obstrução: {relatorio.nivel}",
            bg=CORES_NIVEL.get(relatorio.nivel, CORES_NIVEL["indeterminado"]),
        )
        self._preencher(self.caixa_causas, "\n".join(relatorio.causas) or "Não aplicável.")
        recomendacoes = "\n".join(
            f"[{item['prioridade']}] {item['acao']}" for item in relatorio.recomendacoes
        ) or "Nenhuma recomendação disponível."
        self._preencher(self.caixa_recomendacoes, recomendacoes)
        rastro = "\n".join(
            f"{item['regra']}: {item['descricao']}" for item in relatorio.rastro
        ) or "Nenhuma regra registrada."
        self._preencher(self.caixa_rastro, rastro)
        self.status.configure(text=Path(relatorio.caminho_imagem).name)
        self.botao_escolher.configure(state="normal")
        self.botao_salvar.configure(state="normal")

    @staticmethod
    def _criar_imagem_tk(imagem_bgr):
        altura, largura = imagem_bgr.shape[:2]
        escala = min(480 / largura, 300 / altura, 1.0)
        dimensoes = (max(1, int(largura * escala)), max(1, int(altura * escala)))
        reduzida = cv2.resize(imagem_bgr, dimensoes, interpolation=cv2.INTER_AREA)
        try:
            from PIL import Image, ImageTk
            rgb = cv2.cvtColor(reduzida, cv2.COLOR_BGR2RGB)
            return ImageTk.PhotoImage(Image.fromarray(rgb))
        except ImportError:
            sucesso, buffer = cv2.imencode(".png", reduzida)
            if not sucesso:
                raise ValueError("Não foi possível converter a imagem para a interface.")
            conteudo = base64.b64encode(buffer.tobytes()).decode("ascii")
            return tk.PhotoImage(data=conteudo)

    @staticmethod
    def _preencher(caixa, texto):
        caixa.configure(state="normal")
        caixa.delete("1.0", "end")
        caixa.insert("1.0", texto)
        caixa.configure(state="disabled")

    def _mostrar_erro(self, mensagem):
        self.status.configure(text="Falha na análise")
        self.botao_escolher.configure(state="normal")
        messagebox.showerror("Não foi possível analisar", mensagem, parent=self.raiz)

    def salvar_relatorio(self):
        if self.relatorio is None:
            return
        destino = filedialog.asksaveasfilename(
            title="Salvar relatório", defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt")],
            initialfile=f"{Path(self.relatorio.caminho_imagem).stem}_relatorio.txt",
        )
        if not destino:
            return
        from sistema import formatar_relatorio
        try:
            Path(destino).write_text(formatar_relatorio(self.relatorio), encoding="utf-8")
            self.status.configure(text=f"Relatório salvo: {Path(destino).name}")
        except OSError as erro:
            messagebox.showerror("Falha ao salvar", str(erro), parent=self.raiz)


def main():
    raiz = tk.Tk()
    InterfaceBocaDeLobo(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
