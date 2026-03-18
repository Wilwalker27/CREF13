import sqlite3
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import closing


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("ESTOQUE_DB_PATH", str(BASE_DIR / "estoque.db"))).resolve()


def get_conn():
	DB_PATH.parent.mkdir(parents=True, exist_ok=True)
	conn = sqlite3.connect(str(DB_PATH), timeout=30)
	conn.row_factory = sqlite3.Row
	return conn

def dtc_now():
	return datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()


def init_db():
	with closing(get_conn()) as conn:
		with conn:
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS equipamentos (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					equipamento TEXT NOT NULL,
					tombo TEXT,
					setor TEXT,
					localizacao TEXT,
					status TEXT DEFAULT 'Ativo',
					ativo INTEGER DEFAULT 1,
					data_criacao TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
				)
				"""
			)
			conn.execute(
				"CREATE UNIQUE INDEX IF NOT EXISTS idx_tombo ON equipamentos (tombo)"
			)
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS movimentacoes (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					equipamento_id INTEGER NOT NULL,
					tipo TEXT NOT NULL,
					quantidade INTEGER DEFAULT 1,
					setor_origem TEXT,
					setor_destino TEXT,
					observacao TEXT,
					data_movimentacao TEXT DEFAULT (datetime('now')),
					FOREIGN KEY (equipamento_id) REFERENCES equipamentos (id)
				)
				"""
			)
			columns_info = list(conn.execute("PRAGMA table_info(equipamentos)"))
			columns = [row["name"] for row in columns_info]
			if "localizacao" not in columns:
				conn.execute("ALTER TABLE equipamentos ADD COLUMN localizacao TEXT")
			if "status" not in columns:
				conn.execute("ALTER TABLE equipamentos ADD COLUMN status TEXT DEFAULT 'Ativo'")
			tombo_info = next((row for row in columns_info if row["name"] == "tombo"), None)
			if tombo_info and tombo_info["notnull"] == 1:
				conn.execute("ALTER TABLE equipamentos RENAME TO equipamentos_old")
				conn.execute(
					"""
					CREATE TABLE equipamentos (
						id INTEGER PRIMARY KEY AUTOINCREMENT,
						equipamento TEXT NOT NULL,
						tombo TEXT,
						setor TEXT,
						localizacao TEXT,
						status TEXT DEFAULT 'Ativo',
						ativo INTEGER DEFAULT 1,
						data_criacao TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
					)
					"""
				)
				conn.execute(
					"""
					INSERT INTO equipamentos (id, equipamento, tombo, setor, localizacao, status, ativo, data_criacao)
					SELECT id, equipamento, NULLIF(tombo, ''), setor, localizacao, status, ativo, data_criacao
					FROM equipamentos_old
					"""
				)
				conn.execute("DROP TABLE equipamentos_old")
				conn.execute(
					"CREATE UNIQUE INDEX IF NOT EXISTS idx_tombo ON equipamentos (tombo)"
				)
			conn.execute("UPDATE equipamentos SET status = 'Ativo' WHERE status IS NULL OR status = ''")

			columns_mov = [row["name"] for row in conn.execute("PRAGMA table_info(movimentacoes)")]
			if "localizacao_origem" not in columns_mov:
				conn.execute("ALTER TABLE movimentacoes ADD COLUMN localizacao_origem TEXT")
			if "localizacao_destino" not in columns_mov:
				conn.execute("ALTER TABLE movimentacoes ADD COLUMN localizacao_destino TEXT")


def fetch_all(query, params=None):
	with closing(get_conn()) as conn:
		cur = conn.execute(query, params or [])
		rows = cur.fetchall()
		return [dict(row) for row in rows]


def execute(query, params=None):
	with closing(get_conn()) as conn:
		with conn:
			conn.execute(query, params or [])


def get_equipamentos(ativo_apenas=True, setor=None, busca=None, status=None):
	where_clauses = []
	params = []
	if ativo_apenas:
		where_clauses.append("ativo = 1")
	if setor and setor != "Todos":
		where_clauses.append("COALESCE(setor, '') = ?")
		params.append("" if setor == "Sem setor" else setor)
	if status and status != "Todos":
		where_clauses.append("COALESCE(status, 'Ativo') = ?")
		params.append(status)
	if busca:
		where_clauses.append("(equipamento LIKE ? OR COALESCE(tombo, '') LIKE ?)")
		params.extend([f"%{busca}%", f"%{busca}%"])
	where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
	return fetch_all(
		f"""
		SELECT id, equipamento, tombo, setor, localizacao, status, ativo, data_criacao
		FROM equipamentos
		{where}
		ORDER BY equipamento
		""",
		params,
	)


def contar_por_setor():
	return fetch_all(
		"""
		SELECT COALESCE(setor, 'Sem setor') AS setor, COUNT(*) AS total
		FROM equipamentos
		GROUP BY COALESCE(setor, 'Sem setor')
		ORDER BY setor
		"""
	)


def contar_por_status():
	return fetch_all(
		"""
		SELECT COALESCE(status, 'Ativo') AS status, COUNT(*) AS total
		FROM equipamentos
		WHERE ativo = 1
		GROUP BY COALESCE(status, 'Ativo')
		ORDER BY status
		"""
	)


def registrar_movimentacao(equipamento_id, tipo, setor_origem=None, setor_destino=None, localizacao_origem=None, localizacao_destino=None, observacao=None, quantidade=1):
	execute(
		"""
		INSERT INTO movimentacoes (equipamento_id, tipo, quantidade, setor_origem, setor_destino, localizacao_origem, localizacao_destino, observacao)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		""",
		[equipamento_id, tipo, quantidade, setor_origem, setor_destino, localizacao_origem, localizacao_destino, observacao],
	)


def obter_movimentacoes(limite=200):
	return fetch_all(
		"""
		SELECT m.id, e.equipamento, e.tombo, m.tipo, m.quantidade, m.setor_origem, m.setor_destino, m.localizacao_origem, m.localizacao_destino, m.observacao, m.data_movimentacao
		FROM movimentacoes m
		JOIN equipamentos e ON e.id = m.equipamento_id
		ORDER BY m.data_movimentacao DESC
		LIMIT ?
		""",
		[limite],
	)
