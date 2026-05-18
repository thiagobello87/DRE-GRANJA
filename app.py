import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from io import BytesIO

st.set_page_config(page_title="DRE Granja", layout="wide", page_icon="🐔")
ARQUIVO_DADOS = "dados_granja.xlsx"

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        return pd.read_excel(ARQUIVO_DADOS, sheet_name=None)
    else:
        dados = {
            'LANÇAMENTO': pd.DataFrame(columns=['Data', 'Valor_Venda']),
            'CUSTOS': pd.DataFrame(columns=['Data', 'Valor_Racao']),
            'CONFIG': pd.DataFrame([{'Data_Alojamento': None, 'Custo_Fixo_Lote': 0}])
        }
        return dados

def salvar_dados(dados):
    with pd.ExcelWriter(ARQUIVO_DADOS, engine='openpyxl') as writer:
        for aba, df in dados.items():
            df.to_excel(writer, sheet_name=aba, index=False)

def colorir_margem(val):
    try:
        num = float(val.replace('%',''))
        if num >= 15: return 'background-color: #92D050'
        elif num >= 5: return 'background-color: #FFC000'
        else: return 'background-color: #FF0000; color: white'
    except: return ''

def calcular_dre(df_lanc, df_custos, data_aloj, custo_fixo_lote):
    df_lanc['MesAno'] = pd.to_datetime(df_lanc['Data']).dt.to_period('M')
    df_custos['MesAno'] = pd.to_datetime(df_custos['Data']).dt.to_period('M')
    receita_mes = df_lanc.groupby('MesAno')['Valor_Venda'].sum()
    racao_mes = df_custos.groupby('MesAno')['Valor_Racao'].sum()
    dre = pd.DataFrame({'Receita_Bruta': receita_mes, 'Custo_Racao': racao_mes}).fillna(0)
    dre.index = dre.index.astype(str)
    dre['Custo_Fixo'] = 0.0
    if pd.notna(data_aloj):
        mes_aloj = pd.to_datetime(data_aloj).to_period('M')
        if str(mes_aloj) in dre.index:
            dre.loc[str(mes_aloj), 'Custo_Fixo'] = custo_fixo_lote
    dre['Lucro_Liquido'] = dre['Receita_Bruta'] - dre['Custo_Racao'] - dre['Custo_Fixo']
    dre['Margem_%'] = (dre['Lucro_Liquido'] / dre['Receita_Bruta'] * 100).fillna(0)
    dre = dre.reset_index().rename(columns={'index': 'MesAno'})
    return dre

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='DRE')
        workbook = writer.book
        worksheet = writer.sheets['DRE']

        # Formato moeda pros valores
        for col in ['B', 'C', 'D', 'E']: # Receita, Custo_Rac, Custo_Fix, Lucro_Liq
            for row in range(2, len(df) + 2):
                worksheet[f'{col}{row}'].number_format = 'R$ #,##0.00'

        # Formato % pra margem
        for row in range(2, len(df) + 2):
            worksheet[f'F{row}'].number_format = '0.0%'
            worksheet[f'F{row}'].value = worksheet[f'F{row}'].value / 100 # Converte -400 pra -400%

    processed_data = output.getvalue()
    return processed_data

st.title("🐔 DRE Granja - Controle de Lote")
dados = carregar_dados()
tab1, tab2, tab3, tab4 = st.tabs(["📝 Lançar Dados", "📊 DRE Automática", "⚙️ Config Lote", "📥 Dados"])

with tab3:
    st.subheader("Configuração do Lote Atual")
    col1, col2 = st.columns(2)
    with col1:
        # Corrige erro quando a planilha está vazia
if 'CONFIG' in dados and not dados['CONFIG'].empty and 'Data_Alojamento' in dados['CONFIG'].columns:
    data_padrao = dados['CONFIG']['Data_Alojamento'].iloc[0]
else:
    from datetime import date
    data_padrao = date.today()

data_aloj = st.date_input("Data de Alojamento", value=data_padrao)
    with col2:
        custo_fixo = st.number_input("Custo Fixo Total do Lote R$", min_value=0.0, value=float(dados['CONFIG']['Custo_Fixo_Lote'].iloc[0]), step=100.0)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 Salvar Config"):
            dados['CONFIG'].loc[0] = [pd.to_datetime(data_aloj), custo_fixo]
            salvar_dados(dados)
            st.success("Config salva!")
            st.rerun()
    with col_b:
        if st.button("🔄 Encerrar Lote / Novo Lote", type="primary"):
            dados['LANÇAMENTO'] = pd.DataFrame(columns=['Data', 'Valor_Venda'])
            dados['CUSTOS'] = pd.DataFrame(columns=['Data', 'Valor_Racao'])
            dados['CONFIG'].loc[0] = [None, 0]
            salvar_dados(dados)
            st.success("Lote encerrado! Pronto para novo lote.")
            st.rerun()

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Lançar Receita")
        with st.form("form_receita"):
            data_rec = st.date_input("Data da Venda")
            valor_rec = st.number_input("Valor R$", min_value=0.0, step=10.0)
            if st.form_submit_button("Adicionar Receita"):
                novo = pd.DataFrame([{'Data': pd.to_datetime(data_rec), 'Valor_Venda': valor_rec}])
                dados['LANÇAMENTO'] = pd.concat([dados['LANÇAMENTO'], novo], ignore_index=True)
                salvar_dados(dados)
                st.success("Receita adicionada!")
                st.rerun()
    with col2:
        st.subheader("Lançar Custo Ração")
        with st.form("form_custo"):
            data_cus = st.date_input("Data do Custo")
            valor_cus = st.number_input("Valor Ração R$", min_value=0.0, step=10.0, key="cus")
            if st.form_submit_button("Adicionar Custo"):
                novo = pd.DataFrame([{'Data': pd.to_datetime(data_cus), 'Valor_Racao': valor_cus}])
                dados['CUSTOS'] = pd.concat([dados['CUSTOS'], novo], ignore_index=True)
                salvar_dados(dados)
                st.success("Custo adicionado!")
                st.rerun()

with tab2:
    st.subheader("DRE do Lote")
    if dados['LANÇAMENTO'].empty and dados['CUSTOS'].empty:
        st.info("Lance receitas e custos na aba 'Lançar Dados' para gerar a DRE.")
    else:
        dre = calcular_dre(dados['LANÇAMENTO'], dados['CUSTOS'],
                          dados['CONFIG']['Data_Alojamento'].iloc[0],
                          dados['CONFIG']['Custo_Fixo_Lote'].iloc[0])

        # CARDS DE RESUMO
        receita_total = dre['Receita_Bruta'].sum()
        lucro_total = dre['Lucro_Liquido'].sum()
        margem_media = (lucro_total / receita_total * 100) if receita_total > 0 else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("Receita Total Lote", f"R$ {receita_total:,.2f}")
        col2.metric("Lucro/Prejuízo Total", f"R$ {lucro_total:,.2f}")
        col3.metric("Margem Média Lote", f"{margem_media:.1f}%")

        st.divider()

        # TABELA COM FAROL
        dre_show = dre.copy()
        for col in ['Receita_Bruta', 'Custo_Racao', 'Custo_Fixo', 'Lucro_Liquido']:
            dre_show[col] = dre_show[col].apply(lambda x: f"R$ {x:,.2f}")
        dre_show['Margem_%'] = dre['Margem_%'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(dre_show.style.map(colorir_margem, subset=['Margem_%']), use_container_width=True, hide_index=True)

        # BOTÃO EXPORTAR
        excel_data = to_excel(dre)
        st.download_button(label="📥 Baixar DRE Excel", data=excel_data, file_name="DRE_Granja.xlsx")

        # GRÁFICO
        fig = px.bar(dre, x='MesAno', y=['Receita_Bruta', 'Custo_Racao', 'Lucro_Liquido'],
                     barmode='group', title='Receita x Custo x Lucro por Mês',
                     color_discrete_map={'Receita_Bruta':'#1f77b4', 'Custo_Racao':'#aec7e8', 'Lucro_Liquido':'#d62728'})
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Base de Dados Completa")
    st.write("**Receitas**")
    st.dataframe(dados['LANÇAMENTO'], use_container_width=True)
    st.write("**Custos**")
    st.dataframe(dados['CUSTOS'], use_container_width=True)
