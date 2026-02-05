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
				CREATE TABLE IF NOT EXISTS equipments (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL,
					tombo TEXT NOT NULL,
					unit TEXT,
					sector TEXT,
					status TEXT DEFAULT 'Ativo',
					active INTEGER DEFAULT 1,
					created_at TEXT DEFAULT (datetime('now'))
				)
				"""
			)
			conn.execute(
				"CREATE UNIQUE INDEX IF NOT EXISTS idx_equip_tombo ON equipments (tombo)"
			)
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS movements (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					equipment_id INTEGER NOT NULL,
					action TEXT NOT NULL,
					qty INTEGER DEFAULT 1,
					from_sector TEXT,
					to_sector TEXT,
					note TEXT,
					created_at TEXT DEFAULT (datetime('now')),
					FOREIGN KEY (equipment_id) REFERENCES equipments (id)
				)
				"""
			)
			columns = [row["name"] for row in conn.execute("PRAGMA table_info(equipments)")]
			if "sector" not in columns:
				conn.execute("ALTER TABLE equipments ADD COLUMN sector TEXT")
			if "status" not in columns:
				conn.execute("ALTER TABLE equipments ADD COLUMN status TEXT DEFAULT 'Ativo'")
			conn.execute("UPDATE equipments SET status = 'Ativo' WHERE status IS NULL OR status = ''")


def fetch_all(query, params=None):
	with closing(get_conn()) as conn:
		cur = conn.execute(query, params or [])
		rows = cur.fetchall()
		return [dict(row) for row in rows]


def execute(query, params=None):
	with closing(get_conn()) as conn:
		with conn:
			conn.execute(query, params or [])


def get_equipments(active_only=True, sector=None, search=None, status=None):
	where_clauses = []
	params = []
	if active_only:
		where_clauses.append("active = 1")
	if sector and sector != "Todos":
		where_clauses.append("COALESCE(sector, '') = ?")
		params.append("" if sector == "Sem setor" else sector)
	if status and status != "Todos":
		where_clauses.append("COALESCE(status, 'Ativo') = ?")
		params.append(status)
	if search:
		where_clauses.append("(name LIKE ? OR tombo LIKE ?)")
		params.extend([f"%{search}%", f"%{search}%"])
	where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
	return fetch_all(
		f"""
		SELECT id, name, tombo, unit, sector, status, active, created_at
		FROM equipments
		{where}
		ORDER BY name
		""",
		params,
	)


def count_by_sector():
	return fetch_all(
		"""
		SELECT COALESCE(sector, 'Sem setor') AS sector, COUNT(*) AS total
		FROM equipments
		WHERE active = 1
		GROUP BY COALESCE(sector, 'Sem setor')
		ORDER BY sector
		"""
	)


def count_by_status():
	return fetch_all(
		"""
		SELECT COALESCE(status, 'Ativo') AS status, COUNT(*) AS total
		FROM equipments
		WHERE active = 1
		GROUP BY COALESCE(status, 'Ativo')
		ORDER BY status
		"""
	)


def insert_movement(equipment_id, action, from_sector=None, to_sector=None, note=None, qty=1):
	execute(
		"""
		INSERT INTO movements (equipment_id, action, qty, from_sector, to_sector, note)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		[equipment_id, action, qty, from_sector, to_sector, note],
	)


def get_movements(limit=200):
	return fetch_all(
		"""
		SELECT m.id, e.name, e.tombo, m.action, m.qty, m.from_sector, m.to_sector, m.note, m.created_at
		FROM movements m
		JOIN equipments e ON e.id = m.equipment_id
		ORDER BY m.created_at DESC
		LIMIT ?
		""",
		[limit],
	)


def to_csv(rows):
	if not rows:
		return ""
	import csv
	from io import StringIO

	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
	writer.writeheader()
	writer.writerows(rows)
	return output.getvalue()


def main():
	st.set_page_config(page_title="Inventário TI", layout="wide")
	st.title("Controle de Inventário da TI")
	init_db()

	tabs = st.tabs(["Equipamentos", "Movimentações", "Relatórios"])

	with tabs[0]:
		st.subheader("Cadastrar equipamento")
		with st.form("add_equipment", clear_on_submit=True):
			col1, col2, col3, col4 = st.columns(4)
			with col1:
				name = st.text_input("Equipamento")
			with col2:
				tombo = st.text_input("Tombo")
			with col3:
				unit = st.text_input("Unidade")
			with col4:
				sector = st.text_input("Setor")
			submitted = st.form_submit_button("Adicionar")
			if submitted:
				if not name.strip() or not tombo.strip():
					st.error("Informe equipamento e tombo.")
				else:
					try:
						execute(
							"""
							INSERT INTO equipments (name, tombo, unit, sector)
							VALUES (?, ?, ?, ?)
							""",
							[name.strip(), tombo.strip(), unit.strip(), sector.strip()],
						)
						st.success("Equipamento cadastrado.")
					except sqlite3.IntegrityError:
						st.error("Tombo já existe.")

		st.subheader("Lista de equipamentos")
		colf1, colf2, colf3, colf4 = st.columns(4)
		with colf1:
			search = st.text_input("Buscar por nome ou tombo")
		with colf2:
			sectors = sorted({e.get("sector") or "Sem setor" for e in get_equipments(active_only=False)})
			sector_filter = st.selectbox("Setor", ["Todos"] + sectors)
		with colf3:
			statuses = sorted({e.get("status") or "Ativo" for e in get_equipments(active_only=False)})
			status_filter = st.selectbox("Status", ["Todos"] + statuses)
		with colf4:
			include_inactive = st.checkbox("Incluir inativos", value=False)
		active_only = not include_inactive
		equipments = get_equipments(
			active_only=active_only,
			sector=sector_filter,
			search=search.strip(),
			status=status_filter,
		)
		st.dataframe(equipments, use_container_width=True)

		st.subheader("Atualizar ou desativar")
		if equipments:
			equip_map = {f"{e['name']} ({e['tombo']})": e for e in equipments}
			choice = st.selectbox("Equipamento", list(equip_map.keys()))
			selected = equip_map[choice]
			statuses = ["Ativo", "Em manutenção", "Quebrado", "Baixado", "Devolvido"]
			current_status = selected.get("status") or "Ativo"
			if current_status not in statuses:
				statuses = [current_status] + statuses
			col1, col2, col3, col4 = st.columns(4)
			with col1:
				new_name = st.text_input("Equipamento", value=selected.get("name") or "")
			with col2:
				new_unit = st.text_input("Unidade", value=selected.get("unit") or "")
			with col3:
				new_sector = st.text_input("Setor", value=selected.get("sector") or "")
			with col4:
				new_status = st.selectbox("Status", statuses, index=statuses.index(current_status))
			col5, col6 = st.columns(2)
			with col5:
				if st.button("Atualizar"):
					new_active = 0 if new_status in ("Baixado", "Devolvido") else 1
					execute(
						"""
						UPDATE equipments
						SET name = ?, unit = ?, sector = ?, status = ?, active = ?
						WHERE id = ?
						""",
						[
							new_name.strip(),
							new_unit.strip(),
							new_sector.strip(),
							new_status,
							new_active,
							selected["id"],
						],
					)
					st.success("Equipamento atualizado.")
			with col6:
				if st.button("Desativar"):
					execute("UPDATE equipments SET active = 0 WHERE id = ?", [selected["id"]])
					st.warning("Equipamento desativado.")
		else:
			st.info("Cadastre um equipamento para começar.")

	with tabs[1]:
		st.subheader("Registrar movimentação")
		equipments_all = get_equipments(active_only=False)
		if not equipments_all:
			st.info("Cadastre um equipamento para começar.")
		else:
			equip_map = {f"{e['name']} ({e['tombo']})": e for e in equipments_all}
			with st.form("movement_form", clear_on_submit=True):
				col1, col2, col3, col4 = st.columns(4)
				with col1:
					choice = st.selectbox("Equipamento", list(equip_map.keys()))
				with col2:
					action = st.selectbox(
						"Tipo",
						["Entrada", "Transferência", "Quebra", "Manutenção", "Baixa", "Devolução", "Retorno"],
					)
				with col3:
					qty = st.number_input("Quantidade", min_value=1, step=1, value=1)
				with col4:
					note = st.text_input("Observação")
				new_sector = ""
				if action == "Transferência":
					new_sector = st.text_input("Novo setor")
				submitted = st.form_submit_button("Registrar")
				if submitted:
					selected = equip_map[choice]
					from_sector = selected.get("sector")
					to_sector = from_sector
					new_status = selected.get("status") or "Ativo"
					new_active = selected.get("active")
					if action == "Transferência" and not new_sector.strip():
						st.error("Informe o novo setor para transferência.")
						st.stop()
					if action == "Transferência":
						to_sector = new_sector.strip()
					if action == "Quebra":
						new_status = "Quebrado"
					if action == "Manutenção":
						new_status = "Em manutenção"
					if action == "Baixa":
						new_status = "Baixado"
						new_active = 0
					if action == "Devolução":
						new_status = "Devolvido"
						new_active = 0
					if action in ("Entrada", "Retorno"):
						new_status = "Ativo"
						new_active = 1
					execute(
						"""
						UPDATE equipments
						SET sector = ?, status = ?, active = ?
						WHERE id = ?
						""",
						[to_sector, new_status, new_active, selected["id"]],
					)
					insert_movement(
						selected["id"],
						action,
						from_sector=from_sector,
						to_sector=to_sector,
						note=note.strip(),
						qty=qty,
					)
					st.success("Movimentação registrada.")

		st.subheader("Últimas movimentações")
		movements = get_movements(limit=200)
		st.dataframe(movements, use_container_width=True)

	with tabs[2]:
		st.subheader("Resumo por setor")
		sector_counts = count_by_sector()
		total = sum(s["total"] for s in sector_counts) if sector_counts else 0
		st.metric("Total de equipamentos", total)
		st.dataframe(sector_counts, use_container_width=True)

		st.subheader("Resumo por status")
		status_counts = count_by_status()
		st.dataframe(status_counts, use_container_width=True)

		st.subheader("Tombos por setor")
		sector_list = [s["sector"] for s in sector_counts] or ["Sem setor"]
		selected_sector = st.selectbox("Setor", sector_list)
		equipments = get_equipments(active_only=True, sector=selected_sector)
		st.dataframe(equipments, use_container_width=True)

		st.subheader("Exportar relatórios")
		report_equipments = [
			{
				"Equipamento": e["name"],
				"Tombo": e["tombo"],
				"Setor": e.get("sector") or "",
				"Unidade": e.get("unit") or "",
				"Status": e.get("status") or "Ativo",
				"Ativo": "Sim" if e.get("active") else "Não",
				"Data cadastro": e.get("created_at") or "",
			}
			for e in get_equipments(active_only=False)
		]
		report_movements = [
			{
				"Equipamento": m["name"],
				"Tombo": m["tombo"],
				"Movimentação": m["action"],
				"Quantidade": m["qty"],
				"Setor origem": m.get("from_sector") or "",
				"Setor destino": m.get("to_sector") or "",
				"Observação": m.get("note") or "",
				"Data": m.get("created_at") or "",
			}
			for m in get_movements(limit=1000)
		]
		colr1, colr2 = st.columns(2)
		with colr1:
			st.download_button(
				"Baixar equipamentos (CSV)",
				data=to_csv(report_equipments),
				file_name="relatorio_equipamentos.csv",
				mime="text/csv",
			)
		with colr2:
			st.download_button(
				"Baixar movimentações (CSV)",
				data=to_csv(report_movements),
				file_name="relatorio_movimentacoes.csv",
				mime="text/csv",
			)


if __name__ == "__main__":
	main()
