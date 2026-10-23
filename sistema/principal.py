"""
principal.py
------------
"""
from tkinter import ttk, messagebox

from sessao import sessao, requer_sessao
from dono import JanelaDono
from carro import JanelaCarro
from procedimento import JanelaProcedimento


class TelaPrincipal(ttk.Frame):
    """Menu principal. `ao_sair()` encerra a sessão e volta ao login."""

    def __init__(self, master, ao_sair):
        super().__init__(master, padding=30)
        self.ao_sair = ao_sair

        # Nome do usuário logado
        ttk.Label(self, text=f"Usuário logado: {sessao.usuario_nome}", font=("Arial", 14, "bold")).pack(pady=(0.5))
                

        # Horário em que a sessão expira (informativo)
        ttk.Label(self, text=("Sessão expira às "
                              f"{sessao.expira_em.strftime('%H:%M')}")
                  ).pack(pady=(0, 20))

        # Acesso aos demais recursos
        ttk.Button(self, text="Donos", width=25,
                   command=self.abrir_donos).pack(pady=4)
        ttk.Button(self, text="Carros", width=25,
                   command=self.abrir_carros).pack(pady=4)
        ttk.Button(self, text="Procedimentos", width=25,
                   command=self.abrir_procedimentos).pack(pady=4)


        # Botão Sair
        ttk.Button(self, text="Sair", width=25,
            command=self.sair).pack(pady=(20, 0))



    # Cada recurso abre em uma janela filha (Toplevel)
    @requer_sessao
    def abrir_donos(self):
        JanelaDono(self.winfo_toplevel())

    @requer_sessao
    def abrir_carros(self):
        JanelaCarro(self.winfo_toplevel())

    @requer_sessao
    def abrir_procedimentos(self):
        JanelaProcedimento(self.winfo_toplevel())

    def sair(self):
        if messagebox.askyesno("Sair", "Deseja realmente sair do sistema?",parent=self):self.ao_sair()
