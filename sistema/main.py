"""
main.py
-------
"""
import os
import tkinter as tk
from tkinter import messagebox

from login import TelaLogin
from principal import TelaPrincipal
from sessao import sessao, registrar_ao_expirar


class App(tk.Tk):
    """Janela raiz da aplicação."""

    INTERVALO_VIGIA_MS = 5000   # a cada 5 s verifica se a sessão expirou

    def __init__(self):
        super().__init__()
        self.title("Oficina Mecânica")
        self.geometry("420x320")
        self._definir_icone()

        # Quando a sessão expirar (vigia ou ação bloqueada), chama self.expirou
        registrar_ao_expirar(self.expirou)

        self.mostrar_login()
        self.after(self.INTERVALO_VIGIA_MS, self._vigiar)

    def _definir_icone(self):
        """
        Troca o ícone padrão (pena) pelo ícone da oficina (icone.png).
        iconphoto(True, ...) aplica o ícone também a todas as janelas
        filhas (Donos, Carros, Procedimentos) e às caixas de aviso.
        """
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "icone.png")
        try:
            self._icone = tk.PhotoImage(file=caminho)   # guarda a referência
            self.iconphoto(True, self._icone)
        except tk.TclError:
            pass    # sem o arquivo, segue com o ícone padrão

    # ---------------- troca de telas ----------------
    def _limpar(self):
        """Remove tudo da janela (telas e janelas filhas abertas)."""
        for widget in self.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        self._limpar()
        self.geometry("420x320")
        TelaLogin(self, ao_logar=self.mostrar_principal).pack(
            fill="both", expand=True)

    def mostrar_principal(self):
        self._limpar()
        self.geometry("420x320")
        TelaPrincipal(self, ao_sair=self.sair).pack(fill="both", expand=True)

    # ---------------- saída / expiração ----------------
    def sair(self):
        """Logout voluntário: encerra a sessão e volta ao login."""
        sessao.encerrar()
        self.mostrar_login()

    def expirou(self):
        """Sessão expirada: avisa o usuário, encerra e volta ao login."""
        if sessao.logada():                      # evita aviso duplicado
            sessao.encerrar()
            self.mostrar_login()
            messagebox.showwarning(
                "Sessão expirada",
                "Sua sessão expirou. Faça login novamente.", parent=self)

    def _vigiar(self):
        """Verificação periódica do tempo de expiração da sessão."""
        if sessao.expirada():
            self.expirou()
        self.after(self.INTERVALO_VIGIA_MS, self._vigiar)


if __name__ == "__main__":
    App().mainloop()
