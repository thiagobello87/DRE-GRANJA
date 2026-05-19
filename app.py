import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="DRE Granja", layout="wide")

# CONEXÃO
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["SHEET_ID"])

# CARREGA DADOS
df_diario = pd.DataFrame(sheet.worksheet('DIARIO').get_all_records())
df_mov = pd.DataFrame(sheet.worksheet('MOVIMENTACOES').get_all_records())

# TRATA DADOS DIARIO
if not df_diario.empty:
    df_diario['Data'] = pd.to_datetime(df_diario['Data'], dayfirst=True, errors='coerce')
    df_diario = df_diario.sort_values('Data')
    ultima = df_diario.iloc[-1]
    # Calcula indicadores
    aves_vivas = 1000 - df_diario['Mortalidade'].sum() # Ajusta se tiver lote inicial
    perc_postura = (ultima['Ovos_Coletados'] / aves_vivas * 100) if aves_vivas > 0 else 0
    conv_dz = (ultima['Consumo_Racao_Kg'] / (ultima['Ovos_Coletados'] / 12)) if ultima['Ovos_Coletados'] > 0 else 0
else:
    ultima = {}
    aves_vivas = 0
    perc_postura = 0
    conv_dz = 0

# TRATA DADOS BOT
hoje = datetime.now().date()
if not df_mov.empty:
    df_mov['Data'] = pd.to_datetime(df_mov['Data'], dayfirst=True, errors='coerce')
    df_mov['Valor'] = pd.to_numeric(df_mov['Valor'], errors='coerce').fillna(0)
    mov_hoje = df_mov[df_mov['Data'].dt.date == hoje]
    receita_bot = mov_hoje[mov_hoje['Tipo'] == 'Venda']['Valor'].sum()
    despesa_bot = mov_hoje[mov_hoje['Tipo'] == 'Despesa']['Valor'].sum()
else:
    receita_bot = 0
    despesa_bot = 0

# SIDEBAR - LANÇAMENTO RÁPIDO
with st.sidebar:
    st.header("Lançamento Rápido")
    with st.form("form_diario"):
        data = st.date_input("Data", value=datetime.now())
        ovos = st.number_input("Ovos Coletados", min_value=0, step=1)
        mort = st.number_input("Mortalidade", min_value=0, step=1)
        racao = st.number_input("Consumo Ração Kg", min_value=0.0, step=0.1)
        receita = st.number_input("Receita Venda Ovos R$", min_value=0.0, step=0.01)
        custos = st.number_input("Outros Custos R$", min_value=0.0, step=0.01)
        despesas = st.number_input("Despesas R$", min_value=0.0, step=0.01)
        obs = st.text_input("Observações")

        if st.form_submit_button("Salvar"):
            sheet.worksheet('DIARIO').append_row([
                data.strftime('%d/%m/%Y'), ovos, mort, racao, receita, custos, despesas, obs
            ])
            st.success("Lançado!")
            st.rerun()

# DASHBOARD
st.title("DRE Granja - Dashboard")

if not df_diario.empty:
    receita_dia = float(ultima.get('Receita_Venda_Ovos', 0)) + receita_bot
    custos_dia = float(ultima.get('Custos_Dia', 0)) + float(ultima.get('Despesas_Dia', 0)) + despesa_bot
    saldo_dia = receita_dia - custos_dia

    col1, col2, col3 = st.columns(3)
    col1.metric("Receita Hoje", f"R$ {receita_dia:,.2f}", f"+ R$ {receita_bot:.2f} via bot")
    col2.metric("Custos Hoje", f"R$ {custos_dia:,.2f}", f"+ R$ {despesa_bot:.2f} via bot")
    col3.metric("Saldo Hoje", f"R$ {saldo_dia:,.2f}")

    st.divider()

    st.subheader("🐔 Indicadores de Produção")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Ovos", int(ultima.get('Ovos_Coletados', 0)))
    c2.metric("Aves Vivas", int(aves_vivas))
    c3.metric("Mortalidade Dia", int(ultima.get('Mortalidade', 0)))

    c4, c5, c6 = st.columns(3)
    c4.metric("Consumo Ração", f"{ultima.get('Consumo_Racao_Kg', 0)} Kg")
    c5.metric("Conversão / Dz", f"{conv_dz:.2f} Kg")
    c6.metric("% Postura", f"{perc_postura:.1f}%")

    st.divider()
    st.subheader("📋 Lançamentos Diários")
    st.dataframe(df_diario, use_container_width=True, hide_index=True)
else:
    st.warning("Sem dados na aba DIARIO. Use o bot /producao ou lance na sidebar.")
