import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="DRE Granja", page_icon="🐔", layout="wide")
st.title("🐔 DRE - Granja")

# CABEÇALHOS DA SUA PLANILHA
HEADERS_MOVIMENTACOES = ['Data', 'Descricao', 'Categoria', 'Tipo', 'Valor']

scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
service_account_info = dict(st.secrets["gcp_service_account"])
service_account_info["private_key"] = service_account_info["private_key"].replace('\\n', '\n')

try:
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(st.secrets["private_gsheets_url"])
    sheet = spreadsheet.worksheet("MOVIMENTACOES")

    dados = sheet.get_all_records(expected_headers=HEADERS_MOVIMENTACOES)
    df = pd.DataFrame(dados)

    if df.empty:
        st.info("Aba MOVIMENTACOES sem lançamentos. Adicione dados na planilha.")
        st.stop()

    # LIMPEZA E PADRONIZAÇÃO DOS DADOS
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    df.dropna(subset=['Data'], inplace=True)

    for col in ['Descricao', 'Categoria', 'Tipo']:
        df[col] = df[col].astype(str).str.strip().str.title()

    df['Mes'] = df['Data'].dt.strftime('%Y-%m')

    st.success("Planilha conectada!")

    # FILTRO POR MÊS
    st.sidebar.header("Filtros")
    meses_disponiveis = sorted(df['Mes'].unique(), reverse=True)
    mes_selecionado = st.sidebar.selectbox("Selecione o Mês:", meses_disponiveis)

    df_filtrado = df[df['Mes'] == mes_selecionado]

    st.subheader(f"Lançamentos de {mes_selecionado}")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # CÁLCULO DRE
    st.subheader("📊 Resumo DRE")

    receitas = df_filtrado[df_filtrado['Tipo'] == 'Entrada']['Valor'].sum()
    custos = df_filtrado[(df_filtrado['Tipo'].isin(['Saida', 'Saída'])) & (df_filtrado['Categoria'] == 'Custo')]['Valor'].sum()
    despesas = df_filtrado[(df_filtrado['Tipo'].isin(['Saida', 'Saída'])) & (df_filtrado['Categoria'] == 'Despesa')]['Valor'].sum()

    lucro_bruto = receitas - custos
    lucro_liquido = lucro_bruto - despesas
    margem = (lucro_liquido / receitas * 100) if receitas > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Receita Total", f"R$ {receitas:,.2f}")
    col2.metric("Custos", f"R$ {custos:,.2f}")
    col3.metric("Despesas", f"R$ {despesas:,.2f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Lucro Bruto", f"R$ {lucro_bruto:,.2f}")
    col5.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}")
    col6.metric("Margem Líquida", f"{margem:.1f}%")

    # GRÁFICO
    st.subheader("Gráfico por Categoria")
    if not df_filtrado.empty:
        fig = px.bar(df_filtrado, x='Categoria', y='Valor', color='Tipo',
                     barmode='group', text_auto='.2s',
                     color_discrete_map={'Entrada':'#2ECC71', 'Saida':'#E74C3C', 'Saída':'#E74C3C'})
        fig.update_layout(yaxis_title="Valor (R$)", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para o mês selecionado.")

    # DRE DETALHADO
    st.subheader("DRE Detalhado")
    dre_data = {
        'Descrição': ['(+) Receita Bruta', '(-) Custos', '(=) Lucro Bruto', '(-) Despesas', '(=) Lucro Líquido'],
        'Valor': [receitas, custos, lucro_bruto, despesas, lucro_liquido]
    }
    dre_df = pd.DataFrame(dre_data)
    dre_df['Valor'] = dre_df['Valor'].apply(lambda x: f"R$ {x:,.2f}")
    st.table(dre_df)

except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()
