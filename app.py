import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import re
from io import StringIO

# --- 1. CONFIGURAÇÃO (CORRIGIDA PARA EXIBIR BARRA LATERAL) ---
st.set_page_config(
    page_title="LotoQuant | GRAND MASTER V6.1",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded" # Garante que a barra lateral apareça
)

# --- 2. CSS LIMPO (PARA NÃO BUGAR TEXTO) ---
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #e0e0e0; }
    
    /* Botão Principal */
    .stButton>button { 
        background: linear-gradient(180deg, #00ff88 0%, #00b360 100%);
        color: #000; border: none; border-radius: 6px;
        font-weight: 900; font-size: 24px; height: 75px; width: 100%;
        text-transform: uppercase; box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);
    }
    .stButton>button:hover { transform: scale(1.01); }
    
    /* Card do Jogo */
    .game-card {
        background: #0f1216; border: 1px solid #1f242d;
        border-radius: 12px; padding: 20px; margin-bottom: 25px;
    }
    
    /* Texto da IA (Simplificado para não quebrar) */
    .ai-box {
        background-color: #1c2128; 
        border-left: 5px solid #a371f7;
        padding: 15px; 
        margin: 15px 0;
        border-radius: 4px;
        color: #d0d7de;
        font-family: sans-serif;
    }
    
    /* Grade de Bolas */
    .numbers-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top:10px;}
    .number-box { 
        background: #0d1117; border: 2px solid #30363d; 
        color: #fff; border-radius: 50%; aspect-ratio: 1;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; font-size: 18px;
    }
    
    /* Cores Especiais */
    .fixa { border-color: #a371f7 !important; color: #a371f7 !important; } /* Ciclo */
    .repetida { border-color: #3fb950 !important; color: #3fb950 !important; } /* Repetida */

</style>
""", unsafe_allow_html=True)

# --- 3. DADOS ---
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

# --- 4. CÁLCULOS ---
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

def gerar_jogos(df_stats, ultimas, ciclo):
    jogos = []
    quentes = df_stats.sort_values('RSI', ascending=False).head(12)['Bola'].tolist()
    frios = df_stats.sort_values('RSI', ascending=True).head(8)['Bola'].tolist()
    neutros = [x for x in range(1,26) if x not in quentes and x not in frios]
    
    # JOGO 1
    base1 = list(ciclo)
    txt1 = f"🎯 SNIPER: Ciclo Aberto. Fixei {ciclo}." if ciclo else "🎯 SNIPER: Modo Estatística Pura."
    base1 += [x for x in quentes if x in ultimas and x not in base1]
    while len(base1) < 15: base1.append([x for x in (quentes+neutros) if x not in base1][0])
    jogos.append({"Titulo": "JOGO 1: SNIPER", "Numeros": sorted(base1[:15]), "Razao": txt1, "Tipo": "Principal"})
    
    # JOGO 2
    base2 = quentes[:10] + neutros[:5]
    while len(base2) < 15: base2.append([x for x in range(1,26) if x not in base2][0])
    jogos.append({"Titulo": "JOGO 2: TENDÊNCIA", "Numeros": sorted(base2[:15]), "Razao": "🌊 SURFISTA: Focado apenas nos números quentes (RSI Alto).", "Tipo": "Ataque"})
    
    # JOGO 3
    base3 = frios[:7] + neutros[:6] + quentes[:2]
    jogos.append({"Titulo": "JOGO 3: PROTEÇÃO", "Numeros": sorted(base3[:15]), "Razao": "🛡️ HEDGE: Focado em zebras e números frios.", "Tipo": "Defesa"})
    
    return jogos

# --- 5. INTERFACE ---
# --- BARRA LATERAL (CONFERIDOR) ---
st.sidebar.markdown("## 🧮 CARTEIRA DIGITAL")
st.sidebar.info("Carregue o arquivo para conferir:")
uploaded_file = st.sidebar.file_uploader("📂 Carregar 'MeusJogos.txt'", type="txt")

# Modo Manual (Sempre visível como opção)
manual_input = st.sidebar.text_area("Ou digite (Ex: 01 02 03...):", height=80)

with st.spinner('Conectando...'):
    df = baixar_dados_live()

if df is not None:
    ult = df.iloc[-1]
    dezenas_ult = ult['Dezenas']
    
    # LÓGICA DO CONFERIDOR
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

    # --- TELA PRINCIPAL ---
    st.title("🦅 LOTOQUANT | V6.1")
    st.caption(f"Concurso Atual: {ult['Concurso']}")
    
    ciclo = analisar_ciclo(df)
    if ciclo:
        st.warning(f"⚠️ CICLO ABERTO: Faltam {ciclo}")
    else:
        st.success("✅ Ciclo Fechado.")
        
    if st.button("🚀 GERAR JOGOS"):
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