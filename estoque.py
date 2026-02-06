import streamlit as st
import services
import csv
from io import StringIO

# =========================
# Utils
# =========================
def para_csv(linhas):
    if not linhas:
        return ""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(linhas[0].keys()))
    writer.writeheader()
    writer.writerows(linhas)
    return output.getvalue()


# =========================
# App
# =========================
def main():
    st.set_page_config(
        page_title="Inventário TI",
        page_icon="🖥️",
        layout="wide",
    )

    # CSS
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }
            h1, h2, h3 {
                font-weight: 600;
            }
            div[data-testid="stMetric"] {
                background-color: #f8f9fa;
                padding: 1rem;
                border-radius: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🖥️ Controle de Inventário de Equipamentos de TI")
    services.init_db()

    abas = st.tabs(
        ["🖥️ Equipamentos", "🔄 Movimentações", "📊 Relatórios"]
    )

    # ==========================================================
    # ABA 1 - EQUIPAMENTOS
    # ==========================================================
    with abas[0]:

        # ---------- SIDEBAR (Filtros) ----------
        with st.sidebar:
            st.header("🔍 Filtros")
            busca = st.text_input("Buscar por nome ou tombo")

            todos = services.listar_equipamentos(ativo_apenas=False)
            setores = sorted({e.get("setor") or "Sem setor" for e in todos})
            filtro_setor = st.selectbox("Setor", ["Todos"] + setores)

            status_list = sorted({e.get("status") or "Ativo" for e in todos})
            filtro_status = st.selectbox("Status", ["Todos"] + status_list)

            incluir_inativos = st.checkbox("Incluir inativos")

        ativo_apenas = not incluir_inativos

        equipamentos = services.listar_equipamentos(
            ativo_apenas=ativo_apenas,
            setor=filtro_setor,
            busca=busca.strip(),
            status=filtro_status,
        )

        # ---------- MÉTRICAS ----------
        contagem_status = services.contar_por_status()
        total = sum(s["total"] for s in contagem_status) if contagem_status else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", total)
        col2.metric(
            "Ativos",
            next((s["total"] for s in contagem_status if s["status"] == "Ativo"), 0),
        )
        col3.metric(
            "Em manutenção",
            next((s["total"] for s in contagem_status if s["status"] == "Em manutenção"), 0),
        )
        col4.metric(
            "Baixados",
            next((s["total"] for s in contagem_status if s["status"] == "Baixado"), 0),
        )

        # ---------- CADASTRO ----------
        with st.container(border=True):
            st.subheader("➕ Cadastrar equipamento")
            with st.form("form_cadastro_equipamento", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    equipamento = st.text_input("Nome do equipamento")
                    tombo = st.text_input("Tombo")
                with col2:
                    localizacao = st.text_input("Localização / Funcionário")
                    setor = st.text_input("Setor")

                enviado = st.form_submit_button(
                    "Salvar equipamento", use_container_width=True
                )

                if enviado:
                    ok, mensagem = services.cadastrar_equipamento(
                        equipamento, tombo, localizacao, setor
                        
                    )
                    if ok:
                        st.success(mensagem)
                        st.rerun()  # Atualiza a página para mostrar o novo equipamento
                    else: 
                        st.error(mensagem)
            

        # ---------- LISTA ----------
        with st.container(border=True):
            st.subheader("📋 Lista de equipamentos")
            st.dataframe(
                equipamentos,
                use_container_width=True,
                hide_index=True,
                height=450,
            )

        # ---------- ATUALIZAÇÃO ----------
        if equipamentos:
            with st.container(border=True):
                st.subheader("✏️ Atualizar ou baixar equipamento")

                mapa_equip = {
                    f"{e['equipamento']} ({e['tombo']})": e
                    for e in equipamentos
                }
                escolha = st.selectbox(
                    "Selecione o equipamento", list(mapa_equip.keys())
                )
                selecionado = mapa_equip[escolha]

                status_opcoes = [
                    "Ativo",
                    "Em manutenção",
                    "Quebrado",
                    "Baixado",
                    "Devolvido",
                ]
                status_atual = selecionado.get("status") or "Ativo"

                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input(
                        "Nome", selecionado.get("equipamento") or ""
                    )
                    nova_localizacao = st.text_input(
                        "Localização", selecionado.get("localizacao") or ""
                    )
                with col2:
                    novo_setor = st.text_input(
                        "Setor", selecionado.get("setor") or ""
                    )
                    novo_status = st.selectbox(
                        "Status", status_opcoes, index=status_opcoes.index(status_atual)
                    )

                colb1, colb2 = st.columns(2)
                with colb1:
                    if st.button("Atualizar", use_container_width=True):
                        ok, msg = services.atualizar_equipamento(
                            selecionado["id"],
                            novo_nome,
                            nova_localizacao,
                            novo_setor,
                            novo_status,
                        )
                        st.success(msg) if ok else st.error(msg)

                with colb2:
                    if st.button(
                        "Baixar equipamento",
                        type="secondary",
                        use_container_width=True,
                    ):
                        _, msg = services.desativar_equipamento(selecionado["id"])
                        st.warning(msg)

    # ==========================================================
    # ABA 2 - MOVIMENTAÇÕES
    # ==========================================================
    with abas[1]:
        st.subheader("🔄 Registrar movimentação")

        equipamentos_todos = services.listar_equipamentos(ativo_apenas=False)

        if not equipamentos_todos:
            st.info("Cadastre um equipamento para começar.")
        else:
            mapa_equip = {
                f"{e['equipamento']} ({e['tombo']})": e
                for e in equipamentos_todos
            }

            with st.form("form_movimentacao", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    escolha = st.selectbox("Equipamento", list(mapa_equip.keys()))
                with col2:
                    tipo = st.selectbox(
                        "Tipo",
                        [
                            "Entrada",
                            "Transferência",
                            "Quebra",
                            "Manutenção",
                            "Baixa",
                            "Devolução",
                            "Retorno",
                        ],
                    )
                with col3:
                    quantidade = st.number_input(
                        "Quantidade", min_value=1, step=1, value=1
                    )

                observacao = st.text_input("Observação")
                novo_setor = (
                    st.text_input("Novo setor") if tipo == "Transferência" else ""
                )

                enviado = st.form_submit_button(
                    "Registrar movimentação", use_container_width=True
                )

                if enviado:
                    ok, msg = services.registrar_movimentacao(
                        mapa_equip[escolha],
                        tipo,
                        quantidade,
                        observacao,
                        novo_setor=novo_setor,
                    )
                    st.success(msg) if ok else st.error(msg)

        st.subheader("📜 Últimas movimentações")
        st.dataframe(
            services.listar_movimentacoes(limite=200),
            use_container_width=True,
            hide_index=True,
        )

    # ==========================================================
    # ABA 3 - RELATÓRIOS
    # ==========================================================
    with abas[2]:
        st.subheader("📊 Resumos")

        contagem_setor = services.contar_por_setor()
        st.dataframe(contagem_setor, use_container_width=True, hide_index=True)

        st.subheader("📤 Exportar relatórios")

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

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Equipamentos (CSV)",
                data=para_csv(relatorio_equipamentos),
                file_name="relatorio_equipamentos.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "⬇️ Movimentações (CSV)",
                data=para_csv(relatorio_movimentacoes),
                file_name="relatorio_movimentacoes.csv",
                mime="text/csv",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()