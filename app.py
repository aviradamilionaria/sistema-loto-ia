import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import re
from io import StringIO

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(
    page_title="LotoQuant | PRO V6.3 (HEDGE REAL)",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #050505; color: #e0e0e0; }
    .stButton>button { 
        background: linear-gradient(180deg, #00ff88 0%, #00b360 100%);
        color: #000; border: none; border-radius: 6px;
        font-weight: 900; font-size: 24px; height: 75px; width: 100%;
        text-transform: uppercase; box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);
    }
    .stButton>button:hover { transform: scale(1.01); }
    .game-card { background: #0f1216; border: 1px solid #1f242d; border-radius: 12px; padding: 20px; margin-bottom: 25px; }
    .ai-box { background-color: #1c2128; border-left: 5px solid #a371f7; padding: 15px; margin: 15px 0; border-radius: 4px; color: #d0d7de; font-family: sans-serif; font-size: 14px; }
    .numbers-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top:10px;}
    .number-box { background: #0d1117; border: 2px solid #30363d; color: #fff; border-radius: 50%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; }
    .fixa { border-color: #a371f7 !important; color: #a371f7 !important; }
    .repetida { border-color: #3fb950 !important; color: #3fb950 !important; }
    .proibida { text-decoration: line-through; color: #ff4b4b; } /* Estilo para explicar exclusão */
</style>
""", unsafe_allow_html=True)

# --- 2. DADOS ---
@st.cache_data(ttl=300)
def baixar_dados_live():
    FONTES = [
        "https://raw.githubusercontent.com/guilhermeasn/loteria.json/master/data/lotofacil.json", 
        "https://loteriascaixa-api.herokuapp.com/api/lotofacil",
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    ]
    for url in FONTES:
        try:
            response = requests.get(url, timeout=10, verify=False)
            if response.status_code == 200:
                dados = response.json()
                lista = []
                for jogo in dados:
                    dezenas = jogo.get('dezenas') or jogo.get('listaDezenas') or []
                    dezenas = [int(x) for x in dezenas]
                    if len(dezenas) == 15:
                        lista.append({'Concurso': jogo['concurso'], 'Dezenas': dezenas})
                if lista:
                    return pd.DataFrame(lista).sort_values('Concurso').reset_index(drop=True)
        except: continue
    return None

# --- 3. CÁLCULOS ---
def analisar_ciclo(df):
    todos = set(range(1, 26))
    acumulado = set()
    for i in range(len(df)-1, -1, -1):
        acumulado.update(set(df.iloc[i]['Dezenas']))
        if len(acumulado) == 25:
            novo = set()
            for j in range(i+1, len(df)): novo.update(set(df.iloc[j]['Dezenas']))
            return sorted(list(todos - novo))
    return []

def calcular_rsi(df):
    cols = pd.DataFrame(0, index=df.index, columns=[f'N{i}' for i in range(1,26)])
    for idx, row in df.iterrows():
        for d in row['Dezenas']: cols.at[idx, f'N{d}'] = 1
    stats = []
    for i in range(1, 26):
        rsi = ta.momentum.rsi(cols[f'N{i}'], window=14).iloc[-1]
        stats.append({'Bola': i, 'RSI': rsi})
    return pd.DataFrame(stats)

# --- 4. GERADOR INTELIGENTE COM CONTRA-CICLO ---
def gerar_jogos(df_stats, ultimas, ciclo):
    jogos = []
    quentes = df_stats.sort_values('RSI', ascending=False).head(12)['Bola'].tolist()
    frios = df_stats.sort_values('RSI', ascending=True).head(8)['Bola'].tolist()
    neutros = [x for x in range(1,26) if x not in quentes and x not in frios]
    
    # --- JOGO 1: APOSTA NO CICLO (LÓGICA) ---
    base1 = list(ciclo)
    usou_ciclo = list(ciclo)
    fortes = [x for x in quentes if x in ultimas and x not in base1]
    base1 += fortes[:6]
    while len(base1) < 15: base1.append([x for x in (quentes+neutros) if x not in base1][0])
    
    if usou_ciclo:
        txt1 = f"🎯 <b>MOTIVO:</b> APOSTA A FAVOR DO CICLO. Fixei <b>{usou_ciclo}</b> pois a estatística diz que devem sair hoje."
    else:
        txt1 = f"🎯 <b>MOTIVO:</b> Ciclo fechado. Segui a lógica pura dos números mais fortes."
        
    jogos.append({"Titulo": "JOGO 1: SNIPER (LÓGICA)", "Numeros": sorted(base1[:15]), "Razao": txt1, "Tipo": "Principal"})
    
    # --- JOGO 2: TENDÊNCIA (MISTO) ---
    # Tenta usar o ciclo, mas prioriza força RSI.
    base2 = quentes[:10] + neutros[:5]
    # Se sobrar espaço e tiver ciclo, coloca
    for c in ciclo:
        if c not in base2 and len(base2) < 15: base2.append(c)
    
    while len(base2) < 15: base2.append([x for x in range(1,26) if x not in base2][0])
    
    txt2 = f"🌊 <b>MOTIVO:</b> Surfista de Tendência. Priorizei números com RSI alto (Quentes), independente do atraso."
    jogos.append({"Titulo": "JOGO 2: TENDÊNCIA", "Numeros": sorted(base2[:15]), "Razao": txt2, "Tipo": "Ataque"})
    
    # --- JOGO 3: HEDGE REAL (CONTRA O CICLO) ---
    # AQUI ESTÁ A MUDANÇA: PROIBIR OS NÚMEROS DO CICLO
    base3 = []
    
    # Lista de proibidos (Números do Ciclo)
    proibidos = ciclo
    
    # Pega Frios e Neutros que NÃO ESTÃO no ciclo
    pool_seguro = [x for x in (frios + neutros + quentes) if x not in proibidos]
    
    # Monta o jogo só com quem SOBROU (aposta na falha do ciclo)
    base3 = pool_seguro[:15]
    
    # Se faltar número (caso raro onde o ciclo é enorme), completa com o que tem
    if len(base3) < 15:
        falta = 15 - len(base3)
        base3 += proibidos[:falta] # Só usa se não tiver opção
        txt_exclusao = "Tentei excluir o ciclo, mas faltaram números."
    else:
        txt_exclusao = f"🚫 <b>PROIBI AS DEZENAS {proibidos}.</b>"

    txt3 = f"🛡️ <b>MOTIVO:</b> HEDGE REAL (CONTRA-CICLO). {txt_exclusao}<br>Se o número do ciclo (ex: 16) falhar de novo, este é o único jogo que vai premiar."
    jogos.append({"Titulo": "JOGO 3: PROTEÇÃO TOTAL", "Numeros": sorted(base3[:15]), "Razao": txt3, "Tipo": "Defesa"})
    
    return jogos

# --- 5. INTERFACE ---
st.sidebar.markdown("## 🧮 CARTEIRA DIGITAL")
uploaded_file = st.sidebar.file_uploader("📂 Carregar Arquivo", type="txt")
manual_input = st.sidebar.text_area("Ou digite (Ex: 01 02...):", height=80)

with st.spinner('Calculando Hedge de Proteção...'):
    df = baixar_dados_live()

if df is not None:
    ult = df.iloc[-1]
    dezenas_ult = ult['Dezenas']
    
    # CONFERIDOR
    jogos_check = []
    if uploaded_file:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        for linha in stringio:
            nums = [int(n) for n in re.findall(r'\d+', linha)][:15]
            if len(nums) == 15: jogos_check.append(nums)
    elif manual_input:
        raw = [int(n) for n in re.findall(r'\d+', manual_input)]
        for i in range(0, len(raw), 15):
            if len(raw[i:i+15]) == 15: jogos_check.append(raw[i:i+15])
            
    if jogos_check:
        st.sidebar.markdown(f"**RESULTADO ({ult['Concurso']})**")
        total = 0
        for i, jogo in enumerate(jogos_check):
            acertos = len(set(jogo) & set(dezenas_ult))
            premio = 0
            if acertos == 11: premio=6
            if acertos == 12: premio=12
            if acertos >= 13: premio=30
            total += premio
            cor = "#00ff88" if acertos >= 11 else "#30363d"
            st.sidebar.markdown(f"<div style='border-left:4px solid {cor}; padding:5px; margin-bottom:5px;'>Jogo {i+1}: <b>{acertos} pts</b></div>", unsafe_allow_html=True)
        if total > 0: st.sidebar.success(f"💰 PRÊMIO: R$ {total},00")
        else: st.sidebar.warning("Sem prêmio.")

    # TELA PRINCIPAL
    st.title("🦅 LOTOQUANT | PRO V6.3")
    st.caption(f"Concurso Atual: {ult['Concurso']} | Modo Hedge Ativado")
    
    ciclo = analisar_ciclo(df)
    if ciclo: st.warning(f"⚠️ CICLO ABERTO: {ciclo}")
    else: st.success("✅ Ciclo Fechado.")
        
    if st.button("🚀 GERAR ESTRATÉGIA HEDGE"):
        stats = calcular_rsi(df)
        jogos = gerar_jogos(stats, dezenas_ult, ciclo)
        
        txt_out = f"--- CONCURSO {ult['Concurso']+1} ---\n\n"
        
        for jogo in jogos:
            nums = jogo['Numeros']
            txt_out += f"{jogo['Titulo']}: {nums}\n"
            rep = len(set(nums) & set(dezenas_ult))
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <h3 style='color:#00ff88'>{jogo['Titulo']}</h3>
                    <div class='ai-box'>{jogo['Razao']}</div>
                    <div style='font-size:12px; color:#8b949e'>
                        REPETIDAS: <b style='color:#fff'>{rep}</b> | SOMA: <b style='color:#fff'>{sum(nums)}</b>
                    </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(5)
                html_bolas = ""
                for n in nums:
                    css = "fria"
                    if n in ciclo: css = "fixa"
                    elif n in dezenas_ult: css = "repetida"
                    html_bolas += f"<div class='number-box {css}'>{n:02d}</div>"
                st.markdown(f"<div class='numbers-grid'>{html_bolas}</div></div>", unsafe_allow_html=True)
        
        st.download_button("💾 SALVAR JOGOS", data=txt_out, file_name="jogos.txt")

else:
    st.error("Erro ao conectar. Tente recarregar.")