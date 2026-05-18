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
        'CONFIG': pd.DataFrame(columns=['Data_Alojamento', 'Idade_Inicial_Semanas'])
    }

dados = st.session_state.dados

# Sidebar para lançamentos
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
tab1, tab2, tab3 = st.tabs(["📊 DRE Geral", "📝 Lançamentos", "⚙️ Config Lote"])

with tab1:
    st.header("Resumo Financeiro")
    df = st.session_state.dados['MOVIMENTACOES'].copy()
    if not df.empty:
        df['Data'] = pd.to_datetime(df['Data'])
        receitas = df[df['Tipo']=='Receita']['Valor'].sum()
        despesas = df[df['Tipo']=='Despesa']['Valor'].sum()
        lucro = receitas - despesas

        col1,col2,col3 = st.columns(3)
        col1.metric("Receitas Totais", f"R$ {receitas:,.2f}")
        col2.metric("Despesas Totais", f"R$ {despesas:,.2f}")
        col3.metric("Lucro Líquido", f"R$ {lucro:,.2f}")

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            fig_pizza = px.pie(df, values='Valor', names='Categoria', title='Despesas por Categoria')
            st.plotly_chart(fig_pizza, use_container_width=True)
        with col_graf2:
            df_mes = df.groupby([df['Data'].dt.to_period('M'), 'Tipo'])['Valor'].sum().reset_index()
            df_mes['Data'] = df_mes['Data'].astype(str)
            fig_bar = px.bar(df_mes, x='Data', y='Valor', color='Tipo', barmode='group', title='Receitas vs Despesas por Mês')
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Adicione o primeiro lançamento na barra lateral ←")

with tab2:
    st.header("Histórico de Lançamentos")
    df_mov = st.session_state.dados['MOVIMENTACOES']
    if not df_mov.empty:
        st.dataframe(df_mov.sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.info("Nenhum lançamento ainda.")

with tab3:
    st.header("Configuração do Lote Atual")

    # CORREÇÃO DO BUG AQUI - V3.2
    if 'CONFIG' in dados and not dados['CONFIG'].empty and 'Data_Alojamento' in dados['CONFIG'].columns:
        data_padrao = dados['CONFIG']['Data_Alojamento'].iloc[0]
        idade_padrao = int(dados['CONFIG']['Idade_Inicial_Semanas'].iloc[0])
    else:
        data_padrao = date.today()
        idade_padrao = 1

    data_aloj = st.date_input("Data de Alojamento", value=data_padrao)
    idade_sem = st.number_input("Idade Inicial do Lote em Semanas", min_value=0, value=idade_padrao)

    if st.button("Salvar Configurações do Lote"):
        st.session_state.dados['CONFIG'] = pd.DataFrame([{
            'Data_Alojamento': data_aloj,
            'Idade_Inicial_Semanas': idade_sem
        }])
        st.success("Configurações salvas!")
        st.rerun()
