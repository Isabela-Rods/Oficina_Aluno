"""
config.py
---------
"""
import os

# ---------------------------------------------------------------------
# Conexão com o MySQL
# ---------------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("SAEP_DB_HOST", "localhost"),
    "port": int(os.getenv("SAEP_DB_PORT", "3306")),
    "user": os.getenv("SAEP_DB_USER", "root"),
    # >>> COLOQUE AQUI A SENHA DO SEU MYSQL <<<
    "password": os.getenv("SAEP_DB_PASSWORD", "Senai@118"),
    "database": "oficina_db",
    "charset": "utf8mb4",
}

# ---------------------------------------------------------------------
# Chave usada para criptografar/descriptografar dados sensíveis (CPF).
# PRECISA ser igual à variável @chave do arquivo oficina_db.sql.
# ---------------------------------------------------------------------
CHAVE_CRIPTOGRAFIA = os.getenv("SAEP_CHAVE", "chave_saep_2025")

# ---------------------------------------------------------------------
# Tempo de expiração da sessão (autenticação com tempo de expiração).
# Após esse tempo o usuário é desconectado automaticamente.
# ---------------------------------------------------------------------
SESSAO_MINUTOS = int(os.getenv("SAEP_SESSAO_MIN", "30"))
