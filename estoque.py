import streamlit as st
import services
import csv
import os
import hmac
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo
import pandas as pd

# =========================
# Funções auxiliares
# =========================
def para_csv(linhas):
    if not linhas:
        return ""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(linhas[0].keys()))
    writer.writeheader()
    writer.writerows(linhas)
    return output.getvalue()


def formatar_data_iso(valor):
    if not valor:
        return ""
    try:
        if "T" in valor:
            dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(valor)
        if dt.tzinfo is None:
            return dt.strftime("%d/%m/%Y %H:%M")
        local = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        return local.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return valor

def exibir_tombo(valor):
    return valor if valor else "S/N"

def check_password():
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = ""

    if st.session_state.auth_ok:
        return True

    app_password = st.secrets.get("APP_PASSWORD") or os.getenv("APP_PASSWORD", "")
    if not app_password:
        st.error("Defina APP_PASSWORD no st.secrets ou como variavel de ambiente.")
        return False

    st.markdown(
        """
        <style>
            header, footer { visibility: hidden; height: 0; }
            #MainMenu { visibility: hidden; height: 0; }
            div[data-testid="stDecoration"],
            div[data-testid="stToolbar"],
            div[data-testid="stStatusWidget"],
            div[data-testid="stHeader"] { display: none !important; }
            .stApp, .stAppViewContainer, .main {
                background: #ffffff;
            }
            .block-container {
                padding-top: 1.2rem !important;
                padding-bottom: 2rem !important;
            }
            div[data-testid="stContainer"] {
                background: #ffffff;
                border: 1px solid #e6e9ef;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.06);
                border-radius: 14px;
                padding: 1.6rem 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 2, 1])
    with center:
        with st.container(border=False):
            st.markdown("### Acesso restrito")
            st.caption("Selecione o usuário e informe a senha.")
            usuario = st.selectbox(
                "Usuário",
                ["Marcio Santana", "William Ferreira"],
                index=0,
            )
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                if hmac.compare_digest(senha, app_password):
                    st.session_state.auth_ok = True
                    st.session_state.auth_user = usuario
                    st.rerun()
                else:
                    st.error("Senha invalida.")

            st.markdown(" ")
            st.image("assets/logo.png", use_container_width=True)
    return False
# =========================
# App
# =========================
def main():
    st.set_page_config(
        page_title="Inventário TI",
        page_icon="🖥️",
        layout="wide",
    )

    if not check_password():
        return

    with st.sidebar:
        if st.button("Sair"):
            st.session_state.auth_ok = False
            st.rerun()

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
            :root {
                --metric-bg: #f8f9fa;
                --metric-border: #e6e9ef;
                --metric-text: #0f172a;
            }
            [data-theme="dark"] {
                --metric-bg: #1f2937;
                --metric-border: #334155;
                --metric-text: #e5e7eb;
            }
            div[data-testid="stMetric"] {
                background-color: var(--metric-bg);
                border: 1px solid var(--metric-border);
                padding: 1rem;
                border-radius: 10px;
            }
            div[data-testid="stMetric"] * {
                color: var(--metric-text) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🖥️ Controle e Inventário de Equipamentos da TI")
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
        equipamentos_view = [
            {
                **{k: v for k, v in e.items() if k != "ativo"},
                "tombo": exibir_tombo(e.get("tombo")),
                "data_criacao": formatar_data_iso(e.get("data_criacao")),
            }
            for e in equipamentos
        ]

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
                equipamentos_view,
                use_container_width=True,
                hide_index=True,
                height=450,
            )

        # ---------- ATUALIZAÇÃO ----------
        if equipamentos:
            with st.container(border=True):
                st.subheader("✏️ Atualizar ou baixar equipamento")

                mapa_equip = {
                    f"{e['equipamento']} ({exibir_tombo(e.get('tombo'))})": e
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
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
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
                f"{e['equipamento']} ({exibir_tombo(e.get('tombo'))})": e
                for e in equipamentos_todos
            }

            with st.form("form_movimentacao", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    escolha = st.selectbox("Equipamento", list(mapa_equip.keys()))
                with col2:
                    tipo = st.selectbox(
                        "Tipo",
                        [
                            "Transferência",
                            "Quebra",
                            "Manutenção",
                            "Devolução",
                        ],
                    )

                observacao = st.text_input("Observação")
                novo_setor = (
                    st.text_input("Novo setor") if tipo == "Transferência" else ""
                )
                nova_localizacao = (
                    st.text_input("Nova localização") if tipo == "Transferência" else ""
                )

                enviado = st.form_submit_button(
                    "Registrar movimentação", use_container_width=True
                )

                if enviado:
                    ok, msg = services.registrar_movimentacao(
                        mapa_equip[escolha],
                        tipo,
                        1,
                        observacao,
                        novo_setor=novo_setor,
                        nova_localizacao=nova_localizacao,
                    )
                    if ok: 
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)  # Atualiza a página para mostrar a nova movimentação
                    

        st.subheader("📜 Últimas movimentações")
        movimentacoes_view = [
            {
                **{k: v for k, v in m.items() if k != "quantidade"},
                "tombo": exibir_tombo(m.get("tombo")),
            }
            for m in services.listar_movimentacoes(limite=200)
        ]
        st.dataframe(
            movimentacoes_view,
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

        st.subheader("📈 Panorama geral por status")
        equipamentos_todos = services.listar_equipamentos(ativo_apenas=False)
        status_base = ["Ativo", "Em manutenção", "Quebrado", "Baixado", "Devolvido"]
        contagem_map = {status: 0 for status in status_base}
        for e in equipamentos_todos:
            status = e.get("status") or "Ativo"
            contagem_map[status] = contagem_map.get(status, 0) + 1
        dados_status = [
            {"Status": status, "Total": contagem_map.get(status, 0)}
            for status in status_base
        ]
        df_status = pd.DataFrame(dados_status)
        st.bar_chart(df_status, x="Status", y="Total", height=320)

        st.subheader("📤 Exportar relatórios")

        relatorio_equipamentos = [
            {
                "Equipamento": e["equipamento"],
                "Tombo": exibir_tombo(e.get("tombo")),
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
                "Tombo": exibir_tombo(m.get("tombo")),
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
