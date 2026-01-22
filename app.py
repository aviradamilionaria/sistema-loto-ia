import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import re
from io import StringIO

# --- 1. CONFIGURAÇÃO GRAND MASTER (VISUAL ELITE) ---
st.set_page_config(
    page_title="LotoQuant | GRAND MASTER V6",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PROFISSIONAL
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #e0e0e0; }
    
    /* Botão Principal - Efeito Neon Pulsante */
    .stButton>button { 
        background: linear-gradient(180deg, #00ff88 0%, #00b360 100%);
        color: #000; border: none; border-radius: 6px;
        font-weight: 900; font-size: 26px; height: 80px; width: 100%;
        text-transform: uppercase; box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);
        transition: all 0.3s ease;
    }
    .stButton>button:hover { 
        transform: scale(1.02); 
        box-shadow: 0 0 40px rgba(0, 255, 136, 0.7);
    }
    
    /* Card do Jogo */
    .game-card {
        background: #0f1216; border: 1px solid #1f242d;
        border-radius: 12px; padding: 20px; margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .game-card h3 { color: #00ff88; margin: 0 0 10px 0; font-family: 'Courier New', monospace; letter-spacing: -1px; }
    
    /* Painel Técnico (HUD) */
    .hud-panel {
        display: flex; justify-content: space-between; background: #161b22;
        padding: 8px 15px; border-radius: 6px; margin-bottom: 15px;
        font-size: 13px; color: #8b949e; border: 1px solid #30363d;
    }
    .hud-value { color: #fff; font-weight: bold; margin-left: 5px; }
    
    /* Explicação da IA */
    .ai-reason {
        background: #1c2128; border-left: 4px solid #a371f7;
        padding: 12px; font-size: 14px; color: #d0d7de; margin-bottom: 15px;
        font-family: sans-serif; line-height: 1.5;
    }
    
    /* Alerta de Ciclo */
    .cycle-alert {
        background: linear-gradient(90deg, #3fb95026 0%, transparent 100%);
        border-left: 5px solid #3fb950; color: #3fb950;
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
    }
    
    /* Grade de Bolas */
    .numbers-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
    .number-box { 
        background: #0d1117; border: 2px solid #30363d; 
        color: #fff; border-radius: 50%; aspect-ratio: 1;
        display: flex; align-items: center; justify-content: center;
        font-weight: 900; font-size: 20px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }
    
    /* Classes de Destaque */
    .fixa { border-color: #a371f7 !important; color: #a371f7 !important; box-shadow: 0 0 15px rgba(163, 113, 247, 0.3); } /* Ciclo (Roxo) */
    .repetida { border-color: #3fb950 !important; color: #3fb950 !important; } /* Repetida (Verde) */
    .fria { border-color: #30363d !important; color: #8b949e !important; } /* Normal */

</style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE DADOS BLINDADO (3 FONTES) ---
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

# --- 3. CÉREBRO MATEMÁTICO ---
def analisar_ciclo(df):
    todos = set(range(1, 26))
    acumulado = set()
    for i in range(len(df)-1, -1, -1):
        acumulado.update(set(df.iloc[i]['Dezenas']))
        if len(acumulado) == 25:
            # Ciclo fechou aqui, pegar o que veio depois
            novo_ciclo = set()
            for j in range(i+1, len(df)): novo_ciclo.update(set(df.iloc[j]['Dezenas']))
            return sorted(list(todos - novo_ciclo))
    return []

def calcular_rsi(df):
    cols_map = pd.DataFrame(0, index=df.index, columns=[f'N{i}' for i in range(1,26)])
    for idx, row in df.iterrows():
        for d in row['Dezenas']: cols_map.at[idx, f'N{d}'] = 1
    stats = []
    for i in range(1, 26):
        rsi = ta.momentum.rsi(cols_map[f'N{i}'], window=14).iloc[-1]
        stats.append({'Bola': i, 'RSI': rsi})
    return pd.DataFrame(stats)

# --- 4. GERADOR DE GUERRA (HIERARQUIA V6) ---
def gerar_jogos_elite(df_stats, ultimas_dezenas, dezenas_ciclo):
    jogos = []
    quentes = df_stats.sort_values('RSI', ascending=False).head(12)['Bola'].tolist()
    frios = df_stats.sort_values('RSI', ascending=True).head(8)['Bola'].tolist()
    neutros = [x for x in range(1,26) if x not in quentes and x not in frios]
    
    # --- JOGO 1: SNIPER (CICLO + PADRÃO) ---
    base_j1 = list(dezenas_ciclo) # Fixa ciclo
    
    # Texto dinâmico da IA
    if len(dezenas_ciclo) > 0:
        txt_razao = f"🎯 <b>ESTRATÉGIA SNIPER:</b><br>O Ciclo está aberto. Fixei obrigatoriamente as dezenas <b>{dezenas_ciclo}</b> pois a estatística exige que elas saiam. Completei com as repetidas mais fortes."
    else:
        txt_razao = "🎯 <b>ESTRATÉGIA SNIPER:</b><br>O Ciclo fechou recentemente. Mudei para o modo 'Estatística Pura', focando em equilibrar Repetidas e Dezenas da Moldura."
    
    # Completa com Quentes que são Repetidas (Tendência de repetição)
    candidatos = [x for x in quentes if x in ultimas_dezenas and x not in base_j1]
    base_j1 += candidatos
    
    # Preenchimento inteligente (evita linha vazia)
    while len(base_j1) < 15:
        pool = [x for x in (quentes + neutros) if x not in base_j1]
        # Aqui poderíamos inserir lógica extra de linha, mas vamos confiar no RSI dos neutros
        base_j1.append(pool[0])
        
    jogos.append({
        "Titulo": "🦅 JOGO 1: CICLO SNIPER",
        "Numeros": sorted(base_j1[:15]),
        "Razao": txt_razao,
        "Tipo": "Principal"
    })

    # --- JOGO 2: TENDÊNCIA (O SURFISTA) ---
    # Foca 80% em RSI Alto. Ignora atrasos.
    base_j2 = quentes[:10] + neutros[:5]
    while len(base_j2) < 15:
        rest = [x for x in range(1,26) if x not in base_j2]
        base_j2.append(rest[0])
        
    jogos.append({
        "Titulo": "🔥 JOGO 2: TENDÊNCIA PURA",
        "Numeros": sorted(base_j2[:15]),
        "Razao": "<b>🌊 ESTRATÉGIA SURFISTA:</b><br>Ignorei os números atrasados. Este jogo aposta que o que está 'Quente' vai continuar saindo. É o jogo para quando a lógica prevalece.",
        "Tipo": "Ataque"
    })

    # --- JOGO 3: HEDGE (ZEBRA) ---
    # Pega Frios e Neutros. Evita os Top Quentes.
    base_j3 = frios[:7] + neutros[:6] + quentes[:2]
    jogos.append({
        "Titulo": "🛡️ JOGO 3: ESCUDO ZEBRA",
        "Numeros": sorted(base_j3[:15]),
        "Razao": "<b>🛡️ ESTRATÉGIA DE PROTEÇÃO:</b><br>Se o sorteio for uma loucura e quebrar a lógica do Ciclo, este jogo captura as zebras e números frios que ninguém jogou.",
        "Tipo": "Defesa"
    })

    return jogos

# --- 5. INTERFACE (FRONT-END) ---
# BARRA LATERAL - CARTEIRA
st.sidebar.markdown("## 🧮 CARTEIRA DIGITAL")
st.sidebar.info("Carregue o arquivo gerado ontem para conferir sem digitar.")
uploaded_file = st.sidebar.file_uploader("📂 Carregar Arquivo .txt", type="txt")
if not uploaded_file:
    with st.sidebar.expander("Ou digite manualmente"):
        manual_input = st.text_area("Ex: 01 02 03...", height=80)
else: manual_input = None

with st.spinner('Calibrando algoritmos de previsão...'):
    df = baixar_dados_live()

if df is not None:
    ult_conc = df.iloc[-1]
    dezenas_ult = ult_conc['Dezenas']
    
    # --- CONFERIDOR AUTOMÁTICO ---
    jogos_check = []
    if uploaded_file:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        for linha in stringio:
            nums = [int(n) for n in re.findall(r'\d+', linha)][:15]
            if len(nums) == 15: jogos_check.append(nums)
    elif manual_input:
        raw_nums = [int(n) for n in re.findall(r'\d+', manual_input)]
        for i in range(0, len(raw_nums), 15):
            if len(raw_nums[i:i+15]) == 15: jogos_check.append(raw_nums[i:i+15])
            
    if jogos_check:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**RESULTADO ({ult_conc['Concurso']})**")
        total_ganho = 0
        for idx, jogo in enumerate(jogos_check):
            acertos = len(set(jogo) & set(dezenas_ult))
            premio, cor = 0, "#30363d"
            if acertos == 11: premio=6; cor="#e69138"
            if acertos == 12: premio=12; cor="#f1c232"
            if acertos >= 13: premio=30; cor="#00ff88" # Simbólico para 13+
            total_ganho += premio
            st.sidebar.markdown(f"<div style='border-left:4px solid {cor}; padding:5px 10px; background:#161b22; margin-bottom:5px; font-size:13px;'>Jogo {idx+1}: <b style='color:#fff'>{acertos} pts</b></div>", unsafe_allow_html=True)
        
        if total_ganho > 0: st.sidebar.success(f"💰 PRÊMIO: R$ {total_ganho},00")
        else: st.sidebar.warning("Sem premiação.")

    # --- DASHBOARD PRINCIPAL ---
    st.title("🦅 LOTOQUANT | GRAND MASTER V6")
    st.markdown(f"**Concurso:** {ult_conc['Concurso']} | **Status:** 🟢 Online & Blindado")
    
    # ALERTA DE CICLO
    dezenas_ciclo = analisar_ciclo(df)
    if dezenas_ciclo:
        st.markdown(f"""
        <div class='cycle-alert'>
            <h3 style='margin:0; color:#3fb950'>⚠️ ALERTA DE CICLO ABERTO</h3>
            <span style='font-size:14px; color:#d0d7de'>A matemática indica alta pressão para estes números saírem hoje:</span><br>
            <span style='font-size:28px; font-weight:bold; letter-spacing:2px'>{dezenas_ciclo}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("✅ O Ciclo está Fechado. O sistema usará estratégia de distribuição padrão.")

    # GERADOR
    if st.button("🚀 GERAR ESQUADRÃO TÁTICO (3 JOGOS)"):
        stats = calcular_rsi(df)
        jogos = gerar_jogos_elite(stats, dezenas_ult, dezenas_ciclo)
        
        txt_download = f"--- LOTOQUANT V6 | CONCURSO {ult_conc['Concurso']+1} ---\n\n"
        
        for jogo in jogos:
            nums = jogo['Numeros']
            txt_download += f"{jogo['Titulo']}: {nums}\n"
            
            # Análise de Linhas para o HUD
            linhas_count = [0]*5
            for n in nums: linhas_count[(n-1)//5] += 1
            str_linhas = "-".join(map(str, linhas_count))
            
            repetidos = len(set(nums) & set(dezenas_ult))
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h3>{jogo['Titulo']}</h3>
                        <span style='background:#21262d; padding:2px 8px; border-radius:4px; font-size:11px; color:#8b949e'>{jogo['Tipo']}</span>
                    </div>
                    
                    <div class='ai-reason'>{jogo['Razao']}</div>
                    
                    <div class='hud-panel'>
                        <span>LINHAS: <span class='hud-value'>{str_linhas}</span></span>
                        <span>REPETIDAS: <span class='hud-value'>{repetidos}</span></span>
                        <span>SOMA: <span class='hud-value'>{sum(nums)}</span></span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Renderiza Bolas
                cols = st.columns(5)
                html_bolas = ""
                for n in nums:
                    css_class = "fria"
                    if n in dezenas_ciclo: css_class = "fixa"     # Prioridade 1: Ciclo (Roxo)
                    elif n in dezenas_ult: css_class = "repetida" # Prioridade 2: Repetida (Verde)
                    
                    html_bolas += f"<div class='number-box {css_class}'>{n:02d}</div>"
                
                st.markdown(f"<div class='numbers-grid'>{html_bolas}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.download_button(
            label="💾 BAIXAR JOGOS (SALVAR NO CELULAR)",
            data=txt_download,
            file_name=f"LotoQuant_Jogos_{ult_conc['Concurso']+1}.txt",
            mime="text/plain"
        )
        
else:
    st.error("⚠️ Erro de conexão com os servidores da Caixa. Tente novamente em 1 minuto.")
    if st.button("🔄 Reconectar"): st.rerun()