import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
from fpdf import FPDF
import io

# --- CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="DRE Avícola V2.2", page_icon="🐔", layout="wide")

SHEET_NAME = "DRE-Granja-Dados"
HEADERS_DIARIO = ['Data', 'Ovos_Coletados', 'Mortalidade', 'Consumo_Racao_Kg', 'Receita_Venda_Ovos', 'Custos_Dia', 'Despesas_Dia', 'Observacoes']
HEADERS_CONFIG = ['Data_Alojamento', 'Idade_Inicial_Semanas', 'Qtd_Aves_Inicial', 'Preco_Racao_Kg']

# --- CONEXÃO COM GOOGLE SHEETS ---
@st.cache_resource
def connect_to_gsheet():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME)
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        st.stop()

spreadsheet = connect_to_gsheet()

# --- FUNÇÕES AUXILIARES ---
def normalize_header(header):
    return str(header).strip().lower().replace(' ', '_').replace('ç','c').replace('ã','a').replace('õ','o')

def load_sheet_as_df(worksheet_name, headers):
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Normaliza cabeçalhos da planilha e os esperados
        df.columns = [normalize_header(col) for col in df.columns]
        headers_norm = {normalize_header(h): h for h in headers}

        # Renomeia colunas pra padrão do código
        df = df.rename(columns={col: headers_norm[col] for col in df.columns if col in headers_norm})

        # Garante que todas as colunas existam
        for col in headers:
            if col not in df.columns:
                df[col] = None
        return df[headers]
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols=len(headers))
        worksheet.append_row(headers)
        return pd.DataFrame(columns=headers)
    except Exception as e:
        st.error(f"Erro ao carregar aba {worksheet_name}: {e}")
        return pd.DataFrame(columns=headers)

def save_to_gsheet(df, worksheet_name):
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
        df_str = df.fillna('').astype(str)
        worksheet.update([df_str.columns.values.tolist()] + df_str.values.tolist())
    except Exception as e:
        st.error(f"Erro ao salvar na aba {worksheet_name}: {e}")

def append_row_to_gsheet(data_row, worksheet_name):
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.append_row(data_row)
    except Exception as e:
        st.error(f"Erro ao adicionar linha na aba {worksheet_name}: {e}")

# --- CARREGAR DADOS ---
df_diario = load_sheet_as_df('DIARIO', HEADERS_DIARIO)
df_config = load_sheet_as_df('CONFIG', HEADERS_CONFIG)

# --- PROCESSAR CONFIG ---
qtd_aves_inicial = 0
preco_racao_kg = 0.0
data_alojamento = date.today()
idade_inicial_semanas = 0

if not df_config.empty:
    if 'Qtd_Aves_Inicial' in df_config.columns:
        qtd_aves_inicial = int(pd.to_numeric(df_config['Qtd_Aves_Inicial'], errors='coerce').fillna(0).iloc[-1])

    if 'Preco_Racao_Kg' in df_config.columns:
        preco_racao_kg = float(pd.to_numeric(df_config['Preco_Racao_Kg'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0).iloc[-1])

    if 'Data_Alojamento' in df_config.columns:
        try:
            data_alojamento = pd.to_datetime(df_config['Data_Alojamento'].iloc[-1]).date()
        except:
            data_alojamento = date.today()

    if 'Idade_Inicial_Semanas' in df_config.columns:
        idade_inicial_semanas = int(pd.to_numeric(df_config['Idade_Inicial_Semanas'], errors='coerce').fillna(0).iloc[-1])

# --- PROCESSAR DIÁRIO ---
if not df_diario.empty:
    df_diario['Data'] = pd.to_datetime(df_diario['Data'], errors='coerce')
    df_diario = df_diario.dropna(subset=['Data'])
    df_diario = df_diario.sort_values('Data')

    numeric_cols = ['Ovos_Coletados', 'Mortalidade', 'Consumo_Racao_Kg', 'Receita_Venda_Ovos', 'Custos_Dia', 'Despesas_Dia']
    for col in numeric_cols:
        df_diario[col] = pd.to_numeric(df_diario[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

    df_diario['Aves_Vivas'] = qtd_aves_inicial - df_diario['Mortalidade'].cumsum()
    df_diario['%_Postura'] = (df_diario['Ovos_Coletados'] / df_diario['Aves_Vivas'] * 100).fillna(0)
    df_diario['Custo_Racao_Calculado'] = df_diario['Consumo_Racao_Kg'] * preco_racao_kg
    df_diario['Custo_Total_Dia'] = df_diario['Custos_Dia'] + df_diario['Custo_Racao_Calculado']

# --- SIDEBAR: LANÇAMENTO E CONFIG ---
with st.sidebar:
    st.header("📝 Lançamento Rápido")
    with st.form("form_lancamento", clear_on_submit=True):
        data_lanc = st.date_input("Data", value=date.today())
        ovos = st.number_input("Ovos Coletados", min_value=0, step=1)
        mort = st.number_input("Mortalidade", min_value=0, step=1)
        racao = st.number_input("Consumo Ração Kg", min_value=0.0, step=0.1, format="%.1f")
        receita = st.number_input("Receita Venda Ovos R$", min_value=0.0, step=0.01, format="%.2f")
        custos = st.number_input("Outros Custos R$", min_value=0.0, step=0.01, format="%.2f")
        despesas = st.number_input("Despesas R$", min_value=0.0, step=0.01, format="%.2f")
        obs = st.text_area("Observações")

        if st.form_submit_button("💾 Salvar Lançamento"):
            nova_linha = [
                data_lanc.strftime('%Y-%m-%d'),
                ovos, mort, racao, receita, custos, despesas, obs
            ]
            append_row_to_gsheet(nova_linha, 'DIARIO')
            st.success("Lançamento salvo!")
            st.rerun()

    st.divider()
    st.header("⚙️ Configurar Lote Inicial")
    with st.form("form_config"):
        data_aloj = st.date_input("Data Alojamento", value=data_alojamento)
        idade_ini = st.number_input("Idade Inicial Semanas", min_value=0, value=int(idade_inicial_semanas))
        qtd_aves = st.number_input("Qtd Aves Inicial", min_value=0, value=int(qtd_aves_inicial))
        preco_kg = st.number_input("Preço Ração R$/Kg", min_value=0.0, value=float(preco_racao_kg), step=0.01, format="%.2f")

        if st.form_submit_button("💾 Salvar Config"):
            df_nova_config = pd.DataFrame([[
                data_aloj.strftime('%Y-%m-%d'),
                idade_ini,
                qtd_aves,
                preco_kg
            ]], columns=HEADERS_CONFIG)
            save_to_gsheet(df_nova_config, 'CONFIG')
            st.success("Configuração salva!")
            st.rerun()

# --- DASHBOARD PRINCIPAL ---
st.title("🐔 DRE Avícola - Controle Financeiro")

if df_diario.empty:
    st.warning("Nenhum lançamento encontrado. Use a barra lateral para adicionar o primeiro registro.")
    st.stop()

# --- MÉTRICAS ---
receita_total = df_diario['Receita_Venda_Ovos'].sum()
custo_racao_total = df_diario['Custo_Racao_Calculado'].sum()
custos_outros_total = df_diario['Custos_Dia'].sum()
custos_total = custo_racao_total + custos_outros_total
despesas_total = df_diario['Despesas_Dia'].sum()
lucro_liquido = receita_total - custos_total - despesas_total
margem_liquida = (lucro_liquido / receita_total * 100) if receita_total > 0 else 0

total_ovos = df_diario['Ovos_Coletados'].sum()
custo_por_ovo = custos_total / total_ovos if total_ovos > 0 else 0

aves_vivas_atual = int(df_diario['Aves_Vivas'].iloc[-1]) if not df_diario.empty else qtd_aves_inicial
mortalidade_acum = df_diario['Mortalidade'].sum()
mortalidade_perc = (mortalidade_acum / qtd_aves_inicial * 100) if qtd_aves_inicial > 0 else 0

consumo_racao_total = df_diario['Consumo_Racao_Kg'].sum()
conversao_dz = (consumo_racao_total / (total_ovos / 12)) if total_ovos > 0 else 0
postura_media = df_diario['%_Postura'].mean()

# --- ALERTA DE QUEDA DE POSTURA ---
if len(df_diario) >= 2:
    postura_hoje = df_diario['%_Postura'].iloc[-1]
    postura_ontem = df_diario['%_Postura'].iloc[-2]
    queda = postura_ontem - postura_hoje
    if queda > 5:
        st.error(f"⚠️ ALERTA: Queda de {queda:.1f}% na postura vs dia anterior! Último: {postura_hoje:.1f}% | Anterior: {postura_ontem:.1f}%")

# --- RESUMO FINANCEIRO ---
st.subheader("📊 Resumo Financeiro")
col1, col2, col3 = st.columns(3)
col1.metric("Receita Total", f"R$ {receita_total:,.2f}")
col2.metric("Custos", f"R$ {custos_total:,.2f}", f"↑ Custo Ração: R$ {custo_racao_total:,.2f}")
col3.metric("Despesas", f"R$ {despesas_total:,.2f}")

col4, col5, col6 = st.columns(3)
col4.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}")
col5.metric("Margem Líquida", f"{margem_liquida:.1f}%")
col6.metric("Custo por Ovo", f"R$ {custo_por_ovo:.3f}")

# --- INDICADORES DE PRODUÇÃO ---
st.subheader("🐣 Indicadores de Produção")
col7, col8, col9 = st.columns(3)
col7.metric("Total de Ovos", f"{int(total_ovos):,}")
col8.metric("Aves Vivas", f"{aves_vivas_atual:,}")
col9.metric("Mortalidade", f"{mortalidade_perc:.2f}%")

col10, col11, col12 = st.columns(3)
col10.metric("Consumo Ração", f"{consumo_racao_total:,.1f} Kg")
col11.metric("Conversão / Dz", f"{conversao_dz:.2f} Kg")
col12.metric("% Postura", f"{postura_media:.1f}%")

# --- EXPORTAR PDF ---
def gerar_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "DRE Avícola - Resumo Financeiro", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)

    pdf.cell(0, 8, f"Data do Relatório: {date.today().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 8, f"Período: {df_diario['Data'].min().strftime('%d/%m/%Y')} a {df_diario['Data'].max().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Resumo Financeiro", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Receita Total: R$ {receita_total:,.2f}", ln=True)
    pdf.cell(0, 8, f"Custos Totais: R$ {custos_total:,.2f}", ln=True)
    pdf.cell(0, 8, f" - Custo Ração: R$ {custo_racao_total:,.2f}", ln=True)
    pdf.cell(0, 8, f" - Outros Custos: R$ {custos_outros_total:,.2f}", ln=True)
    pdf.cell(0, 8, f"Despesas: R$ {despesas_total:,.2f}", ln=True)
    pdf.cell(0, 8, f"Lucro Líquido: R$ {lucro_liquido:,.2f}", ln=True)
    pdf.cell(0, 8, f"Margem Líquida: {margem_liquida:.1f}%", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Indicadores de Produção", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Total de Ovos: {int(total_ovos):,}", ln=True)
    pdf.cell(0, 8, f"Aves Vivas: {aves_vivas_atual:,}", ln=True)
    pdf.cell(0, 8, f"Mortalidade: {mortalidade_perc:.2f}%", ln=True)
    pdf.cell(0, 8, f"Consumo Ração: {consumo_racao_total:,.1f} Kg", ln=True)
    pdf.cell(0, 8, f"Conversão/Dz: {conversao_dz:.2f} Kg", ln=True)
    pdf.cell(0, 8, f"% Postura Média: {postura_media:.1f}%", ln=True)
    pdf.cell(0, 8, f"Custo por Ovo: R$ {custo_por_ovo:.3f}", ln=True)

    return bytes(pdf.output())

if st.button("📄 Exportar DRE em PDF"):
    pdf_bytes = gerar_pdf()
    st.download_button(
        label="⬇️ Baixar PDF",
        data=pdf_bytes,
        file_name=f"DRE_Granja_{date.today().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

# --- TABELA DE DADOS ---
st.divider()
st.subheader("📋 Lançamentos Diários")
df_display = df_diario.copy()
df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
st.dataframe(df_display, use_container_width=True, hide_index=True)
