import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import re

# --- 1. CONFIGURAÇÃO ELITE (VISUAL CYBERPUNK/MILITAR) ---
st.set_page_config(
    page_title="LotoQuant | MASTER V5",
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

# --- 2. MOTOR DE DADOS & CONFERÊNCIA ---
@st.cache_data(ttl=300)
def baixar_dados_live():
    url = "https://raw.githubusercontent.com/guilhermeasn/loteria.json/master/data/lotofacil.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            lista = []
            for jogo in dados:
                dezenas = [int(x) for x in jogo.get('dezenas', []) or jogo.get('listaDezenas', [])]
                if len(dezenas) == 15:
                    lista.append({'Concurso': jogo['concurso'], 'Dezenas': dezenas})
            if lista:
                return pd.DataFrame(lista).sort_values('Concurso').reset_index(drop=True)
    except: pass
    return None

# --- 3. INTELIGÊNCIA DE CICLOS (NOVO) ---
def analisar_ciclo(df):
    # Varre de trás pra frente para encontrar o ciclo aberto
    todos_numeros = set(range(1, 26))
    acumulado = set()
    
    # Percorre os últimos jogos
    for i in range(len(df)-1, -1, -1):
        dezenas = set(df.iloc[i]['Dezenas'])
        acumulado.update(dezenas)
        
        if len(acumulado) == 25:
            # Ciclo fechou aqui. O que veio depois é o ciclo novo.
            # Vamos pegar os jogos DEPOIS desse fechamento até agora
            novo_ciclo_numeros = set()
            for j in range(i+1, len(df)):
                novo_ciclo_numeros.update(set(df.iloc[j]['Dezenas']))
            
            faltam = todos_numeros - novo_ciclo_numeros
            return sorted(list(faltam))
            
    # Se nunca fechou (improvável com muitos dados), retorna vazio
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

# --- 5. GERADOR HIERÁRQUICO (FODA) ---
def gerar_jogos_elite(df_stats, ultimas_dezenas, dezenas_ciclo):
    jogos = []
    
    # Classificação
    quentes = df_stats.sort_values('RSI', ascending=False).head(10)['Bola'].tolist()
    frios = df_stats.sort_values('RSI', ascending=True).head(8)['Bola'].tolist()
    neutros = [x for x in range(1,26) if x not in quentes and x not in frios]
    
    # --- JOGO 1: O MATADOR DE CICLO (Principal) ---
    # Prioridade Máxima: Dezenas do Ciclo + Melhores Repetidas
    base_j1 = list(dezenas_ciclo) # Fixa as do ciclo
    # Completa com as melhores quentes que também são repetidas (tendência)
    candidatos = [x for x in quentes if x in ultimas_dezenas and x not in base_j1]
    base_j1 += candidatos
    # Se faltar, pega neutros equilibrados
    while len(base_j1) < 15:
        restante = [x for x in (quentes + neutros) if x not in base_j1]
        base_j1.append(restante[0])
    
    palpite1 = sorted(base_j1[:15])
    razao1 = f"<b>Estratégia:</b> Fechamento de Ciclo.<br>Fixei as dezenas <b>{dezenas_ciclo}</b> pois a estatística exige que elas saiam para fechar o ciclo. Completei com as dezenas mais quentes do momento."
    jogos.append({"Titulo": "🦅 ELITE: CICLO MASTER", "Numeros": palpite1, "Razao": razao1})

    # --- JOGO 2: TENDÊNCIA TÉCNICA (RSI) ---
    # Ignora ciclo, foca apenas na força do número (RSI)
    # 70% Quentes + 30% Neutros
    base_j2 = quentes[:9] + neutros[:4]
    # Completa
    while len(base_j2) < 15:
        restante = [x for x in range(1,26) if x not in base_j2]
        base_j2.append(restante[0])
        
    palpite2 = sorted(base_j2[:15])
    razao2 = "<b>Estratégia:</b> Tendência Pura (RSI).<br>Este jogo ignora atrasos e foca apenas nos números que estão com 'Força Relativa' alta. É o jogo para quando a lógica prevalece."
    jogos.append({"Titulo": "🔥 TENDÊNCIA ALTA", "Numeros": palpite2, "Razao": razao2})

    # --- JOGO 3: PROTEÇÃO (ZEBRA) ---
    # Foca nos frios e atrasados (Hedge)
    base_j3 = frios[:6] + neutros[:5] + quentes[:4] # Mistura forçada
    palpite3 = sorted(base_j3[:15])
    razao3 = "<b>Estratégia:</b> Hedge (Proteção).<br>Se o ciclo não fechar e os favoritos falharem, este jogo captura as zebras (números frios) que podem surpreender."
    jogos.append({"Titulo": "🛡️ ESCUDO (ZEBRA)", "Numeros": palpite3, "Razao": razao3})

    return jogos

# --- 6. INTERFACE DE COMANDO ---
st.sidebar.title("🧮 CONFERIDOR")
st.sidebar.markdown("Cole seu jogo aqui (ex: 01, 02, 05...):")
jogo_usuario_txt = st.sidebar.text_area("Seus Números", height=100)

df = baixar_dados_live()

if df is not None:
    ult_conc = df.iloc[-1]
    dezenas_ult = ult_conc['Dezenas']
    
    # --- LÓGICA DO CONFERIDOR ---
    if st.sidebar.button("CONFERIR RESULTADO"):
        try:
            # Limpa o texto para pegar só números
            nums_str = re.findall(r'\d+', jogo_usuario_txt)
            meu_jogo = [int(n) for n in nums_str]
            meu_jogo = list(set(meu_jogo)) # remove duplicados
            
            if len(meu_jogo) < 15:
                st.sidebar.error(f"Você digitou apenas {len(meu_jogo)} números!")
            else:
                acertos = len(set(meu_jogo) & set(dezenas_ult))
                msg_premio = "SEM PRÊMIO"
                cor_premio = "red"
                if acertos == 11: msg_premio = "R$ 6,00 (11 pts)"; cor_premio="orange"
                if acertos == 12: msg_premio = "R$ 12,00 (12 pts)"; cor_premio="yellow"
                if acertos == 13: msg_premio = "R$ 30,00 (13 pts)"; cor_premio="#00ff88"
                if acertos == 14: msg_premio = "PRÊMIO GRANDE (14 pts)"; cor_premio="#00ff88"
                if acertos == 15: msg_premio = "MILIONÁRIO (15 pts)"; cor_premio="#00ff88"
                
                st.sidebar.markdown(f"""
                <div style='background:#21262d; padding:15px; border-radius:10px; text-align:center;'>
                    <h1 style='margin:0; font-size:40px; color:{cor_premio}'>{acertos}</h1>
                    <span style='color:#8b949e'>ACERTOS</span>
                    <hr style='border-color:#30363d'>
                    <h3 style='color:{cor_premio}; margin:0'>{msg_premio}</h3>
                    <p style='font-size:12px; margin-top:5px'>Ref: Concurso {ult_conc['Concurso']}</p>
                </div>
                """, unsafe_allow_html=True)
        except:
            st.sidebar.error("Formato inválido. Digite apenas números.")

    # --- PAINEL PRINCIPAL ---
    st.title("🦅 LOTOQUANT | MASTER V5")
    st.markdown(f"**Base de Dados:** Concurso {ult_conc['Concurso']} | **Status:** Online")
    
    # ANÁLISE DE CICLO
    dezenas_ciclo = analisar_ciclo(df)
    
    if len(dezenas_ciclo) > 0:
        st.markdown(f"""
        <div class='cycle-alert'>
            ⚠️ ALERTA DE CICLO ABERTO: FALTAM {len(dezenas_ciclo)} NÚMEROS<br>
            <span style='font-size:24px; color:#fff'>{dezenas_ciclo}</span><br>
            <span style='font-size:12px'>Esses números têm 90% de chance de sair hoje.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ O Ciclo fechou no último jogo. Um novo ciclo começa hoje (tudo em aberto).")

    if st.button("GERAR JOGOS DE ALTA PERFORMANCE"):
        stats = calcular_rsi(df)
        jogos = gerar_jogos_elite(stats, dezenas_ult, dezenas_ciclo)
        
        for jogo in jogos:
            nums = jogo['Numeros']
            # Métricas
            repetidos = len(set(nums) & set(dezenas_ult))
            ciclo_presenca = len(set(nums) & set(dezenas_ciclo))
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center'>
                        <h3>{jogo['Titulo']}</h3>
                        <div style='font-size:12px; color:#8b949e'>
                            CICLO: <b style='color:#a371f7'>{ciclo_presenca}</b> | REP: <b style='color:#3fb950'>{repetidos}</b>
                        </div>
                    </div>
                    
                    <div class='ai-reason'>
                        {jogo['Razao']}
                    </div>
                """, unsafe_allow_html=True)
                
                # Renderiza Bolas
                cols = st.columns(5)
                html_bolas = ""
                for n in nums:
                    # Estilo: Roxo (Ciclo), Verde (Repetido), Branco (Normal)
                    style_class = ""
                    if n in dezenas_ciclo: style_class = "fixa"
                    elif n in dezenas_ult: style_class = "repetida"
                    
                    html_bolas += f"<div class='number-box {style_class}'>{n:02d}</div>"
                
                st.markdown(f"<div class='numbers-grid'>{html_bolas}</div></div>", unsafe_allow_html=True)

else:
    st.error("Servidor de dados offline. Tente recarregar a página.")