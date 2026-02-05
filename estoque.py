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
				CREATE TABLE IF NOT EXISTS equipamentos (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					equipamento TEXT NOT NULL,
					tombo TEXT NOT NULL,
					setor TEXT,
					localizacao TEXT,
					status TEXT DEFAULT 'Ativo',
					ativo INTEGER DEFAULT 1,
					data_criacao TEXT DEFAULT (datetime('now'))
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
			columns = [row["name"] for row in conn.execute("PRAGMA table_info(equipamentos)")]
			if "localizacao" not in columns:
				conn.execute("ALTER TABLE equipamentos ADD COLUMN localizacao TEXT")
			if "status" not in columns:
				conn.execute("ALTER TABLE equipamentos ADD COLUMN status TEXT DEFAULT 'Ativo'")
			conn.execute("UPDATE equipamentos SET status = 'Ativo' WHERE status IS NULL OR status = ''")


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
		where_clauses.append("(equipamento LIKE ? OR tombo LIKE ?)")
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
		WHERE ativo = 1
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


def registrar_movimentacao(equipamento_id, tipo, setor_origem=None, setor_destino=None, observacao=None, quantidade=1):
	execute(
		"""
		INSERT INTO movimentacoes (equipamento_id, tipo, quantidade, setor_origem, setor_destino, observacao)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		[equipamento_id, tipo, quantidade, setor_origem, setor_destino, observacao],
	)


def obter_movimentacoes(limite=200):
	return fetch_all(
		"""
		SELECT m.id, e.equipamento, e.tombo, m.tipo, m.quantidade, m.setor_origem, m.setor_destino, m.observacao, m.data_movimentacao
		FROM movimentacoes m
		JOIN equipamentos e ON e.id = m.equipamento_id
		ORDER BY m.data_movimentacao DESC
		LIMIT ?
		""",
		[limite],
	)


def para_csv(linhas):
	if not linhas:
		return ""
	import csv
	from io import StringIO

	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=list(linhas[0].keys()))
	writer.writeheader()
	writer.writerows(linhas)
	return output.getvalue()


def main():
	st.set_page_config(page_title="Inventário TI", layout="wide")
	st.title("Controle de Inventário de Equipamentos da TI")
	init_db()

	abas = st.tabs(["Equipamentos", "Movimentações", "Relatórios"])

	with abas[0]:
		st.subheader("Cadastrar equipamento")
		with st.form("form_cadastro_equipamento", clear_on_submit=True):
			col1, col2, col3, col4 = st.columns(4)
			with col1:
				equipamento = st.text_input("Equipamento")
			with col2:
				tombo = st.text_input("Tombo")
			with col3:
				localizacao = st.text_input("Funcionário")
			with col4:
				setor = st.text_input("Setor")
			enviado = st.form_submit_button("Adicionar")
			if enviado:
				if not equipamento.strip() or not tombo.strip():
					st.error("Informe equipamento e tombo.")
				else:
					try:
						execute(
							"""
							INSERT INTO equipamentos (equipamento, tombo, localizacao, setor)
							VALUES (?, ?, ?, ?)
							""",
							[equipamento.strip(), tombo.strip(), localizacao.strip(), setor.strip()],
						)
						st.success("Equipamento cadastrado.")
					except sqlite3.IntegrityError:
						st.error("Tombo já existe.")

		st.subheader("Lista de equipamentos")
		colf1, colf2, colf3, colf4 = st.columns(4)
		with colf1:
			busca = st.text_input("Buscar por nome ou tombo")
		with colf2:
			setores = sorted({e.get("setor") or "Sem setor" for e in get_equipamentos(ativo_apenas=False)})
			filtro_setor = st.selectbox("Setor", ["Todos"] + setores)
		with colf3:
			status_list = sorted({e.get("status") or "Ativo" for e in get_equipamentos(ativo_apenas=False)})
			filtro_status = st.selectbox("Status", ["Todos"] + status_list)
		with colf4:
			incluir_inativos = st.checkbox("Incluir inativos", value=False)
		ativo_apenas = not incluir_inativos
		equipamentos = get_equipamentos(
			ativo_apenas=ativo_apenas,
			setor=filtro_setor,
			busca=busca.strip(),
			status=filtro_status,
		)
		st.dataframe(equipamentos, use_container_width=True)

		st.subheader("Atualizar ou desativar")
		if equipamentos:
			mapa_equip = {f"{e['equipamento']} ({e['tombo']})": e for e in equipamentos}
			escolha = st.selectbox("Equipamento", list(mapa_equip.keys()))
			selecionado = mapa_equip[escolha]
			status_opcoes = ["Ativo", "Em manutenção", "Quebrado", "Baixado", "Devolvido"]
			status_atual = selecionado.get("status") or "Ativo"
			if status_atual not in status_opcoes:
				status_opcoes = [status_atual] + status_opcoes
			col1, col2, col3, col4 = st.columns(4)
			with col1:
				novo_equipamento = st.text_input("Equipamento", value=selecionado.get("equipamento") or "")
			with col2:
				nova_localizacao = st.text_input("Localização", value=selecionado.get("localizacao") or "")
			with col3:
				novo_setor = st.text_input("Setor", value=selecionado.get("setor") or "")
			with col4:
				novo_status = st.selectbox("Status", status_opcoes, index=status_opcoes.index(status_atual))
			col5, col6 = st.columns(2)
			with col5:
				if st.button("Atualizar"):
					novo_ativo = 0 if novo_status in ("Baixado", "Devolvido") else 1
					execute(
						"""
						UPDATE equipamentos
						SET equipamento = ?, localizacao = ?, setor = ?, status = ?, ativo = ?
						WHERE id = ?
						""",
						[
							novo_equipamento.strip(),
							nova_localizacao.strip(),
							novo_setor.strip(),
							novo_status,
							novo_ativo,
							selecionado["id"],
						],
					)
					st.success("Equipamento atualizado.")
			with col6:
				if st.button("Desativar"):
					execute("UPDATE equipamentos SET ativo = 0 WHERE id = ?", [selecionado["id"]])
					st.warning("Equipamento desativado.")
		else:
			st.info("Cadastre um equipamento para começar.")

	with abas[1]:
		st.subheader("Registrar movimentação")
		equipamentos_todos = get_equipamentos(ativo_apenas=False)
		if not equipamentos_todos:
			st.info("Cadastre um equipamento para começar.")
		else:
			mapa_equip = {f"{e['equipamento']} ({e['tombo']})": e for e in equipamentos_todos}
			with st.form("form_movimentacao", clear_on_submit=True):
				col1, col2, col3, col4 = st.columns(4)
				with col1:
					escolha = st.selectbox("Equipamento", list(mapa_equip.keys()))
				with col2:
					tipo = st.selectbox(
						"Tipo",
						["Entrada", "Transferência", "Quebra", "Manutenção", "Baixa", "Devolução", "Retorno"],
					)
				with col3:
					quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
				with col4:
					observacao = st.text_input("Observação")
				novo_setor = ""
				if tipo == "Transferência":
					novo_setor = st.text_input("Novo setor")
				enviado = st.form_submit_button("Registrar")
				if enviado:
					selecionado = mapa_equip[escolha]
					setor_origem = selecionado.get("setor")
					setor_destino = setor_origem
					novo_status = selecionado.get("status") or "Ativo"
					novo_ativo = selecionado.get("ativo")
					if tipo == "Transferência" and not novo_setor.strip():
						st.error("Informe o novo setor para transferência.")
						st.stop()
					if tipo == "Transferência":
						setor_destino = novo_setor.strip()
					if tipo == "Quebra":
						novo_status = "Quebrado"
					if tipo == "Manutenção":
						novo_status = "Em manutenção"
					if tipo == "Baixa":
						novo_status = "Baixado"
						novo_ativo = 0
					if tipo == "Devolução":
						novo_status = "Devolvido"
						novo_ativo = 0
					if tipo in ("Entrada", "Retorno"):
						novo_status = "Ativo"
						novo_ativo = 1
					execute(
						"""
						UPDATE equipamentos
						SET setor = ?, status = ?, ativo = ?
						WHERE id = ?
						""",
						[setor_destino, novo_status, novo_ativo, selecionado["id"]],
					)
					registrar_movimentacao(
						selecionado["id"],
						tipo,
						setor_origem=setor_origem,
						setor_destino=setor_destino,
						observacao=observacao.strip(),
						quantidade=quantidade,
					)
					st.success("Movimentação registrada.")

		st.subheader("Últimas movimentações")
		movimentacoes = obter_movimentacoes(limite=200)
		st.dataframe(movimentacoes, use_container_width=True)

	with abas[2]:
		st.subheader("Resumo por setor")
		contagem_setor = contar_por_setor()
		total = sum(s["total"] for s in contagem_setor) if contagem_setor else 0
		st.metric("Total de equipamentos", total)
		st.dataframe(contagem_setor, use_container_width=True)

		st.subheader("Resumo por status")
		contagem_status = contar_por_status()
		st.dataframe(contagem_status, use_container_width=True)

		st.subheader("Equipamentos por setor")
		lista_setores = [s["setor"] for s in contagem_setor] or ["Sem setor"]
		setor_selecionado = st.selectbox("Setor", lista_setores)
		equipamentos = get_equipamentos(ativo_apenas=True, setor=setor_selecionado)
		st.dataframe(equipamentos, use_container_width=True)

		st.subheader("Exportar relatórios")
		relatorio_equipamentos = [
			{
				"Equipamento": e["equipamento"],
				"Tombo": e["tombo"],
				"Setor": e.get("setor") or "",
				"Localização": e.get("localizacao") or "",
				"Status": e.get("status") or "Ativo",
				"Ativo": "Sim" if e.get("ativo") else "Não",
				"Data de criação": e.get("data_criacao") or "",
			}
			for e in get_equipamentos(ativo_apenas=False)
		]
		relatorio_movimentacoes = [
			{
				"Equipamento": m["equipamento"],
				"Tombo": m["tombo"],
				"Tipo": m["tipo"],
				"Quantidade": m["quantidade"],
				"Setor origem": m.get("setor_origem") or "",
				"Setor destino": m.get("setor_destino") or "",
				"Observação": m.get("observacao") or "",
				"Data": m.get("data_movimentacao") or "",
			}
			for m in obter_movimentacoes(limite=1000)
		]
		colr1, colr2 = st.columns(2)
		with colr1:
			st.download_button(
				"Baixar equipamentos (CSV)",
				data=para_csv(relatorio_equipamentos),
				file_name="relatorio_equipamentos.csv",
				mime="text/csv",
			)
		with colr2:
			st.download_button(
				"Baixar movimentações (CSV)",
				data=para_csv(relatorio_movimentacoes),
				file_name="relatorio_movimentacoes.csv",
				mime="text/csv",
			)


if __name__ == "__main__":
	main()
