"""
dono.py
--------
Gerenciamento de DONO (Entrega 06): cadastrar, atualizar, excluir e
CONSULTAR com busca.

Regras atendidas:
  * Busca: o usuário digita um termo e confirma (botão Buscar ou Enter);
    a listagem (tabela) é ATUALIZADA mostrando só os registros que
    correspondem ao termo (nome, endereço, celular ou CPF).
  * CPF é gravado CRIPTOGRAFADO (AES_ENCRYPT) e só é descriptografado
    (AES_DECRYPT) na hora de exibir.
  * Validações: campos obrigatórios, CPF válido, celular válido, CPF único.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from mysql.connector.errors import Error

from config import CHAVE_CRIPTOGRAFIA
from database import consultar, executar, mensagem_erro
from seguranca import (somente_digitos, validar_cpf, validar_celular,
                       formatar_cpf, formatar_celular, texto,
                       mascara_cpf, mascara_celular, aplicar_mascara)
from sessao import requer_sessao


# =====================================================================
# CAMADA DE DADOS
# =====================================================================
def listar_donos(termo=""):
    """
    Lista donos. Se `termo` for informado, filtra por:
      nome OU endereço OU (celular / CPF, comparando só os dígitos).
    O CPF é descriptografado no próprio SELECT.
    """
    termo = (termo or "").strip()
    sql = ("SELECT id_dono, nome, "
           "CAST(AES_DECRYPT(cpf, %s) AS CHAR) AS cpf, endereco, celular "
           "FROM dono")
    params = [CHAVE_CRIPTOGRAFIA]

    if termo:
        condicoes = ["nome LIKE %s", "endereco LIKE %s"]
        params += [f"%{termo}%", f"%{termo}%"]

        # Se o termo tiver números, também procura em celular e CPF
        digitos = somente_digitos(termo)
        if digitos:
            condicoes.append("celular LIKE %s")
            condicoes.append("CAST(AES_DECRYPT(cpf, %s) AS CHAR) LIKE %s")
            params += [f"%{digitos}%", CHAVE_CRIPTOGRAFIA, f"%{digitos}%"]

        sql += " WHERE " + " OR ".join(condicoes)

    sql += " ORDER BY nome"
    return consultar(sql, params)


def inserir_dono(nome, cpf, endereco, celular):
    """Insere um dono gravando o CPF criptografado."""
    return executar(
        "INSERT INTO dono (nome, cpf, endereco, celular) "
        "VALUES (%s, AES_ENCRYPT(%s, %s), %s, %s)",
        (nome, cpf, CHAVE_CRIPTOGRAFIA, endereco, celular),
    )


def atualizar_dono(id_dono, nome, cpf, endereco, celular):
    """Atualiza os dados de um dono (CPF regravado criptografado)."""
    executar(
        "UPDATE dono SET nome = %s, cpf = AES_ENCRYPT(%s, %s), "
        "endereco = %s, celular = %s WHERE id_dono = %s",
        (nome, cpf, CHAVE_CRIPTOGRAFIA, endereco, celular, id_dono),
    )


def excluir_dono(id_dono):
    """Exclui um dono pelo ID (falha se ele tiver carros vinculados)."""
    executar("DELETE FROM dono WHERE id_dono = %s", (id_dono,))


# =====================================================================
# INTERFACE (mínima)
# =====================================================================
class JanelaDono(tk.Toplevel):
    """Janela de gerenciamento de donos."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Donos")
        self.geometry("950x560")
        self.id_selecionado = None   # None = novo cadastro; número = edição
        # Termo da busca em uso. salvar() e excluir() usam este valor para
        # recarregar a listagem; o item 5.2 deve atualizá-lo em buscar().
        self.termo_atual = ""
        self._montar()
        self.carregar()

    # ---------------- montagem da tela ----------------
    def _montar(self):
        # --- Barra de busca ---
        topo = ttk.Frame(self, padding=8)
        topo.pack(fill="x")
        ttk.Label(topo, text="Buscar:").pack(side="left")
        self.var_busca = tk.StringVar()
        ent = ttk.Entry(topo, textvariable=self.var_busca, width=40)
        ent.pack(side="left", padx=5)
        ent.bind("<Return>", lambda e: self.buscar())   # Enter confirma
        ttk.Button(topo, text="Buscar", command=self.buscar).pack(side="left")
        ttk.Button(topo, text="Limpar busca",
                   command=self.limpar_busca).pack(side="left", padx=5)

        # --- Tabela de donos ---
        meio = ttk.Frame(self, padding=(8, 0))
        meio.pack(fill="both", expand=True)
        colunas = ("id", "nome", "cpf", "endereco", "celular")
        self.tabela = ttk.Treeview(meio, columns=colunas, show="headings",
                                   height=10)
        titulos = {"id": ("ID", 50), "nome": ("Nome", 200),
                   "cpf": ("CPF", 120), "endereco": ("Endereço", 350),
                   "celular": ("Celular", 120)}
        for col, (titulo, largura) in titulos.items():
            self.tabela.heading(col, text=titulo, anchor="w")  # cabeçalho à esquerda
            self.tabela.column(col, width=largura)
        barra = ttk.Scrollbar(meio, orient="vertical",
                              command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        # Ao clicar numa linha, carrega os dados no formulário
        self.tabela.bind("<<TreeviewSelect>>", self.selecionar)

        # --- Formulário ---
        form = ttk.LabelFrame(self, text="Dados do dono", padding=8)
        form.pack(fill="x", padx=8, pady=8)
        self.vars = {}
        self.entradas = {}
        rotulos = [("nome", "Nome:"), ("cpf", "CPF:"),
                   ("endereco", "Endereço:"), ("celular", "Celular:")]
        for i, (chave, rotulo) in enumerate(rotulos):
            ttk.Label(form, text=rotulo).grid(row=i, column=0, sticky="e",
                                              padx=4, pady=2)
            self.vars[chave] = tk.StringVar()
            self.entradas[chave] = ttk.Entry(form, textvariable=self.vars[chave],
                                             width=60)
            self.entradas[chave].grid(row=i, column=1, sticky="w", pady=2)

        # Máscaras automáticas: aceitam só números (até 11) e formatam
        # enquanto o usuário digita. CPF: 333.444.555-66 | Celular: (11) 99999-8888
        aplicar_mascara(self.entradas["cpf"], self.vars["cpf"], mascara_cpf)
        aplicar_mascara(self.entradas["celular"], self.vars["celular"],
                        mascara_celular)

        botoes = ttk.Frame(form)
        botoes.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(botoes, text="Novo", command=self.novo).pack(side="left", padx=4)
        ttk.Button(botoes, text="Salvar", command=self.salvar).pack(side="left", padx=4)
        ttk.Button(botoes, text="Excluir", command=self.excluir).pack(side="left", padx=4)
        ttk.Button(botoes, text="Voltar", command=self.destroy).pack(side="left", padx=(24, 4))  # fecha a janela e volta ao menu

    # ---------------- listagem / busca ----------------
    def carregar(self, termo=""):
        """Recarrega a tabela (todos os donos ou só os do termo)."""
        try:
            donos = listar_donos(termo)
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return

        self.tabela.delete(*self.tabela.get_children())
        for t in donos:
            self.tabela.insert("", "end", iid=str(t["id_dono"]), values=(
                t["id_dono"], t["nome"], formatar_cpf(texto(t["cpf"])),
                t["endereco"], formatar_celular(t["celular"])))

    @requer_sessao
    def buscar(self):
        """Confirma a busca: atualiza a listagem com os registros que batem."""
        termo = self.var_busca.get().strip()
        self.carregar(termo)
        if termo and not self.tabela.get_children():
            messagebox.showinfo("Busca", "Nenhum dono encontrado para o termo "
                                f"'{termo}'.", parent=self)

    @requer_sessao
    def limpar_busca(self):
        self.var_busca.set("")
        self.carregar()

    # ---------------- formulário ----------------
    def selecionar(self, _evento=None):
        """Preenche o formulário com a linha selecionada na tabela."""
        sel = self.tabela.selection()
        if not sel:
            return
        valores = self.tabela.item(sel[0], "values")
        self.id_selecionado = int(valores[0])
        self.vars["nome"].set(valores[1])
        self.vars["cpf"].set(valores[2])
        self.vars["endereco"].set(valores[3])
        self.vars["celular"].set(valores[4])

    def novo(self):
        """Limpa o formulário para um novo cadastro."""
        self.id_selecionado = None
        for v in self.vars.values():
            v.set("")
        self.tabela.selection_remove(self.tabela.selection())

    def _validar(self):
        """Valida o formulário. Retorna (nome, cpf, endereco, celular) ou None."""
        nome = self.vars["nome"].get().strip()
        cpf = somente_digitos(self.vars["cpf"].get())
        endereco = self.vars["endereco"].get().strip()
        celular = somente_digitos(self.vars["celular"].get())

        if not nome or not endereco:
            messagebox.showwarning("Atenção", "Nome e endereço são obrigatórios.",
                                   parent=self)
            return None
        if not validar_cpf(cpf):
            messagebox.showwarning("Atenção",
                                   "CPF incompleto: informe os 11 dígitos.",
                                   parent=self)
            return None
        if not validar_celular(celular):
            messagebox.showwarning("Atenção",
                                   "Celular inválido (informe DDD + número).",
                                   parent=self)
            return None
        return nome, cpf, endereco, celular

    # ---------------- ações ----------------
    @requer_sessao
    def salvar(self):
        """Cadastra (se for novo) ou atualiza (se houver dono selecionado)."""
        dados = self._validar()
        if not dados:
            return
        try:
            if self.id_selecionado is None:
                inserir_dono(*dados)
                messagebox.showinfo("Sucesso", "Dono cadastrado!", parent=self)
            else:
                atualizar_dono(self.id_selecionado, *dados)
                messagebox.showinfo("Sucesso", "Dono atualizado!", parent=self)
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return
        self.novo()
        self.carregar(self.var_busca.get().strip())

    @requer_sessao
    def excluir(self):
        """Exclui o dono selecionado (com confirmação)."""
        if self.id_selecionado is None:
            messagebox.showwarning("Atenção", "Selecione um dono na tabela.",
                                   parent=self)
            return
        if not messagebox.askyesno("Confirmar", "Excluir o dono selecionado?",
                                   parent=self):
            return
        try:
            excluir_dono(self.id_selecionado)
        except Error as e:
            messagebox.showerror("Erro", mensagem_erro(e), parent=self)
            return
        self.novo()
        self.carregar(self.var_busca.get().strip())
