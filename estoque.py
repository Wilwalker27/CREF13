import streamlit as st

import services

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
	services.init_db()

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
				ok, mensagem = services.cadastrar_equipamento(
					equipamento,
					tombo,
					localizacao,
					setor,
				)
				if ok:
					st.success(mensagem)
				else:
					st.error(mensagem)

		st.subheader("Lista de equipamentos")
		colf1, colf2, colf3, colf4 = st.columns(4)
		with colf1:
			busca = st.text_input("Buscar por nome ou tombo")
		with colf2:
			setores = sorted({e.get("setor") or "Sem setor" for e in services.listar_equipamentos(ativo_apenas=False)})
			filtro_setor = st.selectbox("Setor", ["Todos"] + setores)
		with colf3:
			status_list = sorted({e.get("status") or "Ativo" for e in services.listar_equipamentos(ativo_apenas=False)})
			filtro_status = st.selectbox("Status", ["Todos"] + status_list)
		with colf4:
			incluir_inativos = st.checkbox("Incluir inativos", value=False)
		ativo_apenas = not incluir_inativos
		equipamentos = services.listar_equipamentos(
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
					ok, mensagem = services.atualizar_equipamento(
						selecionado["id"],
						novo_equipamento,
						nova_localizacao,
						novo_setor,
						novo_status,
					)
					if ok:
						st.success(mensagem)
					else:
						st.error(mensagem)
			with col6:
				if st.button("Desativar"):
					_, mensagem = services.desativar_equipamento(selecionado["id"])
					st.warning(mensagem)
		else:
			st.info("Cadastre um equipamento para começar.")

	with abas[1]:
		st.subheader("Registrar movimentação")
		equipamentos_todos = services.listar_equipamentos(ativo_apenas=False)
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
					ok, mensagem = services.registrar_movimentacao(
						selecionado,
						tipo,
						quantidade,
						observacao,
						novo_setor=novo_setor,
					)
					if ok:
						st.success(mensagem)
					else:
						st.error(mensagem)
						st.stop()

		st.subheader("Últimas movimentações")
		movimentacoes = services.listar_movimentacoes(limite=200)
		st.dataframe(movimentacoes, use_container_width=True)

	with abas[2]:
		st.subheader("Resumo por setor")
		contagem_setor = services.contar_por_setor()
		total = sum(s["total"] for s in contagem_setor) if contagem_setor else 0
		st.metric("Total de equipamentos", total)
		st.dataframe(contagem_setor, use_container_width=True)

		st.subheader("Resumo por status")
		contagem_status = services.contar_por_status()
		st.dataframe(contagem_status, use_container_width=True)

		st.subheader("Equipamentos por setor")
		lista_setores = [s["setor"] for s in contagem_setor] or ["Sem setor"]
		setor_selecionado = st.selectbox("Setor", lista_setores)
		equipamentos = services.listar_equipamentos(ativo_apenas=True, setor=setor_selecionado)
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
			for e in services.listar_equipamentos(ativo_apenas=False)
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
			for m in services.listar_movimentacoes(limite=1000)
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
