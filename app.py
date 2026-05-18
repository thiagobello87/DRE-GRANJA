import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="Sistema DRE - Granja", page_icon="🐔", layout="wide")
st.title("🐔 Sistema DRE - Granja")

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# CORREÇÃO DA PRIVATE_KEY PRA STREAMLIT
service_account_info = dict(st.secrets["gcp_service_account"])
service_account_info["private_key"] = service_account_info["private_key"].replace('\\n', '\n')

try:
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(st.secrets["private_gsheets_url"])
    sheet = spreadsheet.sheet1
    st.success("Conectado ao Google Sheets com sucesso!")
    
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)
    
    if df.empty:
        st.info("Planilha conectada, mas está vazia. Adicione dados na primeira aba.")
    else:
        st.subheader("Dados da Planilha")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao conectar com Google Sheets: {e}")
    st.stop()

# SEU CÓDIGO DO DRE COMEÇA AQUI
# Exemplo:
# if not df.empty:
#     st.subheader("Resumo DRE")
#     receita = df['Receita'].sum()
#     st.metric("Receita Total", f"R$ {receita:,.2f}")
