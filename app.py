import os
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime

# CONFIGURA AQUI
TOKEN = "SEU_TOKEN_AQUI" # Troca pelo token do @BotFather
SEU_TELEGRAM_ID = 1162972058 # Já tá o seu
SHEET_NAME = "DRE-Granja-Dados"
HEADERS_DIARIO = ['Data', 'Ovos_Coletados', 'Mortalidade', 'Consumo_Racao_Kg', 'Receita_Venda_Ovos', 'Custos_Dia', 'Despesas_Dia', 'Observacoes']
HEADERS_CONFIG = ['Data_Alojamento', 'Idade_Inicial_Semanas', 'Qtd_Aves_Inicial', 'Preco_Racao_Kg']

def connect_gsheet():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(eval(os.environ["GCP_CREDS"]), scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)

def to_numeric_br(val):
    return pd.to_numeric(str(val).replace(',', '.'), errors='coerce')

def check_auth(update: Update):
    if update.effective_user.id!= SEU_TELEGRAM_ID:
        return False
    return True

def calc_resumo_dia(df_diario, df_config):
    if df_diario.empty or df_config.empty: return None
    preco_racao = to_numeric_br(df_config['Preco_Racao_Kg'].iloc[-1])
    qtd_aves_ini = int(to_numeric_br(df_config['Qtd_Aves_Inicial'].iloc[-1]))

    df = df_diario.copy()
    for col in ['Ovos_Coletados', 'Mortalidade', 'Consumo_Racao_Kg', 'Receita_Venda_Ovos', 'Custos_Dia', 'Despesas_Dia']:
        df[col] = df[col].apply(to_numeric_br).fillna(0)

    df['Aves_Vivas'] = qtd_aves_ini - df['Mortalidade'].cumsum()
    df['Custo_Racao'] = df['Consumo_Racao_Kg'] * preco_racao
    df['Custo_Total'] = df['Custos_Dia'] + df['Custo_Racao']

    ultima = df.iloc[-1]
    postura = (ultima['Ovos_Coletados'] / ultima['Aves_Vivas'] * 100) if ultima['Aves_Vivas'] > 0 else 0
    conversao = (ultima['Consumo_Racao_Kg'] / (ultima['Ovos_Coletados'] / 12)) if ultima['Ovos_Coletados'] > 0 else 0
    lucro = ultima['Receita_Venda_Ovos'] - ultima['Custo_Total'] - ultima['Despesas_Dia']

    alerta = ""
    if len(df) >= 2:
        postura_ontem = (df.iloc[-2]['Ovos_Coletados'] / (qtd_aves_ini - df['Mortalidade'].cumsum().iloc[-2]) * 100)
        if postura_ontem - postura > 5:
            alerta = f"\n⚠️ ALERTA: Queda de {postura_ontem - postura:.1f}% na postura!"
    if conversao > 2.6:
        alerta += f"\n⚠️ Conversão {conversao:.2f} Kg/Dz acima da meta 2.6"

    return f"Ovos: {int(ultima['Ovos_Coletados'])} | Postura: {postura:.1f}%\nCusto Ração: R$ {ultima['Custo_Racao']:.2f}\nCusto Total: R$ {ultima['Custo_Total']:.2f}\nLucro do Dia: R$ {lucro:.2f}{alerta}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update): return
    await update.message.reply_text("🐔 DRE Granja Bot online!\n\n/lancar ovos mort racao receita custos despesas obs\n/dre - Resumo total\n/postura - Últimos 7 dias\n/config - Ver lote\n/ajuda")

async def lancar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update):
        await update.message.reply_text("Acesso negado.")
        return
    try:
        args = context.args
        if len(args) < 7: raise ValueError("Faltam dados")
        ovos, mort, racao, receita, custos, despesas = map(lambda x: x.replace(',', '.'), args[:6])
        obs = " ".join(args[6:])
        data = datetime.now().strftime('%Y-%m-%d')

        ss = connect_gsheet()
        ws = ss.worksheet('DIARIO')
        ws.append_row([data, ovos, mort, racao, receita, custos, despesas, obs])

        df_d = pd.DataFrame(ws.get_all_records())
        df_c = pd.DataFrame(ss.worksheet('CONFIG').get_all_records())
        resumo = calc_resumo_dia(df_d, df_c)

        await update.message.reply_text(f"✅ Lançamento salvo {datetime.now().strftime('%d/%m/%Y')}\n\n{resumo}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}\nFormato: /lancar 684 2 165.8 800 200 0 texto")

async def dre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update): return
    ss = connect_gsheet()
    df_d = pd.DataFrame(ss.worksheet('DIARIO').get_all_records())
    df_c = pd.DataFrame(ss.worksheet('CONFIG').get_all_records())
    if df_d.empty:
        await update.message.reply_text("Sem lançamentos ainda.")
        return

    preco_racao = to_numeric_br(df_c['Preco_Racao_Kg'].iloc[-1])
    for col in ['Ovos_Coletados', 'Consumo_Racao_Kg', 'Receita_Venda_Ovos', 'Custos_Dia', 'Despesas_Dia']:
        df_d[col] = df_d[col].apply(to_numeric_br).fillna(0)

    rec = df_d['Receita_Venda_Ovos'].sum()
    cus_racao = (df_d['Consumo_Racao_Kg'] * preco_racao).sum()
    cus_total = cus_racao + df_d['Custos_Dia'].sum()
    desp = df_d['Despesas_Dia'].sum()
    lucro = rec - cus_total - desp
    margem = (lucro / rec * 100) if rec > 0 else 0

    await update.message.reply_text(f"📊 DRE TOTAL\n\nReceita: R$ {rec:.2f}\nCustos: R$ {cus_total:.2f}\n- Ração: R$ {cus_racao:.2f}\nDespesas: R$ {desp:.2f}\nLucro: R$ {lucro:.2f}\nMargem: {margem:.1f}%")

async def postura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update): return
    ss = connect_gsheet()
    df_d = pd.DataFrame(ss.worksheet('DIARIO').get_all_records())
    df_c = pd.DataFrame(ss.worksheet('CONFIG').get_all_records())
    if df_d.empty:
        await update.message.reply_text("Sem lançamentos.")
        return

    qtd_aves = int(to_numeric_br(df_c['Qtd_Aves_Inicial'].iloc[-1]))
    df_d['Ovos_Coletados'] = df_d['Ovos_Coletados'].apply(to_numeric_br)
    df_d['Mortalidade'] = df_d['Mortalidade'].apply(to_numeric_br)
    df_d['Aves_Vivas'] = qtd_aves - df_d['Mortalidade'].cumsum()
    df_d['Postura'] = (df_d['Ovos_Coletados'] / df_d['Aves_Vivas'] * 100).fillna(0)

    ult7 = df_d.tail(7)
    texto = "📈 Postura 7 dias:\n" + "\n".join([f"{row['Data']}: {row['Postura']:.1f}%" for _, row in ult7.iterrows()])
    await update.message.reply_text(texto)

async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update): return
    ss = connect_gsheet()
    df_c = pd.DataFrame(ss.worksheet('CONFIG').get_all_records())
    if df_c.empty:
        await update.message.reply_text("CONFIG vazia.")
        return
    c = df_c.iloc[-1]
    await update.message.reply_text(f"⚙️ LOTE ATUAL\n\nData: {c['Data_Alojamento']}\nIdade Inicial: {c['Idade_Inicial_Semanas']} sem\nAves Iniciais: {c['Qtd_Aves_Inicial']}\nPreço Ração: R$ {c['Preco_Racao_Kg']}/Kg")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", start))
    app.add_handler(CommandHandler("lancar", lancar))
    app.add_handler(CommandHandler("dre", dre))
    app.add_handler(CommandHandler("postura", postura))
    app.add_handler(CommandHandler("config", config))
    print("Bot rodando...")
    app.run_polling()
