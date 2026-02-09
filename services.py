import sqlite3
import data_access


def init_db():
	data_access.init_db()


def listar_equipamentos(ativo_apenas=True, setor=None, busca=None, status=None):
	return data_access.get_equipamentos(
		ativo_apenas=ativo_apenas,
		setor=setor,
		busca=busca,
		status=status,
	)


def contar_por_setor():
	return data_access.contar_por_setor()


def contar_por_status():
	return data_access.contar_por_status()


def listar_movimentacoes(limite=200):
	return data_access.obter_movimentacoes(limite=limite)


def cadastrar_equipamento(equipamento, tombo, localizacao, setor):
	if not equipamento.strip() or not tombo.strip():
		return False, "Informe equipamento e tombo."
	try:
		data_access.execute(
			"""
			INSERT INTO equipamentos (equipamento, tombo, localizacao, setor)
			VALUES (?, ?, ?, ?)
			""",
			[equipamento.strip(), tombo.strip(), localizacao.strip(), setor.strip()],	
		)
		return True, "Equipamento cadastrado."
	except sqlite3.IntegrityError:
		return False, "Tombo já existe."


def atualizar_equipamento(equipamento_id, equipamento, localizacao, setor, status):
	novo_ativo = 0 if status in ("Baixado", "Devolvido") else 1
	data_access.execute(
		"""
		UPDATE equipamentos
		SET equipamento = ?, localizacao = ?, setor = ?, status = ?, ativo = ?
		WHERE id = ?
		""",
		[
			equipamento.strip(),
			localizacao.strip(),
			setor.strip(),
			status,
			novo_ativo,
			equipamento_id,
		],
	)
	return True, "Equipamento atualizado."


def desativar_equipamento(equipamento_id):
	data_access.execute("UPDATE equipamentos SET ativo = 0 WHERE id = ?", [equipamento_id])
	return True, "Equipamento desativado."


def registrar_movimentacao(selecionado, tipo, quantidade, observacao, novo_setor=""):
	setor_origem = selecionado.get("setor")
	setor_destino = setor_origem
	novo_status = selecionado.get("status") or "Ativo"
	novo_ativo = selecionado.get("ativo")
	if tipo == "Transferência" and not novo_setor.strip():
		return False, "Informe o novo setor para transferência."
	if tipo == "Transferência":
		setor_destino = novo_setor.strip()
	if tipo == "Quebra":
		novo_status = "Quebrado"
	if tipo == "Manutenção":
		novo_status = "Em manutenção"
	if tipo == "Baixa":
		novo_status = "Baixado"
		novo_ativo = 0
		setor_destino = "TI"
	if tipo == "Devolução":
		# Devolução volta o equipamento para o inventário da TI
		novo_status = "Ativo"
		novo_ativo = 1
		setor_destino = "TI"
	if tipo in ("Entrada", "Retorno"):
		novo_status = "Ativo"
		novo_ativo = 1
	data_access.execute(
		"""
		UPDATE equipamentos
		SET setor = ?, status = ?, ativo = ?
		WHERE id = ?
		""",
		[setor_destino, novo_status, novo_ativo, selecionado["id"]],
	)
	data_access.registrar_movimentacao(
		selecionado["id"],
		tipo,
		setor_origem=setor_origem,
		setor_destino=setor_destino,
		observacao=observacao.strip(),
		quantidade=quantidade,
	)
	return True, "Movimentação registrada."
