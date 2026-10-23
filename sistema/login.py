"""
login.py
--------
"""
import tkinter as tk
from tkinter import ttk, messagebox
from mysql.connector.errors import Error

from database import consultar, mensagem_erro
from seguranca import conferir_senha
from sessao import sessao

class ErroLogin(Exception):
    """Falha de autenticação; a mensagem explica o motivo ao usuário."""


# ---------------------------------------------------------------------
# LÓGICA (independente da interface)
# ---------------------------------------------------------------------
def autenticar(login, senha):
    """
    Valida as credenciais. Retorna o registro do usuário se estiverem
    corretas; caso contrário levanta ErroLogin com o motivo da negação.
    """
    login = (login or "").strip()
    senha = senha or ""

    # 1) campos obrigatórios
    if not login and not senha:
        raise ErroLogin("Informe o usuário e a senha.")
    if not login:
        raise ErroLogin("Informe o usuário.")
    if not senha:
        raise ErroLogin("Informe a senha.")

    # 2) o usuário existe?
    usuarios = consultar(
        "SELECT id_usuario, nome, salt, senha_hash "
        "FROM usuario WHERE login = %s",
        (login,),
    )
    if not usuarios:
        raise ErroLogin("Usuário não encontrado.")

    usuario = usuarios[0]

    # 3) a senha confere com o hash armazenado?
    if not conferir_senha(senha, usuario["salt"], usuario["senha_hash"]):
        raise ErroLogin("Senha incorreta.")

    return usuario


# ---------------------------------------------------------------------
# INTERFACE (mínima)
# ---------------------------------------------------------------------
class TelaLogin(ttk.Frame):
    """Tela de login. Chama `ao_logar()` quando a autenticação der certo."""

    def __init__(self, master, ao_logar):
        super().__init__(master, padding=30)
        self.ao_logar = ao_logar

        ttk.Label(self, text="Oficina Mecânica - Login",
                  font=("Arial", 14, "bold")).grid(row=0, column=0,
                                                   columnspan=2, pady=(0, 15))

        ttk.Label(self, text="Usuário:").grid(row=1, column=0, sticky="e", pady=4)
        self.var_login = tk.StringVar()
        self.ent_login = ttk.Entry(self, textvariable=self.var_login, width=28)
        self.ent_login.grid(row=1, column=1, pady=4)

        ttk.Label(self, text="Senha:").grid(row=2, column=0, sticky="e", pady=4)
        self.var_senha = tk.StringVar()
        # show="*" esconde a senha enquanto é digitada
        self.ent_senha = ttk.Entry(self, textvariable=self.var_senha,
                                   show="*", width=28)
        self.ent_senha.grid(row=2, column=1, pady=4)

        ttk.Button(self, text="Entrar", command=self.entrar).grid(
            row=3, column=0, columnspan=2, pady=15)

        # Enter em qualquer campo também faz login
        self.ent_login.bind("<Return>", lambda e: self.entrar())
        self.ent_senha.bind("<Return>", lambda e: self.entrar())
        self.ent_login.focus_set()

    def entrar(self):
        """Tenta autenticar; mostra o motivo caso falhe."""
        try:
            usuario = autenticar(self.var_login.get(), self.var_senha.get())
        except ErroLogin as e:
            # Falha de autenticação: mostra o motivo e limpa a senha
            messagebox.showwarning("Falha no login", str(e), parent=self)
            self.var_senha.set("")
            return
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return

        # Sucesso: abre a sessão (com expiração) e vai para a tela principal
        sessao.iniciar(usuario["id_usuario"], usuario["nome"])
        self.ao_logar()