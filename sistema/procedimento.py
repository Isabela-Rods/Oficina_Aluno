"""
procedimento.py
---------------
"""
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox
from mysql.connector.errors import Error

from config import CHAVE_CRIPTOGRAFIA
from database import consultar, executar, mensagem_erro
from seguranca import (formatar_cpf, formatar_celular, formatar_placa, texto,
                       mascara_data, mascara_hora, mascara_mes_ano,
                       mascara_ano, aplicar_mascara)
from sessao import sessao, requer_sessao

# ---------------------------------------------------------------------
# Configuração dos modos de visualização
# ---------------------------------------------------------------------
MODOS = ("Dia", "Mês", "Ano")
FORMATOS = {"Dia": "%d/%m/%Y", "Mês": "%m/%Y", "Ano": "%Y"}
DICAS = {"Dia": "dd/mm/aaaa", "Mês": "mm/aaaa", "Ano": "aaaa"}
MASCARAS = {"Dia": mascara_data, "Mês": mascara_mes_ano, "Ano": mascara_ano}
STATUS = ("AGENDADO", "REALIZADO", "CANCELADO")


# =====================================================================
# LÓGICA DE PERÍODO (independente da interface)
# =====================================================================
def calcular_intervalo(modo, texto_periodo):
    """
    Converte o modo + texto digitado em um intervalo [inicio, fim).
    Ex.: modo 'Mês', '10/2026' -> (2026-10-01 00:00, 2026-11-01 00:00).
    Levanta ValueError se o texto não estiver no formato do modo.
    """
    data = datetime.strptime(texto_periodo.strip(), FORMATOS[modo])

    if modo == "Dia":
        inicio = data.replace(hour=0, minute=0, second=0)
        fim = inicio + timedelta(days=1)
    elif modo == "Mês":
        inicio = data.replace(day=1)
        if inicio.month == 12:
            fim = inicio.replace(year=inicio.year + 1, month=1)
        else:
            fim = inicio.replace(month=inicio.month + 1)
    else:  # Ano
        inicio = datetime(data.year, 1, 1)
        fim = datetime(data.year + 1, 1, 1)
    return inicio, fim


# =====================================================================
# CAMADA DE DADOS
# =====================================================================
def listar_procedimentos(intervalo=None):
    """
    Lista procedimentos ordenados por data/hora, com TODOS os dados do
    dono e do carro. Se `intervalo` (inicio, fim) for dado, filtra por ele.
    """
    sql = (
        "SELECT a.id_procedimento, a.data_hora, a.descricao, a.status, a.id_carro, "
        "       p.modelo AS carro_modelo, p.marca, p.placa, p.ano, "
        "       t.id_dono, t.nome AS dono_nome, "
        "       CAST(AES_DECRYPT(t.cpf, %s) AS CHAR) AS dono_cpf, "
        "       t.endereco, t.celular "
        "FROM procedimento a "
        "JOIN carro   p ON p.id_carro   = a.id_carro "
        "JOIN dono t ON t.id_dono = p.id_dono "
    )
    params = [CHAVE_CRIPTOGRAFIA]

    if intervalo:
        sql += "WHERE a.data_hora >= %s AND a.data_hora < %s "
        params += [intervalo[0], intervalo[1]]

    # Ordenação por dia (e hora) do procedimento
    sql += "ORDER BY a.data_hora ASC"
    return consultar(sql, params)


def listar_carros_com_dono():
    """Carros com o nome do dono, para o combobox do formulário."""
    return consultar(
        "SELECT p.id_carro, p.modelo AS carro_modelo, p.placa, t.nome AS dono_nome "
        "FROM carro p JOIN dono t ON t.id_dono = p.id_dono "
        "ORDER BY p.modelo"
    )


def inserir_procedimento(data_hora, descricao, status, id_carro, id_usuario):
    return executar(
        "INSERT INTO procedimento (data_hora, descricao, status, id_carro, id_usuario) "
        "VALUES (%s, %s, %s, %s, %s)",
        (data_hora, descricao, status, id_carro, id_usuario),
    )


def atualizar_procedimento(id_procedimento, data_hora, descricao, status, id_carro):
    executar(
        "UPDATE procedimento SET data_hora = %s, descricao = %s, status = %s, "
        "id_carro = %s WHERE id_procedimento = %s",
        (data_hora, descricao, status, id_carro, id_procedimento),
    )


def excluir_procedimento(id_procedimento):
    executar("DELETE FROM procedimento WHERE id_procedimento = %s",
             (id_procedimento,))


# =====================================================================
# INTERFACE (mínima)
# =====================================================================
class JanelaProcedimento(tk.Toplevel):
    """Janela de gerenciamento e listagem de procedimentos."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Procedimentos")
        self.geometry("1250x680")
        self.id_selecionado = None
        self.mapa_carros = {}          # texto do combobox -> id_carro
        self._montar()
        self._carregar_carros()
        self.mostrar_todos()         # começa listando tudo, ordenado por dia

    # ---------------- montagem da tela ----------------
    def _montar(self):
        # --- Barra de filtro: Dia / Mês / Ano ---
        topo = ttk.Frame(self, padding=8)
        topo.pack(fill="x")

        ttk.Label(topo, text="Visualizar por:").pack(side="left")
        self.var_modo = tk.StringVar(value="Dia")
        cmb = ttk.Combobox(topo, textvariable=self.var_modo, values=MODOS,
                           state="readonly", width=6)
        cmb.pack(side="left", padx=5)
        # Ao trocar o modo, sugere o período atual e já filtra
        cmb.bind("<<ComboboxSelected>>", lambda e: self.trocar_modo())

        ttk.Label(topo, text="Período:").pack(side="left", padx=(10, 0))
        self.var_periodo = tk.StringVar()
        ent = ttk.Entry(topo, textvariable=self.var_periodo, width=14)
        ent.pack(side="left", padx=5)
        ent.bind("<Return>", lambda e: self.filtrar())
        # Máscara do período muda conforme o modo (Dia / Mês / Ano)
        aplicar_mascara(ent, self.var_periodo,
                        lambda d: MASCARAS[self.var_modo.get()](d))
        self.lbl_dica = ttk.Label(topo, text=f"({DICAS['Dia']})")
        self.lbl_dica.pack(side="left")

        ttk.Button(topo, text="Filtrar", command=self.filtrar).pack(side="left", padx=5)
        ttk.Button(topo, text="Mostrar todos",
                   command=self.mostrar_todos).pack(side="left")
        self.lbl_total = ttk.Label(topo, text="")
        self.lbl_total.pack(side="right")

        # --- Tabela (com barra horizontal, pois tem muitas colunas) ---
        meio = ttk.Frame(self, padding=(8, 0))
        meio.pack(fill="both", expand=True)
        colunas = ("id", "data", "hora", "status", "descricao",
                   "carro", "marca", "placa", "ano",
                   "dono", "cpf", "endereco", "celular")
        self.tabela = ttk.Treeview(meio, columns=colunas, show="headings",
                                   height=10)
        titulos = {
            "id": ("ID", 40), "data": ("Data", 85), "hora": ("Hora", 50),
            "status": ("Status", 95), "descricao": ("Descrição", 220),
            "carro": ("Modelo", 100), "marca": ("Marca", 90),
            "placa": ("Placa", 80), "ano": ("Ano", 50),
            "dono": ("Dono", 130), "cpf": ("CPF Dono", 110),
            "endereco": ("Endereço Dono", 250), "celular": ("Celular", 110),
        }
        for col, (titulo, largura) in titulos.items():
            self.tabela.heading(col, text=titulo, anchor="w")  # cabeçalho à esquerda
            self.tabela.column(col, width=largura)
        barra_v = ttk.Scrollbar(meio, orient="vertical", command=self.tabela.yview)
        barra_h = ttk.Scrollbar(meio, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=barra_v.set,
                              xscrollcommand=barra_h.set)
        barra_v.pack(side="right", fill="y")
        barra_h.pack(side="bottom", fill="x")
        self.tabela.pack(side="left", fill="both", expand=True)
        self.tabela.bind("<<TreeviewSelect>>", self.selecionar)

        # --- Formulário ---
        form = ttk.LabelFrame(self, text="Dados do procedimento", padding=8)
        form.pack(fill="x", padx=8, pady=8)

        self.var_carro = tk.StringVar()
        self.var_data = tk.StringVar()
        self.var_hora = tk.StringVar()
        self.var_descricao = tk.StringVar()
        self.var_status = tk.StringVar(value="AGENDADO")

        ttk.Label(form, text="Carro:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.cmb_carro = ttk.Combobox(form, textvariable=self.var_carro,
                                    state="readonly", width=45,
                                    postcommand=self._carregar_carros)
        self.cmb_carro.grid(row=0, column=1, sticky="w")

        ttk.Label(form, text="Data (dd/mm/aaaa):").grid(row=0, column=2, sticky="e", padx=4)
        ent_data = ttk.Entry(form, textvariable=self.var_data, width=14)
        ent_data.grid(row=0, column=3, sticky="w")

        ttk.Label(form, text="Hora (hh:mm):").grid(row=0, column=4, sticky="e", padx=4)
        ent_hora = ttk.Entry(form, textvariable=self.var_hora, width=8)
        ent_hora.grid(row=0, column=5, sticky="w")

        # Máscaras: formatam sozinhas (dd/mm/aaaa e hh:mm) e aceitam digitar / e :
        aplicar_mascara(ent_data, self.var_data, mascara_data)
        aplicar_mascara(ent_hora, self.var_hora, mascara_hora)

        ttk.Label(form, text="Descrição:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        ttk.Entry(form, textvariable=self.var_descricao, width=48).grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="Status:").grid(row=1, column=2, sticky="e", padx=4)
        ttk.Combobox(form, textvariable=self.var_status, values=STATUS,
                     state="readonly", width=12).grid(row=1, column=3, sticky="w")

        botoes = ttk.Frame(form)
        botoes.grid(row=2, column=0, columnspan=6, pady=(8, 0))
        ttk.Button(botoes, text="Novo", command=self.novo).pack(side="left", padx=4)
        ttk.Button(botoes, text="Salvar", command=self.salvar).pack(side="left", padx=4)
        ttk.Button(botoes, text="Excluir", command=self.excluir).pack(side="left", padx=4)
        ttk.Button(botoes, text="Voltar", command=self.destroy).pack(side="left", padx=(24, 4))  # fecha a janela e volta ao menu

    # ---------------- carga de dados ----------------
    def _carregar_carros(self):
        """Preenche o combobox de carros ('id - modelo placa (Dono: nome)')."""
        try:
            carros = listar_carros_com_dono()
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return
        self.mapa_carros = {
            f"{p['id_carro']} - {p['carro_modelo']} {formatar_placa(p['placa'])} (Dono: {p['dono_nome']})": p["id_carro"]
            for p in carros}
        self.cmb_carro["values"] = list(self.mapa_carros.keys())

    def carregar(self, intervalo=None):
        """Recarrega a tabela (todos ou apenas o intervalo informado)."""
        try:
            lista = listar_procedimentos(intervalo)
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return

        self.tabela.delete(*self.tabela.get_children())
        for a in lista:
            self.tabela.insert("", "end", iid=str(a["id_procedimento"]), values=(
                a["id_procedimento"],
                a["data_hora"].strftime("%d/%m/%Y"),
                a["data_hora"].strftime("%H:%M"),
                a["status"], a["descricao"],
                a["carro_modelo"], a["marca"], formatar_placa(a["placa"]),
                a["ano"],
                a["dono_nome"], formatar_cpf(texto(a["dono_cpf"])),
                a["endereco"], formatar_celular(a["celular"])))
        self.lbl_total.config(text=f"{len(lista)} procedimento(s) exibido(s)")

    # ---------------- filtro Dia / Mês / Ano ----------------
    def trocar_modo(self):
        """Ao alternar Dia/Mês/Ano: ajusta a dica, sugere o período atual e filtra."""
        modo = self.var_modo.get()
        self.lbl_dica.config(text=f"({DICAS[modo]})")
        self.var_periodo.set(datetime.now().strftime(FORMATOS[modo]))
        self.filtrar()

    @requer_sessao
    def filtrar(self):
        """Aplica o filtro conforme o modo e o período digitado."""
        modo = self.var_modo.get()
        periodo = self.var_periodo.get().strip()
        if not periodo:                       # sem período = todos
            self.carregar()
            return
        try:
            intervalo = calcular_intervalo(modo, periodo)
        except ValueError:
            messagebox.showwarning(
                "Atenção", f"Período inválido para '{modo}'. "
                           f"Use o formato {DICAS[modo]}.", parent=self)
            return
        self.carregar(intervalo)

    @requer_sessao
    def mostrar_todos(self):
        """Remove o filtro e lista todos os procedimentos ordenados por dia."""
        self.var_periodo.set("")
        self.carregar()

    # ---------------- formulário ----------------
    def selecionar(self, _evento=None):
        """Preenche o formulário com o procedimento selecionado."""
        sel = self.tabela.selection()
        if not sel:
            return
        v = self.tabela.item(sel[0], "values")
        self.id_selecionado = int(v[0])
        self.var_data.set(v[1])
        self.var_hora.set(v[2])
        self.var_status.set(v[3])
        self.var_descricao.set(v[4])
        # localiza no combobox o carro cujo ID é o do procedimento
        id_carro = self._id_carro_da_linha(self.id_selecionado)
        for texto_cmb, pid in self.mapa_carros.items():
            if pid == id_carro:
                self.var_carro.set(texto_cmb)
                break

    def _id_carro_da_linha(self, id_procedimento):
        """Busca o id_carro do procedimento (a tabela não exibe esse ID)."""
        linhas = consultar("SELECT id_carro FROM procedimento "
                           "WHERE id_procedimento = %s", (id_procedimento,))
        return linhas[0]["id_carro"] if linhas else None

    def novo(self):
        self.id_selecionado = None
        for var in (self.var_carro, self.var_data, self.var_hora, self.var_descricao):
            var.set("")
        self.var_status.set("AGENDADO")
        self.tabela.selection_remove(self.tabela.selection())

    def _validar(self):
        """Valida o formulário. Retorna (data_hora, descricao, status, id_carro) ou None."""
        id_carro = self.mapa_carros.get(self.var_carro.get())
        if id_carro is None:
            messagebox.showwarning("Atenção", "Selecione o carro.", parent=self)
            return None

        descricao = self.var_descricao.get().strip()
        if not descricao:
            messagebox.showwarning("Atenção", "Informe o descricao.", parent=self)
            return None

        try:
            data_hora = datetime.strptime(
                f"{self.var_data.get().strip()} {self.var_hora.get().strip()}",
                "%d/%m/%Y %H:%M")
        except ValueError:
            messagebox.showwarning("Atenção", "Data/hora inválida. Use "
                                   "dd/mm/aaaa e hh:mm.", parent=self)
            return None

        status = self.var_status.get()

        # Novo procedimento não pode ser marcado no passado
        if (self.id_selecionado is None and status == "AGENDADO"
                and data_hora < datetime.now()):
            messagebox.showwarning("Atenção", "Não é possível agendar em "
                                   "data/hora passada.", parent=self)
            return None
        return data_hora, descricao, status, id_carro

    # ---------------- ações ----------------
    @requer_sessao
    def salvar(self):
        dados = self._validar()
        if not dados:
            return
        data_hora, descricao, status, id_carro = dados
        try:
            if self.id_selecionado is None:
                # grava também QUEM registrou (usuário logado)
                inserir_procedimento(data_hora, descricao, status, id_carro,
                                    sessao.usuario_id)
                messagebox.showinfo("Sucesso", "Procedimento cadastrado!", parent=self)
            else:
                atualizar_procedimento(self.id_selecionado, data_hora, descricao,
                                      status, id_carro)
                messagebox.showinfo("Sucesso", "Procedimento atualizado!", parent=self)
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return
        self.novo()
        self.filtrar()          # recarrega respeitando o filtro atual

    @requer_sessao
    def excluir(self):
        if self.id_selecionado is None:
            messagebox.showwarning("Atenção", "Selecione um procedimento.",
                                   parent=self)
            return
        if not messagebox.askyesno("Confirmar", "Excluir o procedimento selecionado?",
                                   parent=self):
            return
        try:
            excluir_procedimento(self.id_selecionado)
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return
        self.novo()
        self.filtrar()
