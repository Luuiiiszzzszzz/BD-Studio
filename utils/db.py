import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bdstudio.db")

class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._criar_tabelas()

    def _criar_tabelas(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                canal_id INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                assunto TEXT NOT NULL,
                staff_id INTEGER,
                status TEXT DEFAULT 'aberto',
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                fechado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS pagamentos (
                pagamento_id TEXT PRIMARY KEY,
                criador_id INTEGER NOT NULL,
                cliente_id INTEGER,
                item TEXT NOT NULL,
                valor REAL NOT NULL,
                status TEXT DEFAULT 'pendente',
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                confirmado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pagamento_id TEXT NOT NULL,
                cliente_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                valor REAL NOT NULL,
                data TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs_comandos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                comando TEXT NOT NULL,
                referencia TEXT,
                extra TEXT,
                data TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        self.conn.commit()

    # ── Tickets ──
    def criar_ticket(self, ticket_id, user_id, canal_id, categoria, assunto):
        self.conn.execute(
            "INSERT INTO tickets (ticket_id, user_id, canal_id, categoria, assunto) VALUES (?,?,?,?,?)",
            (ticket_id, user_id, canal_id, categoria, assunto),
        )
        self.conn.commit()

    def buscar_ticket(self, ticket_id):
        row = self.conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        return dict(row) if row else None

    def buscar_ticket_por_canal(self, canal_id):
        row = self.conn.execute(
            "SELECT * FROM tickets WHERE canal_id=? AND status='aberto'", (canal_id,)
        ).fetchone()
        return dict(row) if row else None

    def buscar_ticket_aberto_por_usuario(self, user_id):
        row = self.conn.execute(
            "SELECT * FROM tickets WHERE user_id=? AND status='aberto'", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def assumir_ticket(self, ticket_id, staff_id):
        self.conn.execute(
            "UPDATE tickets SET staff_id=? WHERE ticket_id=?", (staff_id, ticket_id)
        )
        self.conn.commit()

    def fechar_ticket(self, ticket_id):
        self.conn.execute(
            "UPDATE tickets SET status='fechado', fechado_em=datetime('now','localtime') WHERE ticket_id=?",
            (ticket_id,),
        )
        self.conn.commit()

    # ── Pagamentos ──
    def criar_pagamento_pendente(self, pagamento_id, criador_id, cliente_id, item, valor):
        self.conn.execute(
            "INSERT OR IGNORE INTO pagamentos (pagamento_id, criador_id, cliente_id, item, valor) VALUES (?,?,?,?,?)",
            (pagamento_id, criador_id, cliente_id, item, valor),
        )
        self.conn.commit()

    def confirmar_pagamento(self, pagamento_id, cliente_id, item, valor):
        data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.conn.execute(
            "UPDATE pagamentos SET status='aprovado', confirmado_em=datetime('now','localtime') WHERE pagamento_id=?",
            (pagamento_id,),
        )
        if cliente_id:
            self.conn.execute(
                "INSERT INTO compras (pagamento_id, cliente_id, item, valor, data) VALUES (?,?,?,?,?)",
                (pagamento_id, cliente_id, item, valor, data),
            )
        self.conn.commit()

    def listar_compras(self, cliente_id):
        rows = self.conn.execute(
            "SELECT * FROM compras WHERE cliente_id=? ORDER BY id DESC", (cliente_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Logs ──
    def salvar_log_comando(self, user_id, username, comando, referencia=None, extra=None):
        self.conn.execute(
            "INSERT INTO logs_comandos (user_id, username, comando, referencia, extra) VALUES (?,?,?,?,?)",
            (user_id, username, comando, referencia, extra),
        )
        self.conn.commit()
