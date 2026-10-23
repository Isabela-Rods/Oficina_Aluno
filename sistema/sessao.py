"""
sessao.py
---------
"""
from datetime import datetime, timedelta
from functools import wraps

from config import SESSAO_MINUTOS


class Sessao:
    """Guarda quem está logado e até quando a sessão é válida."""

    def __init__(self):
        self.usuario_id = None
        self.usuario_nome = None
        self.expira_em = None

    def iniciar(self, usuario_id, usuario_nome):
        """Abre a sessão após um login bem-sucedido."""
        self.usuario_id = usuario_id
        self.usuario_nome = usuario_nome
        self.expira_em = datetime.now() + timedelta(minutes=SESSAO_MINUTOS)

    def encerrar(self):
        """Fecha a sessão (logout ou expiração)."""
        self.usuario_id = None
        self.usuario_nome = None
        self.expira_em = None

    def logada(self):
        """True se existe alguém logado (mesmo que a sessão já tenha expirado)."""
        return self.usuario_id is not None

    def ativa(self):
        """True se há usuário logado E o tempo de expiração ainda não passou."""
        return self.logada() and datetime.now() < self.expira_em

    def expirada(self):
        """True se havia usuário logado e o tempo de expiração já passou."""
        return self.logada() and datetime.now() >= self.expira_em


# Instância única usada por todo o sistema
sessao = Sessao()

# Função que o main.py registra para tratar a expiração (mostrar aviso + login)
_ao_expirar = None


def registrar_ao_expirar(funcao):
    """Registra a função chamada quando a sessão expira."""
    global _ao_expirar
    _ao_expirar = funcao


def requer_sessao(metodo):
    """
    Decorador para métodos de tela: só executa se a sessão estiver ativa.
    Se estiver expirada (ou inexistente), chama o tratador de expiração
    e NÃO executa o método.
    """
    @wraps(metodo)
    def interno(*args, **kwargs):
        if not sessao.ativa():
            if _ao_expirar:
                _ao_expirar()
            return None
        return metodo(*args, **kwargs)
    return interno
