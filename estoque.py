import sqlite3
from contextlib import closing

import streamlit as st


DB_PATH = "estoque.db"


def get_conn():
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn


def init_db():
	with closing(get_conn()) as conn:
		with conn:
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS products (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL,
					sku TEXT,
					unit TEXT,
					min_stock REAL DEFAULT 0,
					active INTEGER DEFAULT 1,
					created_at TEXT DEFAULT (datetime('now'))
				)
				"""
			)
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS stock_moves (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					product_id INTEGER NOT NULL,
					qty REAL NOT NULL,
					note TEXT,
					created_at TEXT DEFAULT (datetime('now')),
					FOREIGN KEY (product_id) REFERENCES products (id)
				)
				"""
			)


def fetch_all(query, params=None):
	with closing(get_conn()) as conn:
		cur = conn.execute(query, params or [])
		rows = cur.fetchall()
		return [dict(row) for row in rows]


def execute(query, params=None):
	with closing(get_conn()) as conn:
		with conn:
			conn.execute(query, params or [])


def get_products(active_only=True):
	where = "WHERE p.active = 1" if active_only else ""
	return fetch_all(
		f"""
		SELECT
			p.id,
			p.name,
			p.sku,
			p.unit,
			p.min_stock,
			p.active,
			COALESCE(SUM(m.qty), 0) AS stock
		FROM products p
		LEFT JOIN stock_moves m ON m.product_id = p.id
		{where}
		GROUP BY p.id
		ORDER BY p.name
		"""
	)


def get_stock(product_id):
	result = fetch_all(
		"""
		SELECT COALESCE(SUM(qty), 0) AS stock
		FROM stock_moves
		WHERE product_id = ?
		""",
		[product_id],
	)
	return result[0]["stock"] if result else 0


def insert_move(product_id, qty, note=None):
	execute(
		"""
		INSERT INTO stock_moves (product_id, qty, note)
		VALUES (?, ?, ?)
		""",
		[product_id, qty, note],
	)


def main():
	st.set_page_config(page_title="Estoque", layout="wide")
	st.title("Estoque enxuto")
	init_db()

	tabs = st.tabs(["Produtos", "Movimentações", "Inventário", "Relatórios"])

	with tabs[0]:
		st.subheader("Cadastrar produto")
		with st.form("add_product", clear_on_submit=True):
			col1, col2, col3, col4 = st.columns(4)
			with col1:
				name = st.text_input("Nome")
			with col2:
				sku = st.text_input("SKU")
			with col3:
				unit = st.text_input("Unidade")
			with col4:
				min_stock = st.number_input("Estoque mínimo", min_value=0.0, step=1.0)
			submitted = st.form_submit_button("Adicionar")
			if submitted and name.strip():
				execute(
					"""
					INSERT INTO products (name, sku, unit, min_stock)
					VALUES (?, ?, ?, ?)
					""",
					[name.strip(), sku.strip(), unit.strip(), min_stock],
				)
				st.success("Produto cadastrado.")

		st.subheader("Produtos ativos")
		products = get_products(active_only=True)
		st.dataframe(products, use_container_width=True)

		st.subheader("Atualizar ou desativar")
		if products:
			product_map = {f"{p['name']} ({p['sku']})".strip(): p for p in products}
			choice = st.selectbox("Produto", list(product_map.keys()))
			selected = product_map[choice]
			col1, col2 = st.columns(2)
			with col1:
				new_min = st.number_input(
					"Novo estoque mínimo",
					min_value=0.0,
					step=1.0,
					value=float(selected["min_stock"] or 0),
				)
			with col2:
				new_unit = st.text_input("Unidade", value=selected.get("unit") or "")
			col3, col4 = st.columns(2)
			with col3:
				if st.button("Atualizar"):
					execute(
						"""
						UPDATE products
						SET min_stock = ?, unit = ?
						WHERE id = ?
						""",
						[new_min, new_unit.strip(), selected["id"]],
					)
					st.success("Produto atualizado.")
			with col4:
				if st.button("Desativar"):
					execute(
						"UPDATE products SET active = 0 WHERE id = ?",
						[selected["id"]],
					)
					st.warning("Produto desativado.")
		else:
			st.info("Cadastre um produto para começar.")

	with tabs[1]:
		st.subheader("Movimentação rápida")
		products = get_products(active_only=True)
		if not products:
			st.info("Cadastre um produto primeiro.")
		else:
			product_map = {f"{p['name']} ({p['sku']})".strip(): p for p in products}
			with st.form("move_stock", clear_on_submit=True):
				col1, col2, col3, col4 = st.columns(4)
				with col1:
					choice = st.selectbox("Produto", list(product_map.keys()))
				with col2:
					move_type = st.selectbox("Tipo", ["Entrada", "Saída", "Ajuste"])
				with col3:
					qty = st.number_input("Quantidade", min_value=0.0, step=1.0)
				with col4:
					note = st.text_input("Observação")
				submitted = st.form_submit_button("Lançar")
				if submitted and qty > 0:
					selected = product_map[choice]
					signed_qty = qty
					if move_type == "Saída":
						signed_qty = -qty
					insert_move(selected["id"], signed_qty, note.strip())
					st.success("Movimentação registrada.")

		st.subheader("Últimas movimentações")
		moves = fetch_all(
			"""
			SELECT m.id, p.name, p.sku, m.qty, m.note, m.created_at
			FROM stock_moves m
			JOIN products p ON p.id = m.product_id
			ORDER BY m.created_at DESC
			LIMIT 50
			"""
		)
		st.dataframe(moves, use_container_width=True)

	with tabs[2]:
		st.subheader("Inventário (contagem)")
		products = get_products(active_only=True)
		if not products:
			st.info("Cadastre um produto primeiro.")
		else:
			product_map = {f"{p['name']} ({p['sku']})".strip(): p for p in products}
			with st.form("inventory_count", clear_on_submit=True):
				col1, col2, col3 = st.columns(3)
				with col1:
					choice = st.selectbox("Produto", list(product_map.keys()))
				with col2:
					counted = st.number_input("Quantidade contada", min_value=0.0, step=1.0)
				with col3:
					note = st.text_input("Observação")
				submitted = st.form_submit_button("Aplicar ajuste")
				if submitted:
					selected = product_map[choice]
					current = get_stock(selected["id"])
					diff = counted - current
					if diff != 0:
						insert_move(selected["id"], diff, note.strip() or "Ajuste inventário")
						st.success("Ajuste aplicado.")
					else:
						st.info("Sem diferença para ajustar.")

	with tabs[3]:
		st.subheader("Estoque atual")
		products = get_products(active_only=True)
		st.dataframe(products, use_container_width=True)

		st.subheader("Abaixo do mínimo")
		low_stock = [p for p in products if float(p.get("stock") or 0) <= float(p.get("min_stock") or 0)]
		if low_stock:
			st.dataframe(low_stock, use_container_width=True)
		else:
			st.info("Nenhum item abaixo do mínimo.")


if __name__ == "__main__":
	main()
