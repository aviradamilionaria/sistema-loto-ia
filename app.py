import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import re
from io import StringIO

# --- 1. CONFIGURAÇÃO ELITE (VISUAL CYBERPUNK/MILITAR) ---
st.set_page_config(
    page_title="LotoQuant | MASTER V5.2",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS AVANÇADO
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #e0e0e0; }
    
    /* Botão de Disparo Nuclear */
    .stButton>button { 
        background: linear-gradient(180deg, #00ff88 0%, #00b360 100%);
        color: #000; border: none; border-radius: 6px;
        font-weight: 900; font-size: 28px; height: 80px; width: 100%;
        text-transform: uppercase; box-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
        transition: all 0.2s;
    }
    .stButton>button:hover { transform: scale(1.01); box-shadow: 0 0 50px rgba(0, 255, 136, 0.6); }
    
    /* Card do Jogo */
    .game-card {
        background: #0f1216; border: 1px solid #1f242d;
        border-radius: 10px; padding: 20px; margin-bottom: 25px;
        position: relative;
    }
    .game-card h3 { color: #00ff88; margin-top: 0; font-family: 'Courier New', monospace; }
    
    /* Explicação da IA */
    .ai-reason {
        background: #161b22; border-left: 4px solid #a371f7;
        padding: 10px; font-size: 14px; color: #d0d7de; margin: 15px 0;
        font-family: sans-serif;
    }
    
    /* Ciclo Alert */
    .cycle-alert {
        background: #3fb95026; border: 1px solid #3fb950; color: #3fb950;
        padding: 15px; border-radius: 8px; text-align: center; font-weight: bold;
        margin-bottom: 20px; font-size: 18px;
    }
    
    /* Bolas */
    .numbers-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
    .number-box { 
        background: #0d1117; border: 2px solid #30363d; 
        color: #fff; border-radius: 50%; aspect-ratio: 1;
        display: flex; align-items: center; justify-content: center;
        font-weight: 900; font-size: 20px;
    }
    /* Destaques */
    .fixa { border-color: #a371f7 !important; color: #a371f7 !important; box-shadow: 0 0 10px rgba(163, 113, 247, 0.2); } /* Ciclo */
    .repetida { border-color: #3fb950 !important; color: #3fb950 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS BLINDADO (MULTI-FONTE) ---
@st.cache_data(ttl=300)
def baixar_dados_live():
    FONTES = [
        "https://raw.githubusercontent.com/guilhermeasn/loteria.json/master/data/lotofacil.json", 
        "https://loteriascaixa-api.herokuapp.com/api/lotofacil",
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in FONTES:
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
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

# --- 3. INTELIGÊNCIA DE CICLOS ---
def analisar_ciclo(df):
    todos_numeros = set(range(1, 26))
    acumulado = set()
    for i in range(len(df)-1, -1, -1):
        dezenas = set(df.iloc[i]['Dezenas'])
        acumulado.update(dezenas)
        if len(acumulado) == 25:
            novo_ciclo_numeros = set()
            for j in range(i+1, len(df)):
                novo_ciclo_numeros.update(set(df.iloc[j]['Dezenas']))
            faltam = todos_numeros - novo_ciclo_numeros
            return sorted(list(faltam))
    return []

# --- 4. MOTOR ESTATÍSTICO (RSI) ---
def calcular_rsi(df):
    cols_map = pd.DataFrame(0, index=df.index, columns=[f'N{i}' for i in range(1,26)])
    for idx, row in df.iterrows():
        for d in row['Dezenas']: cols_map.at[idx, f'N{d}'] = 1
    stats = []
    for i in range(1, 26):
        serie = cols_map[f'N{i}']
        rsi = ta.momentum.rsi(serie, window=14).iloc[-1]
        stats.append({'Bola': i, 'RSI': rsi})
    return pd.DataFrame(stats)

# --- 5. GERADOR HIERÁRQUICO ---
def gerar_jogos_elite(df_stats, ultimas_dezenas, dezenas_ciclo):
    jogos = []
    quentes = df_stats.sort_values('RSI', ascending=False).head(10)['Bola'].tolist()
    frios = df_stats.sort_values('RSI', ascending=True).head(8)['Bola'].tolist()
    neutros = [x for x in range(1,26) if x not in quentes and x not in frios]
    
    # JOGO 1: CICLO
    base_j1 = list(dezenas_ciclo)
    candidatos = [x for x in quentes if x in ultimas_dezenas and x not in base_j1]
    base_j1 += candidatos
    while len(base_j1) < 15:
        restante = [x for x in (quentes + neutros) if x not in base_j1]
        base_j1.append(restante[0])
    palpite1 = sorted(base_j1[:15])
    razao1 = f"<b>Estratégia:</b> Fechamento de Ciclo.<br>Fixei as dezenas <b>{dezenas_ciclo}</b> para fechar o ciclo. Base completada com repetidas fortes."
    jogos.append({"Titulo": "🦅 ELITE: CICLO MASTER", "Numeros": palpite1, "Razao": razao1})

    # JOGO 2: TENDÊNCIA
    base_j2 = quentes[:9] + neutros[:4]
    while len(base_j2) < 15:
        restante = [x for x in range(1,26) if x not in base_j2]
        base_j2.append(restante[0])
    palpite2 = sorted(base_j2[:15])
    razao2 = "<b>Estratégia:</b> Tendência Pura (RSI).<br>Foca apenas na força relativa dos números. Jogo para dias lógicos."
    jogos.append({"Titulo": "🔥 TENDÊNCIA ALTA", "Numeros": palpite2, "Razao": razao2})

    # JOGO 3: PROTEÇÃO
    base_j3 = frios[:6] + neutros[:5] + quentes[:4]
    palpite3 = sorted(base_j3[:15])
    razao3 = "<b>Estratégia:</b> Hedge (Proteção).<br>Captura as zebras e números atrasados caso a lógica falhe."
    jogos.append({"Titulo": "🛡️ ESCUDO (ZEBRA)", "Numeros": palpite3, "Razao": razao3})

    return jogos

# --- 6. INTERFACE ---
# BARRA LATERAL (CONFERIDOR INTELIGENTE)
st.sidebar.title("🧮 CARTEIRA")
st.sidebar.info("Amanhã, carregue o arquivo aqui para conferir sem digitar nada.")
uploaded_file = st.sidebar.file_uploader("📂 Carregar 'MeusJogos.txt'", type="txt")

# Modo Manual (Backup)
with st.sidebar.expander("Ou digite manualmente"):
    jogo_manual = st.text_area("Números:", height=100)

with st.spinner('Sincronizando banco de dados...'):
    df = baixar_dados_live()

if df is not None:
    ult_conc = df.iloc[-1]
    dezenas_ult = ult_conc['Dezenas']
    
    # --- LÓGICA DE CONFERÊNCIA AUTOMÁTICA ---
    jogos_para_conferir = []
    
    # 1. Se carregou arquivo
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        linhas = stringio.readlines()
        for linha in linhas:
            nums = re.findall(r'\d+', linha)
            if len(nums) >= 15:
                jogos_para_conferir.append([int(n) for n in nums[:15]])
                
    # 2. Se digitou manual
    elif jogo_manual:
        nums = re.findall(r'\d+', jogo_manual)
        if len(nums) >= 15:
            # Tenta quebrar em blocos de 15 se tiver colado tudo junto
            for i in range(0, len(nums), 15):
                bloco = nums[i:i+15]
                if len(bloco) == 15:
                    jogos_para_conferir.append([int(n) for n in bloco])

    # MOSTRAR RESULTADO DA CONFERÊNCIA
    if jogos_para_conferir:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### 🏆 RESULTADO ({ult_conc['Concurso']})")
        
        total_premio = 0
        for i, jogo in enumerate(jogos_para_conferir):
            acertos = len(set(jogo) & set(dezenas_ult))
            premio = 0
            cor = "gray"
            msg = "0"
            
            if acertos == 11: premio = 6; cor="orange"; msg="R$ 6,00"
            if acertos == 12: premio = 12; cor="yellow"; msg="R$ 12,00"
            if acertos == 13: premio = 30; cor="#00ff88"; msg="R$ 30,00"
            if acertos == 14: premio = 1500; cor="#00ff88"; msg="R$ 1.500+"
            if acertos == 15: premio = 2000000; cor="#00ff88"; msg="JACKPOT"
            
            total_premio += premio
            
            st.sidebar.markdown(f"""
            <div style='border:1px solid {cor}; padding:10px; border-radius:5px; margin-bottom:5px; font-size:14px;'>
                Jogo {i+1}: <b>{acertos} Acertos</b> <span style='float:right; color:{cor}'>{msg}</span>
            </div>
            """, unsafe_allow_html=True)
            
        if total_premio > 0:
            st.sidebar.success(f"💰 TOTAL A RECEBER: R$ {total_premio},00")
        else:
            st.sidebar.warning("Nenhum prêmio hoje.")

    # --- PAINEL PRINCIPAL ---
    st.title("🦅 LOTOQUANT | MASTER V5.2")
    st.markdown(f"**Concurso Atual:** {ult_conc['Concurso']} | **Status:** 🟢 Online")
    
    dezenas_ciclo = analisar_ciclo(df)
    if len(dezenas_ciclo) > 0:
        st.markdown(f"<div class='cycle-alert'>⚠️ ALERTA DE CICLO ABERTO: FALTAM {len(dezenas_ciclo)} NÚMEROS<br><span style='font-size:24px; color:#fff'>{dezenas_ciclo}</span></div>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Ciclo fechado. Novo ciclo iniciando.")

    if st.button("GERAR JOGOS DE ALTA PERFORMANCE"):
        stats = calcular_rsi(df)
        jogos = gerar_jogos_elite(stats, dezenas_ult, dezenas_ciclo)
        
        # Prepara texto para baixar
        texto_download = ""
        
        for jogo in jogos:
            nums = jogo['Numeros']
            texto_download += f"{jogo['Titulo']}: {nums}\n"
            
            # Cards
            repetidos = len(set(nums) & set(dezenas_ult))
            ciclo_presenca = len(set(nums) & set(dezenas_ciclo))
            with st.container():
                st.markdown(f"<div class='game-card'><div style='display:flex; justify-content:space-between; align-items:center'><h3>{jogo['Titulo']}</h3><div style='font-size:12px; color:#8b949e'>CICLO: <b style='color:#a371f7'>{ciclo_presenca}</b> | REP: <b style='color:#3fb950'>{repetidos}</b></div></div><div class='ai-reason'>{jogo['Razao']}</div>", unsafe_allow_html=True)
                cols = st.columns(5)
                html_bolas = ""
                for n in nums:
                    style_class = ""
                    if n in dezenas_ciclo: style_class = "fixa"
                    elif n in dezenas_ult: style_class = "repetida"
                    html_bolas += f"<div class='number-box {style_class}'>{n:02d}</div>"
                st.markdown(f"<div class='numbers-grid'>{html_bolas}</div></div>", unsafe_allow_html=True)
        
        # BOTÃO DE DOWNLOAD (SALVA VIDAS)
        st.markdown("---")
        st.download_button(
            label="💾 BAIXAR JOGOS (SALVAR PARA CONFERIR DEPOIS)",
            data=texto_download,
            file_name=f"Jogos_Concurso_{ult_conc['Concurso']+1}.txt",
            mime="text/plain",
            help="Clique aqui para salvar seus jogos. Amanhã, basta carregar esse arquivo no menu lateral para conferir."
        )

else:
    st.error("⚠️ Erro de conexão. Tente recarregar.")