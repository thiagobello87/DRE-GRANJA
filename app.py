import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="DRE Granja", page_icon="🐔", layout="wide")
st.title("🐔 Sistema DRE - Granja")

HEADERS_CONFIG = ['Data_Alojamento', 'Idade_Inicial_Semanas', 'Qtd_Aves_Inicial', 'Preco_Racao_Kg']
HEADERS_MOVIMENTACOES = ['Data', 'Descricao', 'Categoria', 'Tipo', 'Valor']
HEADERS_PRODUCAO = ['Data', 'Semana_Aves', 'Qtd_Ovos', 'Mortalidade', 'Consumo_Racao_Kg', 'Observacao']

# Curva padrão Hy-Line Brown - % Postura por Semana
CURVA_PADRAO = {
    18: 5, 19: 30, 20: 65, 21: 85, 22: 92, 23: 94, 24: 95, 25: 95, 26: 94,
    27: 93, 28: 92, 29: 91, 30: 90, 31: 89, 32: 88, 33: 87, 34: 86, 35: 85,
    36: 84, 37: 83, 38: 82, 39: 81, 40: 80, 41: 79, 42: 78, 43: 77, 44: 76,
    45: 75, 46: 74, 47: 73, 48: 72, 49: 71, 50: 70, 51: 69, 52: 68, 53: 67,
    54: 66, 55: 65, 56: 64, 57: 63, 58: 62, 59: 61, 60: 60, 61: 59, 62: 58,
    63: 57, 64: 56, 65: 55, 66: 54, 67: 53, 68: 52, 69: 51, 70: 50, 71: 49,
    72: 48, 73: 47, 74: 46, 75: 45, 76: 44, 77: 43, 78: 42, 79: 41, 80: 40
}

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
    sheets_info = {
        "CONFIG": HEADERS_CONFIG,
        "MOVIMENTACOES": HEADERS_MOVIMENTACOES,
        "PRODUCAO": HEADERS_PRODUCAO
    }
    dataframes = {}
    for sheet_name, headers in sheets_info.items():
        try:
            sh = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            sh = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
            sh.update('A1', [headers])

        if sh.row_count <= 1 or not sh.row_values(1):
            sh.clear()
            sh.update('A1', [headers])
            df = pd.DataFrame(columns=headers)
        else:
            df = pd.DataFrame(sh.get_all_records())
            df = df.reindex(columns=headers, fill_value=0)

        dataframes[sheet_name] = df
    return dataframes["CONFIG"], dataframes["MOVIMENTACOES"], dataframes["PRODUCAO"]

def append_row(sheet_name, row_data):
    spreadsheet = get_gsheet()
    sheet = spreadsheet.worksheet(sheet_name)
    sheet.append_row(row_data, value_input_option='USER_ENTERED')
    st.cache_data.clear()

def delete_row(sheet_name, row_index):
    spreadsheet = get_gsheet()
    sheet = spreadsheet.worksheet(sheet_name)
    sheet.delete_rows(row_index + 2)
    st.cache_data.clear()

def gerar_pdf_dre(mes, receitas, custos, despesas, lucro_liquido, margem, total_ovos, aves_vivas, postura_perc, conversao, mortalidade_perc, custo_racao):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(f"DRE GRANJA - {mes}", styles['Title']))
    elementos.append(Spacer(1, 12))

    dados_financeiro = [
        ['DRE FINANCEIRO', ''],
        ['Receita Total', f'R$ {receitas:,.2f}'],
        ['(-) Custos', f'R$ {custos:,.2f}'],
        [' - Custo Ração', f'R$ {custo_racao:,.2f}'],
        ['(=) Lucro Bruto', f'R$ {receitas - custos:,.2f}'],
        ['(-) Despesas', f'R$ {despesas:,.2f}'],
        ['(=) Lucro Líquido', f'R$ {lucro_liquido:,.2f}'],
        ['Margem Líquida', f'{margem:.1f}%']
    ]

    dados_producao = [
        ['INDICADORES DE PRODUÇÃO', ''],
        ['Total de Ovos', f'{total_ovos:,.0f}'],
        ['Aves Vivas', f'{aves_vivas:,.0f}'],
        ['% Postura', f'{postura_perc:.1f}%'],
        ['Conversão / Dz', f'{conversao:.2f} Kg'],
        ['Mortalidade', f'{mortalidade_perc:.2f}%']
    ]

    t1 = Table(dados_financeiro, colWidths=[250, 150])
    t2 = Table(dados_producao, colWidths=[250, 150])

    estilo = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    t1.setStyle(estilo)
    t2.setStyle(estilo)

    elementos.append(t1)
    elementos.append(Spacer(1, 24))
    elementos.append(t2)

    doc.build(elementos)
    buffer.seek(0)
    return buffer

try:
    df_config, df_mov, df_prod = load_data()
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

if not df_mov.empty:
    df_mov['Valor'] = pd.to_numeric(df_mov['Valor'], errors='coerce').fillna(0)
    df_mov['Data'] = pd.to_datetime(df_mov['Data'], dayfirst=True, errors='coerce')
    df_mov.dropna(subset=['Data'], inplace=True)
    for col in ['Descricao', 'Categoria', 'Tipo']:
        df_mov[col] = df_mov[col].astype(str).str.strip().str.title()
    df_mov['Mes'] = df_mov['Data'].dt.strftime('%Y-%m')

if not df_prod.empty:
    df_prod['Data'] = pd.to_datetime(df_prod['Data'], dayfirst=True, errors='coerce')
    df_prod.dropna(subset=['Data'], inplace=True)
    for col in ['Qtd_Ovos', 'Mortalidade', 'Consumo_Racao_Kg', 'Semana_Aves']:
        df_prod[col] = pd.to_numeric(df_prod[col], errors='coerce').fillna(0)
    # CORREÇÃO AUTOMÁTICA CORRIGIDA: Se ração > 200kg/dia, divide por 10
    mask = df_prod['Consumo_Racao_Kg'] > 200
    df_prod.loc[mask, 'Consumo_Racao_Kg'] = df_prod.loc[mask, 'Consumo_Racao_Kg'] / 10
    df_prod['Mes'] = df_prod['Data'].dt.strftime('%Y-%m')

qtd_aves_inicial = 0
preco_racao_kg = 0
if not df_config.empty:
    df_config['Qtd_Aves_Inicial'] = pd.to_numeric(df_config['Qtd_Aves_Inicial'], errors='coerce').fillna(0)
    df_config['Preco_Racao_Kg'] = pd.to_numeric(df_config.get('Preco_Racao_Kg', 0), errors='coerce').fillna(0)
    qtd_aves_inicial = df_config['Qtd_Aves_Inicial'].iloc[-1] if not df_config.empty else 0
    preco_racao_kg = df_config['Preco_Racao_Kg'].iloc[-1] if 'Preco_Racao_Kg' in df_config.columns else 0

meses_mov = df_mov['Mes'].unique() if not df_mov.empty else []
meses_prod = df_prod['Mes'].unique() if not df_prod.empty else []
meses_disponiveis = sorted(list(set(list(meses_mov) + list(meses_prod))), reverse=True)

st.sidebar.header("Filtros")
if meses_disponiveis:
    mes_selecionado = st.sidebar.selectbox("Selecione o Mês:", meses_disponiveis)
else:
    mes_selecionado = date.today().strftime('%Y-%m')
    st.sidebar.info("Sem dados ainda")

df_mov_filtrado = df_mov[df_mov['Mes'] == mes_selecionado] if not df_mov.empty else pd.DataFrame(columns=HEADERS_MOVIMENTACOES)
df_prod_mes = df_prod[df_prod['Mes'] == mes_selecionado] if not df_prod.empty else pd.DataFrame(columns=HEADERS_PRODUCAO)

st.sidebar.header("Lançamentos Rápidos")

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

with st.sidebar.expander("Configurar Lote Inicial"):
    with st.form("form_config", clear_on_submit=True):
        data_aloj = st.date_input("Data Alojamento")
        idade_ini = st.number_input("Idade Inicial em Semanas", min_value=1, step=1)
        qtd_aves = st.number_input("Qtd Aves Inicial", min_value=1, step=1)
        preco_racao = st.number_input("Preço Ração R$/Kg", min_value=0.0, format="%.2f", value=float(preco_racao_kg))
        if st.form_submit_button("Salvar Config"):
            nova_linha = [data_aloj.strftime('%d/%m/%Y'), idade_ini, qtd_aves, preco_racao]
            append_row("CONFIG", nova_linha)
            st.sidebar.success("Config salva!")
            st.rerun()

st.header(f"Dashboard - {mes_selecionado}")

receitas = df_mov_filtrado[df_mov_filtrado['Tipo'] == 'Entrada']['Valor'].sum()
custos_manual = df_mov_filtrado[(df_mov_filtrado['Tipo'].isin(['Saida', 'Saída'])) & (df_mov_filtrado['Categoria'] == 'Custo')]['Valor'].sum()
despesas = df_mov_filtrado[(df_mov_filtrado['Tipo'].isin(['Saida', 'Saída'])) & (df_mov_filtrado['Categoria'] == 'Despesa')]['Valor'].sum()

total_ovos = df_prod_mes['Qtd_Ovos'].sum()
total_mortalidade = df_prod_mes['Mortalidade'].sum()
total_racao = df_prod_mes['Consumo_Racao_Kg'].sum()
aves_vivas = qtd_aves_inicial - total_mortalidade

# CUSTO DE RAÇÃO AUTOMÁTICO
custo_racao = total_racao * preco_racao_kg
custos = custos_manual + custo_racao

lucro_bruto = receitas - custos
lucro_liquido = lucro_bruto - despesas
margem = (lucro_liquido / receitas * 100) if receitas > 0 else 0

custo_por_ovo = custos / total_ovos if total_ovos > 0 else 0
custo_por_ave = custos / aves_vivas if aves_vivas > 0 else 0
mortalidade_perc = (total_mortalidade / qtd_aves_inicial * 100) if qtd_aves_inicial > 0 else 0

dias_com_producao = df_prod_mes['Data'].nunique() if not df_prod_mes.empty else 0
postura_perc = (total_ovos / (aves_vivas * dias_com_producao) * 100) if aves_vivas > 0 and dias_com_producao > 0 else 0
conversao = (total_racao / (total_ovos / 12)) if total_ovos > 0 else 0

# ALERTA DE QUEDA DE POSTURA
if len(df_prod_mes) >= 2:
    df_prod_mes_sorted = df_prod_mes.sort_values('Data')
    df_prod_mes_sorted['Aves_Dia'] = qtd_aves_inicial - df_prod_mes_sorted['Mortalidade'].cumsum()
    df_prod_mes_sorted['Postura_Dia'] = (df_prod_mes_sorted['Qtd_Ovos'] / df_prod_mes_sorted['Aves_Dia']) * 100
    ultima_postura = df_prod_mes_sorted['Postura_Dia'].iloc[-1]
    penultima_postura = df_prod_mes_sorted['Postura_Dia'].iloc[-2]
    queda = penultima_postura - ultima_postura
    if queda > 5:
        st.error(f"⚠️ ALERTA: Queda de {queda:.1f}% na postura vs dia anterior! Último: {ultima_postura:.1f}% | Anterior: {penultima_postura:.1f}%")

st.subheader("📊 Resumo Financeiro")
col1, col2, col3 = st.columns(3)
col1.metric("Receita Total", f"R$ {receitas:,.2f}")
col2.metric("Custos", f"R$ {custos:,.2f}", f"Custo Ração: R$ {custo_racao:,.2f}")
col3.metric("Despesas", f"R$ {despesas:,.2f}")
col4, col5, col6 = st.columns(3)
col4.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}")
col5.metric("Margem Líquida", f"{margem:.1f}%")
col6.metric("Custo por Ovo", f"R$ {custo_por_ovo:.3f}")

st.subheader("🐔 Indicadores de Produção")
col7, col8, col9 = st.columns(3)
col7.metric("Total de Ovos", f"{total_ovos:,.0f}")
col8.metric("Aves Vivas", f"{aves_vivas:,.0f}")
col9.metric("Mortalidade", f"{mortalidade_perc:.2f}%")
col10, col11, col12 = st.columns(3)
col10.metric("Consumo Ração", f"{total_racao:,.1f} Kg")
col11.metric("Conversão / Dz", f"{conversao:.2f} Kg")
col12.metric("% Postura", f"{postura_perc:.1f}%")

# BOTÃO PDF
pdf_buffer = gerar_pdf_dre(mes_selecionado, receitas, custos, despesas, lucro_liquido, margem, total_ovos, aves_vivas, postura_perc, conversao, mortalidade_perc, custo_racao)
st.download_button(
    label="📄 Exportar DRE em PDF",
    data=pdf_buffer,
    file_name=f"DRE_Granja_{mes_selecionado}.pdf",
    mime="application/pdf"
)

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
    st.subheader("Curva de Postura: Real vs Padrão")
    if not df_prod_mes.empty:
        df_postura_dia = df_prod_mes.copy()
        df_postura_dia['Aves_Dia'] = qtd_aves_inicial - df_postura_dia['Mortalidade'].cumsum()
        df_postura_dia['Postura_Dia'] = (df_postura_dia['Qtd_Ovos'] / df_postura_dia['Aves_Dia']) * 100
        df_postura = df_postura_dia.groupby('Semana_Aves')['Postura_Dia'].mean().reset_index()

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_postura['Semana_Aves'], y=df_postura['Postura_Dia'],
                                  mode='lines+markers', name='% Postura Real', line=dict(color='#2ECC71', width=3)))

        # CURVA PADRÃO
        semanas_padrao = sorted(CURVA_PADRAO.keys())
        postura_padrao = [CURVA_PADRAO[s] for s in semanas_padrao]
        fig2.add_trace(go.Scatter(x=semanas_padrao, y=postura_padrao,
                                  mode='lines', name='Padrão Hy-Line', line=dict(color='red', dash='dash')))

        fig2.update_layout(yaxis_title="% Postura", xaxis_title="Semana das Aves",
                           title="% Postura Real vs Padrão da Linhagem")
        st.plotly_chart(fig2, use_container_width=True)

# GRÁFICO NOVO: PROJEÇÃO DO LOTE
st.subheader("Projeção de Lucro do Lote até Semana 80")
if not df_prod_mes.empty and postura_perc > 0:
    semana_atual = df_prod_mes['Semana_Aves'].max()
    semanas_futuras = list(range(int(semana_atual), 81))

    # Projeta ovos baseado na média de postura atual
    ovos_projetados = []
    aves_projetadas = aves_vivas
    for s in semanas_futuras:
        if s in CURVA_PADRAO:
            postura_esperada = postura_perc # usa a sua média atual
            ovos_dia = (aves_projetadas * postura_esperada / 100) * 7 # 7 dias
            ovos_projetados.append(ovos_dia)
            aves_projetadas = aves_projetadas * 0.999 # mortalidade 0.1% semana

    ovos_total_projetado = sum(ovos_projetados)
    preco_medio_ovo = receitas / total_ovos if total_ovos > 0 else 0.5
    receita_projetada = ovos_total_projetado * preco_medio_ovo
    custo_projetado = ovos_total_projetado * custo_por_ovo
    lucro_projetado = receita_projetada - custo_projetado

    col_proj1, col_proj2, col_proj3 = st.columns(3)
    col_proj1.metric("Ovos até Semana 80", f"{ovos_total_projetado:,.0f}")
    col_proj2.metric("Receita Projetada", f"R$ {receita_projetada:,.2f}")
    col_proj3.metric("Lucro Projetado", f"R$ {lucro_projetado:,.2f}")

with st.expander("Ver Lançamentos Financeiros"):
    st.dataframe(df_mov_filtrado, use_container_width=True, hide_index=True)
    if not df_mov_filtrado.empty:
        idx_del = st.number_input("Índice da linha pra deletar", min_value=0, max_value=len(df_mov_filtrado)-1, step=1)
        if st.button("Deletar Lançamento Financeiro"):
            delete_row("MOVIMENTACOES", df_mov.index[df_mov['Mes'] == mes_selecionado][idx_del])
            st.success("Deletado!")
            st.rerun()

with st.expander("Ver Dados de Produção"):
    st.dataframe(df_prod_mes, use_container_width=True, hide_index=True)
    if not df_prod_mes.empty:
        idx_del_prod = st.number_input("Índice da linha pra deletar", min_value=0, max_value=len(df_prod_mes)-1, step=1, key="del_prod")
        if st.button("Deletar Dado de Produção"):
            delete_row("PRODUCAO", df_prod.index[df_prod['Mes'] == mes_selecionado][idx_del_prod])
            st.success("Deletado!")
            st.rerun()
