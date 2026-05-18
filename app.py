import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="DRE Granja", page_icon="🐔", layout="wide")
st.title("🐔 Sistema DRE - Granja")

# CABEÇALHOS DAS 3 ABAS
HEADERS_CONFIG = ['Data_Alojamento', 'Idade_Inicial_Semanas', 'Qtd_Aves_Inicial']
HEADERS_MOVIMENTACOES = ['Data', 'Descricao', 'Categoria', 'Tipo', 'Valor']
HEADERS_PRODUCAO = ['Data', 'Semana_Aves', 'Qtd_Ovos', 'Mortalidade', 'Consumo_Racao_Kg', 'Observacao']

scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
service_account_info = dict(st.secrets["gcp_service_account"])
service_account_info["private_key"] = service_account_info["private_key"].replace('\\n', '\n')

@st.cache_resource
def get_gsheet():
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(st.secrets["private_gsheets_url"])
    return spreadsheet

@st.cache_data(ttl=60)
def load_data():
    spreadsheet = get_gsheet()
    sh_config = spreadsheet.worksheet("CONFIG")
    sh_mov = spreadsheet.worksheet("MOVIMENTACOES")
    sh_prod = spreadsheet.worksheet("PRODUCAO")

    df_config = pd.DataFrame(sh_config.get_all_records(expected_headers=HEADERS_CONFIG))
    df_mov = pd.DataFrame(sh_mov.get_all_records(expected_headers=HEADERS_MOVIMENTACOES))
    df_prod = pd.DataFrame(sh_prod.get_all_records(expected_headers=HEADERS_PRODUCAO))
    return df_config, df_mov, df_prod

def append_row(sheet_name, row_data):
    spreadsheet = get_gsheet()
    sheet = spreadsheet.worksheet(sheet_name)
    sheet.append_row(row_data, value_input_option='USER_ENTERED')
    st.cache_data.clear()

# CARREGA DADOS
try:
    df_config, df_mov, df_prod = load_data()
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

# TRATAMENTO MOVIMENTACOES
if not df_mov.empty:
    df_mov['Valor'] = pd.to_numeric(df_mov['Valor'], errors='coerce').fillna(0)
    df_mov['Data'] = pd.to_datetime(df_mov['Data'], format='%d/%m/%Y', errors='coerce')
    for col in ['Descricao', 'Categoria', 'Tipo']:
        df_mov[col] = df_mov[col].astype(str).str.strip().str.title()
    df_mov['Mes'] = df_mov['Data'].dt.strftime('%Y-%m')

# TRATAMENTO PRODUCAO
if not df_prod.empty:
    df_prod['Data'] = pd.to_datetime(df_prod['Data'], format='%d/%m/%Y', errors='coerce')
    for col in ['Qtd_Ovos', 'Mortalidade', 'Consumo_Racao_Kg', 'Semana_Aves']:
        df_prod[col] = pd.to_numeric(df_prod[col], errors='coerce').fillna(0)

# TRATAMENTO CONFIG
qtd_aves_inicial = 0
if not df_config.empty:
    df_config['Qtd_Aves_Inicial'] = pd.to_numeric(df_config['Qtd_Aves_Inicial'], errors='coerce').fillna(0)
    qtd_aves_inicial = df_config['Qtd_Aves_Inicial'].iloc[-1] # Pega o último registro

# SIDEBAR - FILTROS E CADASTROS
st.sidebar.header("Filtros")
if not df_mov.empty:
    meses_disponiveis = sorted(df_mov['Mes'].unique(), reverse=True)
    mes_selecionado = st.sidebar.selectbox("Selecione o Mês:", meses_disponiveis)
    df_mov_filtrado = df_mov[df_mov['Mes'] == mes_selecionado]
else:
    mes_selecionado = date.today().strftime('%Y-%m')
    df_mov_filtrado = df_mov

st.sidebar.header("Lançamentos Rápidos")

# FORMULÁRIO MOVIMENTAÇÃO FINANCEIRA
with st.sidebar.form("form_mov", clear_on_submit=True):
    st.subheader("Financeiro")
    data_mov = st.date_input("Data", value=date.today())
    desc_mov = st.text_input("Descrição")
    cat_mov = st.selectbox("Categoria", ["Receita", "Custo", "Despesa"])
    tipo_mov = "Entrada" if cat_mov == "Receita" else "Saida"
    valor_mov = st.number_input("Valor R$", min_value=0.0, format="%.2f")
    if st.form_submit_button("Salvar Lançamento"):
        nova_linha = [data_mov.strftime('%d/%m/%Y'), desc_mov, cat_mov, tipo_mov, valor_mov]
        append_row("MOVIMENTACOES", nova_linha)
        st.sidebar.success("Salvo!")
        st.rerun()

# FORMULÁRIO PRODUÇÃO DIÁRIA
with st.sidebar.form("form_prod", clear_on_submit=True):
    st.subheader("Produção Diária")
    data_prod = st.date_input("Data Produção", value=date.today())
    semana_aves = st.number_input("Semana das Aves", min_value=1, step=1)
    qtd_ovos = st.number_input("Qtd de Ovos", min_value=0, step=1)
    mortalidade = st.number_input("Mortalidade", min_value=0, step=1)
    consumo_racao = st.number_input("Consumo Ração Kg", min_value=0.0, format="%.2f")
    obs_prod = st.text_input("Observação")
    if st.form_submit_button("Salvar Produção"):
        nova_linha = [data_prod.strftime('%d/%m/%Y'), semana_aves, qtd_ovos, mortalidade, consumo_racao, obs_prod]
        append_row("PRODUCAO", nova_linha)
        st.sidebar.success("Salvo!")
        st.rerun()

# FORMULÁRIO CONFIG INICIAL
with st.sidebar.expander("Configurar Lote Inicial"):
    with st.form("form_config", clear_on_submit=True):
        data_aloj = st.date_input("Data Alojamento")
        idade_ini = st.number_input("Idade Inicial em Semanas", min_value=1, step=1)
        qtd_aves = st.number_input("Qtd Aves Inicial", min_value=1, step=1)
        if st.form_submit_button("Salvar Config"):
            nova_linha = [data_aloj.strftime('%d/%m/%Y'), idade_ini, qtd_aves]
            append_row("CONFIG", nova_linha)
            st.sidebar.success("Config salva!")
            st.rerun()

# DASHBOARD PRINCIPAL
st.header(f"Dashboard - {mes_selecionado}")

# CÁLCULOS DRE
receitas = df_mov_filtrado[df_mov_filtrado['Tipo'] == 'Entrada']['Valor'].sum()
custos = df_mov_filtrado[(df_mov_filtrado['Tipo'].isin(['Saida', 'Saída'])) & (df_mov_filtrado['Categoria'] == 'Custo')]['Valor'].sum()
despesas = df_mov_filtrado[(df_mov_filtrado['Tipo'].isin(['Saida', 'Saída'])) & (df_mov_filtrado['Categoria'] == 'Despesa')]['Valor'].sum()
lucro_bruto = receitas - custos
lucro_liquido = lucro_bruto - despesas
margem = (lucro_liquido / receitas * 100) if receitas > 0 else 0

# CÁLCULOS PRODUÇÃO
df_prod_mes = df_prod[df_prod['Data'].dt.strftime('%Y-%m') == mes_selecionado]
total_ovos = df_prod_mes['Qtd_Ovos'].sum()
total_mortalidade = df_prod_mes['Mortalidade'].sum()
total_racao = df_prod_mes['Consumo_Racao_Kg'].sum()
aves_vivas = qtd_aves_inicial - total_mortalidade

custo_por_ovo = custos / total_ovos if total_ovos > 0 else 0
custo_por_ave = custos / aves_vivas if aves_vivas > 0 else 0
mortalidade_perc = (total_mortalidade / qtd_aves_inicial * 100) if qtd_aves_inicial > 0 else 0
postura_perc = (total_ovos / (aves_vivas * 30) * 100) if aves_vivas > 0 else 0 # 30 dias

# MÉTRICAS FINANCEIRAS
st.subheader("📊 Resumo Financeiro")
col1, col2, col3 = st.columns(3)
col1.metric("Receita Total", f"R$ {receitas:,.2f}")
col2.metric("Custos", f"R$ {custos:,.2f}")
col3.metric("Despesas", f"R$ {despesas:,.2f}")
col4, col5, col6 = st.columns(3)
col4.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}")
col5.metric("Margem Líquida", f"{margem:.1f}%")
col6.metric("Custo por Ovo", f"R$ {custo_por_ovo:.3f}")

# MÉTRICAS ZOOTÉCNICAS
st.subheader("🐔 Indicadores de Produção")
col7, col8, col9 = st.columns(3)
col7.metric("Total de Ovos", f"{total_ovos:,.0f}")
col8.metric("Aves Vivas", f"{aves_vivas:,.0f}")
col9.metric("Mortalidade", f"{mortalidade_perc:.2f}%")
col10, col11, col12 = st.columns(3)
col10.metric("Consumo Ração", f"{total_racao:,.1f} Kg")
col11.metric("Custo por Ave", f"R$ {custo_por_ave:.2f}")
col12.metric("% Postura Mês", f"{postura_perc:.1f}%")

# GRÁFICOS
c1, c2 = st.columns(2)
with c1:
    st.subheader("Financeiro por Categoria")
    if not df_mov_filtrado.empty:
        fig = px.bar(df_mov_filtrado, x='Categoria', y='Valor', color='Tipo',
                     barmode='group', text_auto='.2s',
                     color_discrete_map={'Entrada':'#2ECC71', 'Saida':'#E74C3C', 'Saída':'#E74C3C'})
        fig.update_layout(yaxis_title="Valor (R$)", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    st.subheader("Evolução da Produção")
    if not df_prod_mes.empty:
        fig2 = px.line(df_prod_mes.sort_values('Data'), x='Data', y='Qtd_Ovos', markers=True,
                       title="Ovos por Dia")
        st.plotly_chart(fig2, use_container_width=True)

# TABELAS
with st.expander("Ver Lançamentos Financeiros"):
    st.dataframe(df_mov_filtrado, use_container_width=True, hide_index=True)
with st.expander("Ver Dados de Produção"):
    st.dataframe(df_prod_mes, use_container_width=True, hide_index=True)
