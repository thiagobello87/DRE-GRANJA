import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

st.set_page_config(page_title="DRE Granja", layout="wide")
st.title("🐔 Sistema DRE - Granja")

# Inicializa os dados na sessão
if 'dados' not in st.session_state:
    st.session_state.dados = {
        'MOVIMENTACOES': pd.DataFrame(columns=['Data','Tipo','Categoria','Descrição','Valor']),
        'CONFIG': pd.DataFrame(columns=['Data_Alojamento', 'Idade_Inicial_Semanas', 'Qtd_Aves_Inicial']),
        'PRODUCAO': pd.DataFrame(columns=['Data','Qtd_Ovos','Aves_Mortas','Racao_Kg'])
    }

dados = st.session_state.dados

# Sidebar para lançamentos financeiros
with st.sidebar:
    st.header("Lançar Movimentação")
    data = st.date_input("Data", datetime.now())
    tipo = st.selectbox("Tipo", ["Receita","Despesa"])
    if tipo == "Receita":
        categoria = st.selectbox("Categoria", ["Venda de Ovos","Venda de Aves","Outros"])
    else:
        categoria = st.selectbox("Categoria", ["Ração","Medicamentos","Salários","Energia","Manutenção","Outros"])
    desc = st.text_input("Descrição")
    valor = st.number_input("Valor R$", min_value=0.0, format="%.2f")
    if st.button("Adicionar Lançamento"):
        novo = pd.DataFrame([{'Data':data,'Tipo':tipo,'Categoria':categoria,'Descrição':desc,'Valor':valor}])
        st.session_state.dados['MOVIMENTACOES'] = pd.concat([st.session_state.dados['MOVIMENTACOES'], novo], ignore_index=True)
        st.success("Lançado!")

# Abas principais
tab1, tab2, tab3, tab4 = st.tabs(["📊 DRE Geral", "🐔 Produção Diária", "📝 Lançamentos", "⚙️ Config Lote"])

with tab1:
    st.header("Resumo Financeiro e Zootécnico")
    df_mov = st.session_state.dados['MOVIMENTACOES'].copy()
    df_prod = st.session_state.dados['PRODUCAO'].copy()

    if not df_mov.empty:
        df_mov['Data'] = pd.to_datetime(df_mov['Data'])
        receitas = df_mov[df_mov['Tipo']=='Receita']['Valor'].sum()
        despesas = df_mov[df_mov['Tipo']=='Despesa']['Valor'].sum()
        lucro = receitas - despesas

        col1,col2,col3,col4 = st.columns(4)
        col1.metric("Receitas Totais", f"R$ {receitas:,.2f}")
        col2.metric("Despesas Totais", f"R$ {despesas:,.2f}")
        col3.metric("Lucro Líquido", f"R$ {lucro:,.2f}")

        # Indicadores Zootécnicos
        if not df_prod.empty and 'Qtd_Aves_Inicial' in dados['CONFIG'].columns:
            aves_inicial = dados['CONFIG']['Qtd_Aves_Inicial'].iloc[0]
            total_mortas = df_prod['Aves_Mortas'].sum()
            aves_atual = aves_inicial - total_mortas
            mort_pct = (total_mortas / aves_inicial * 100) if aves_inicial > 0 else 0
            total_ovos = df_prod['Qtd_Ovos'].sum()
            total_racao = df_prod['Racao_Kg'].sum()
            custo_racao = df_mov[df_mov['Categoria']=='Ração']['Valor'].sum()
            custo_duzia = (custo_racao / (total_ovos / 12)) if total_ovos > 0 else 0

            col4.metric("Mortalidade", f"{mort_pct:.2f}%", f"{int(total_mortas)} aves")

            col5,col6,col7 = st.columns(3)
            col5.metric("Aves Atuais", f"{int(aves_atual)}")
            col6.metric("Ovos Produzidos", f"{int(total_ovos)}")
            col7.metric("Custo/Dúzia", f"R$ {custo_duzia:.2f}")

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            fig_pizza = px.pie(df_mov, values='Valor', names='Categoria', title='Despesas por Categoria')
            st.plotly_chart(fig_pizza, use_container_width=True)
        with col_graf2:
            df_mes = df_mov.groupby([df_mov['Data'].dt.to_period('M'), 'Tipo'])['Valor'].sum().reset_index()
            df_mes['Data'] = df_mes['Data'].astype(str)
            fig_bar = px.bar(df_mes, x='Data', y='Valor', color='Tipo', barmode='group', title='Receitas vs Despesas por Mês')
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Adicione o primeiro lançamento na barra lateral ←")

with tab2:
    st.header("Lançamento de Produção Diária")
    col_a, col_b, col_c, col_d = st.columns(4)
    data_prod = col_a.date_input("Data da Produção", datetime.now(), key="data_prod")
    qtd_ovos = col_b.number_input("Qtd de Ovos", min_value=0, step=1)
    aves_mortas = col_c.number_input("Aves Mortas", min_value=0, step=1)
    racao_kg = col_d.number_input("Ração Consumida Kg", min_value=0.0, format="%.1f")

    if st.button("Adicionar Produção do Dia"):
        novo = pd.DataFrame([{'Data':data_prod,'Qtd_Ovos':qtd_ovos,'Aves_Mortas':aves_mortas,'Racao_Kg':racao_kg}])
        st.session_state.dados['PRODUCAO'] = pd.concat([st.session_state.dados['PRODUCAO'], novo], ignore_index=True)
        st.success("Produção lançada!")

    st.subheader("Histórico de Produção")
    if not st.session_state.dados['PRODUCAO'].empty:
        st.dataframe(st.session_state.dados['PRODUCAO'].sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.info("Nenhuma produção lançada ainda.")

with tab3:
    st.header("Histórico de Lançamentos Financeiros")
    df_mov = st.session_state.dados['MOVIMENTACOES']
    if not df_mov.empty:
        st.dataframe(df_mov.sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.info("Nenhum lançamento ainda.")

with tab4:
    st.header("Configuração do Lote Atual")

    if 'CONFIG' in dados and not dados['CONFIG'].empty:
        data_padrao = dados['CONFIG']['Data_Alojamento'].iloc[0]
        idade_padrao = int(dados['CONFIG']['Idade_Inicial_Semanas'].iloc[0])
        aves_padrao = int(dados['CONFIG']['Qtd_Aves_Inicial'].iloc[0])
    else:
        data_padrao = date.today()
        idade_padrao = 1
        aves_padrao = 1000

    data_aloj = st.date_input("Data de Alojamento", value=data_padrao)
    idade_sem = st.number_input("Idade Inicial do Lote em Semanas", min_value=0, value=idade_padrao)
    qtd_aves = st.number_input("Qtd de Aves Alojadas", min_value=1, value=aves_padrao)

    if st.button("Salvar Configurações do Lote"):
        st.session_state.dados['CONFIG'] = pd.DataFrame([{
            'Data_Alojamento': data_aloj,
            'Idade_Inicial_Semanas': idade_sem,
            'Qtd_Aves_Inicial': qtd_aves
        }])
        st.success("Configurações salvas!")
        st.rerun()
