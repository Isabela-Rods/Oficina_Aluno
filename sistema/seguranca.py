"""
seguranca.py
------------
"""
import hashlib
import hmac
import re
import secrets


# ---------------------------------------------------------------------
# Utilitários de texto
# ---------------------------------------------------------------------
def somente_digitos(texto):
    """Remove tudo que não for número. Ex.: '529.982.247-25' -> '52998224725'."""
    return re.sub(r"\D", "", texto or "")


def texto(valor):
    """Converte qualquer valor vindo do banco em str (trata None e bytes)."""
    if valor is None:
        return ""
    if isinstance(valor, (bytes, bytearray)):
        return bytes(valor).decode("utf-8", errors="replace")
    return str(valor)


# ---------------------------------------------------------------------
# Senha: hash + salt
# ---------------------------------------------------------------------
def gerar_salt():
    """Gera um salt aleatório (16 caracteres hexadecimais)."""
    return secrets.token_hex(8)


def gerar_hash(senha, salt):
    """SHA-256 de (salt + senha). Mesma fórmula usada no oficina_db.sql."""
    return hashlib.sha256((salt + senha).encode("utf-8")).hexdigest()


def conferir_senha(senha, salt, hash_banco):
    """Compara a senha digitada com o hash do banco (tempo constante)."""
    return hmac.compare_digest(gerar_hash(senha, salt),
                               texto(hash_banco).lower())


# ---------------------------------------------------------------------
# CPF
# ---------------------------------------------------------------------
def validar_cpf(cpf):
    """
    Valida apenas o FORMATO do CPF: precisa ter exatamente 11 dígitos.
    (Não confere os dígitos verificadores, conforme solicitado.)
    """
    return len(somente_digitos(cpf)) == 11


def mascara_cpf(digitos):
    """
    Máscara PROGRESSIVA usada enquanto o usuário digita.
    '3334445556' -> '333.444.555-6'   |   '33344455566' -> '333.444.555-66'
    """
    d = somente_digitos(digitos)[:11]
    if len(d) <= 3:
        return d
    if len(d) <= 6:
        return f"{d[:3]}.{d[3:]}"
    if len(d) <= 9:
        return f"{d[:3]}.{d[3:6]}.{d[6:]}"
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def mascara_celular(digitos):
    """
    Máscara PROGRESSIVA usada enquanto o usuário digita.
    '11999998888' -> '(11) 99999-8888'  |  '1133334444' -> '(11) 3333-4444'
    """
    d = somente_digitos(digitos)[:11]
    if not d:
        return ""
    if len(d) <= 2:
        return f"({d}"
    if len(d) <= 6:
        return f"({d[:2]}) {d[2:]}"
    if len(d) <= 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return f"({d[:2]}) {d[2:7]}-{d[7:]}"


def formatar_cpf(cpf):
    """'52998224725' -> '529.982.247-25' (para exibição)."""
    d = somente_digitos(cpf)
    if len(d) != 11:
        return d
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


# ---------------------------------------------------------------------
# Celular
# ---------------------------------------------------------------------
def validar_celular(celular):
    """Aceita DDD + 8 ou 9 dígitos (10 ou 11 números)."""
    return len(somente_digitos(celular)) in (10, 11)


def formatar_celular(celular):
    """'11987654321' -> '(11) 98765-4321' (para exibição)."""
    d = somente_digitos(celular)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return d


# ---------------------------------------------------------------------
# Placa de veículo
# ---------------------------------------------------------------------
def normalizar_placa(placa):
    """'abc-1d23' -> 'ABC1D23' (maiúscula, sem hífen/espaço)."""
    return re.sub(r"[^A-Za-z0-9]", "", placa or "").upper()


def validar_placa(placa):
    """Aceita o padrão antigo (ABC1234) e o Mercosul (ABC1D23)."""
    return re.fullmatch(r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}",
                        normalizar_placa(placa)) is not None


def formatar_placa(placa):
    """'ABC1234' -> 'ABC-1234' ; Mercosul permanece 'ABC1D23'."""
    p = normalizar_placa(placa)
    if re.fullmatch(r"[A-Z]{3}[0-9]{4}", p):
        return f"{p[:3]}-{p[3:]}"
    return p


# ---------------------------------------------------------------------
# Máscaras de data e hora (usadas nos formulários de carro e procedimento)
# ---------------------------------------------------------------------
def mascara_data(digitos):
    """
    Máscara progressiva dd/mm/aaaa. A barra entra sozinha ao completar o
    dia e o mês, mas também pode ser digitada.
    '12' -> '12/'   |   '1203' -> '12/03/'   |   '12032020' -> '12/03/2020'
    """
    d = somente_digitos(digitos)[:8]
    if len(d) < 2:
        return d
    if len(d) < 4:
        return f"{d[:2]}/{d[2:]}"
    return f"{d[:2]}/{d[2:4]}/{d[4:]}"


def mascara_hora(digitos):
    """
    Máscara progressiva hh:mm. Os dois-pontos entram sozinhos ao completar
    a hora, mas também podem ser digitados.
    '14' -> '14:'   |   '1430' -> '14:30'
    """
    d = somente_digitos(digitos)[:4]
    if len(d) < 2:
        return d
    return f"{d[:2]}:{d[2:]}"


def mascara_mes_ano(digitos):
    """Máscara progressiva mm/aaaa. '10' -> '10/'  |  '102026' -> '10/2026'."""
    d = somente_digitos(digitos)[:6]
    if len(d) < 2:
        return d
    return f"{d[:2]}/{d[2:]}"


def mascara_ano(digitos):
    """Apenas 4 dígitos para o ano. '2026' -> '2026'."""
    return somente_digitos(digitos)[:4]


def aplicar_mascara(entry, var, mascara):
    """
    Liga uma máscara a um campo de texto (Entry + sua tk.StringVar).

    A cada alteração:
      * descarta tudo que não for número (separadores digitados como
        '/', ':' , '.' , '-' são aceitos e refeitos pela máscara);
      * limita o tamanho e reescreve o texto já formatado;
      * MANTÉM O CURSOR no lugar certo (logo após o último dígito digitado),
        inclusive pulando o separador automático. Ao apagar (backspace),
        o separador sobrando no fim é removido para não "travar".
    """
    estado = {"anterior": var.get()}

    def ao_alterar(*_):
        atual = var.get()
        try:
            pos = entry.index("insert")
        except Exception:
            pos = len(atual)

        # quantos dígitos existem antes do cursor (referência para reposicionar)
        digitos_antes = len(somente_digitos(atual[:pos]))

        formatado = mascara(somente_digitos(atual))
        apagando = len(atual) < len(estado["anterior"])
        if apagando:
            # ao apagar, tira o separador do fim (ex.: '12/' -> '12')
            formatado = re.sub(r"\D+$", "", formatado)

        # calcula a nova posição do cursor: logo após o N-ésimo dígito
        nova = 0
        contados = 0
        if digitos_antes > 0:
            for i, ch in enumerate(formatado):
                if ch.isdigit():
                    contados += 1
                    if contados == digitos_antes:
                        nova = i + 1
                        break
            else:
                nova = len(formatado)
            # digitando: se o próximo caractere é um separador, pula-o
            if (not apagando and nova < len(formatado)
                    and not formatado[nova].isdigit()):
                nova += 1

        estado["anterior"] = formatado
        if formatado != atual:
            var.set(formatado)
        # after_idle garante que o Tk não sobrescreva a posição depois
        entry.after_idle(lambda: entry.icursor(nova))

    var.trace_add("write", ao_alterar)
