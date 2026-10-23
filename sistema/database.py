"""
database.py
-----------
"""
import mysql.connector
from mysql.connector.errors import Error

from config import DB_CONFIG


def conectar():
    """Abre e retorna uma nova conexão com o MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


def consultar(sql, params=None):
    """
    Executa um SELECT e devolve uma lista de dicionários
    (uma chave por coluna), ex.: [{"id_dono": 1, "nome": "Ana"}].
    """
    con = conectar()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        con.close()


def executar(sql, params=None):
    """
    Executa INSERT / UPDATE / DELETE e confirma (commit).
    Devolve o último ID gerado (útil nos INSERTs).
    Em caso de erro faz rollback e repassa a exceção para a tela tratar.
    """
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute(sql, params or ())
        con.commit()
        return cur.lastrowid
    except Error:
        con.rollback()
        raise
    finally:
        con.close()


def mensagem_erro(erro):
    """Converte erros técnicos do MySQL em mensagens amigáveis."""
    codigo = getattr(erro, "errno", None)
    if codigo == 1062:
        return "Registro duplicado: já existe um cadastro com esses dados."
    if codigo == 1451:
        return ("Não é possível excluir: existem registros vinculados "
                "(ex.: carros ou procedimentos).")
    if codigo == 1452:
        return "Registro relacionado inexistente (dono, carro ou usuário)."
    if codigo in (2002, 2003, 2005, 1045, 1049):
        return ("Não foi possível conectar ao banco. Verifique se o MySQL "
                "está ligado, se o oficina_db.sql foi importado e se a senha "
                "em config.py está correta.")
    return f"Erro no banco de dados: {erro}"
