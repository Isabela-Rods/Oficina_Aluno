"""
carro.py
--------
"""
import tkinter as tk
from tkinter import ttk, messagebox
from mysql.connector.errors import Error

from database import consultar, mensagem_erro

# Sugestão de marcas para o formulário (use se quiser)
MARCAS = ("Chevrolet", "Fiat", "Ford", "Honda", "Hyundai", "Toyota",
          "Volkswagen", "Outra")


# =====================================================================
# CAMADA DE DADOS
# =====================================================================
def listar_carros():
    """Lista todos os carros já com o nome do dono (JOIN)."""
    return consultar(
        "SELECT c.id_carro, c.modelo, c.marca, c.placa, c.ano, "
        "       c.id_dono, d.nome AS dono_nome "
        "FROM carro c JOIN dono d ON d.id_dono = c.id_dono "
        "ORDER BY c.modelo"
    )




# =====================================================================
# INTERFACE (mínima)
# =====================================================================
class JanelaCarro(tk.Toplevel):
    """Janela de gerenciamento de carros."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Carros")
        self.geometry("900x560")
        self._montar()
        self.carregar()

    # ---------------- montagem da tela ----------------
    def _montar(self):
        # --- Tabela de carros ---
        meio = ttk.Frame(self, padding=8)
        meio.pack(fill="both", expand=True)
        colunas = ("id", "modelo", "marca", "placa", "ano", "dono")
        self.tabela = ttk.Treeview(meio, columns=colunas, show="headings",
                                   height=10)
        titulos = {"id": ("ID", 50), "modelo": ("Modelo", 150),
                   "marca": ("Marca", 100), "placa": ("Placa", 90),
                   "ano": ("Ano", 60), "dono": ("Dono", 250)}
        for col, (titulo, largura) in titulos.items():
            self.tabela.heading(col, text=titulo, anchor="w")
            self.tabela.column(col, width=largura)
        barra = ttk.Scrollbar(meio, orient="vertical",
                              command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")


        # --- Voltar ---
        rodape = ttk.Frame(self, padding=8)
        rodape.pack(fill="x")
        ttk.Button(rodape, text="Voltar", command=self.destroy).pack(side="left")

    # ---------------- carga de dados ----------------
    def carregar(self):
        """Recarrega a tabela de carros."""
        try:
            carros = listar_carros()
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return
        self.tabela.delete(*self.tabela.get_children())
        for c in carros:
            self.tabela.insert("", "end", iid=str(c["id_carro"]), values=(
                c["id_carro"], c["modelo"], c["marca"], c["placa"],
                c["ano"], f"{c['id_dono']} - {c['dono_nome']}"))
