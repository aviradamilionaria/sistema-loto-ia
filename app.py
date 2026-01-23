import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import re
from io import StringIO

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(
    page_title="LotoQuant | SYSTEM V8.2",
    page_icon="🧿",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stButton>button { 
        background: linear-gradient(180deg, #238636 0%, #2ea043 100%);
        color: white; border: none; border-radius: 6px;
        font-weight: 900; font-size: 24px; height: 80px; width: 100%;
        text-transform: uppercase; box-shadow: 0 4px 15px rgba(46, 160, 67, 0.4);
    }
    .stButton>button:hover { transform: scale(1.02); }
    
    .info-panel {
        background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 20px;
        display: grid; grid-template-columns: 1fr 1fr; gap: 15px;
    }
    .info-box { background: #0d1117; padding: 10px; border-radius: 6px; border-left: 4px solid #58a6ff; }
    .info-title { font-size: 12px; color: #8b949e; text-transform: uppercase; font-weight: bold; }
    .info-value { font-size: 18px; color: #fff; font-weight: bold; }
    
    .game-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 25px; position: relative; }
    .game-badge { position: absolute; top: 15px; right: 15px; background: #238636; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .ai-reason { background: #21262d; border-left: 4px solid #a371f7; padding: 12px; margin: 15px 0; border-radius: 4px; color: #d0d7de; font-size: 14px; }
    
    .numbers-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top:10px; }
    .number-box { background: #0d1117; border: 2px solid #30363d; color: #fff; border-radius: 50%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; }
    
    .fixa { border-color: #a371f7 !important; color: #a371f7 !important; box-shadow: 0 0 10px rgba(163, 113, 247, 0.2); }
    .repetida { border-color: #238636 !important; color: #3fb950 !important; }
    .alerta { border-color: #d29922 !important; color: #d29922 !important; }
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

def calcular_atrasos(df):
    atrasos = {}
    for i in range(1, 26):
        atraso = 0
        for idx in range(len(df)-1, -1, -1):
            if i not in df.iloc[idx]['Dezenas']: atraso += 1
            else: break
        atrasos[i] = atraso
    return atrasos

def calcular_rsi(df):
    cols = pd.DataFrame(0, index=df.index, columns=[f'N{i}' for i in range(1,26)])
    for idx, row in df.iterrows():
        for d in row['Dezenas']: cols.at[idx, f'N{d}'] = 1
    stats = []
    for i in range(1, 26):
        rsi = ta.momentum.rsi(cols[f'N{i}'], window=14).iloc[-1]
        stats.append({'Bola': i, 'RSI': rsi})
    return pd.DataFrame(stats)

# --- 4. GERADOR COM MODO DE SEGURANÇA ---
def gerar_jogos_ultimate(df_stats, ultimas, ciclo, atrasos):
    jogos = []
    quentes = df_stats.sort_values('RSI', ascending=False)['Bola'].tolist()
    atrasados_criticos = [k for k,v in atrasos.items() if v >= 2]
    atrasados_criticos = sorted(atrasados_criticos, key=lambda x: atrasos[x], reverse=True)
    
    # === JOGO 1: SNIPER (Lógica Pura) ===
    base1_final = []
    tentativas = 0
    sucesso = False
    
    # Loop de Tentativa Perfeita (Soma + Repetidas)
    while tentativas < 3000:
        base1 = list(set(ciclo + atrasados_criticos)) 
        pool = [x for x in quentes if x not in base1 and x in ultimas]
        np.random.shuffle(pool)
        base1 += pool
        if len(base1) < 15:
            rest = [x for x in range(1,26) if x not in base1]
            np.random.shuffle(rest)
            base1 += rest[:(15-len(base1))]
            
        base1 = sorted(base1[:15])
        rep = len(set(base1) & set(ultimas))
        soma = sum(base1)
        
        if (8 <= rep <= 10) and (180 <= soma <= 220):
            base1_final = base1
            txt1 = f"🎯 <b>ESTRATÉGIA:</b> Fixei os atrasados <b>{atrasados_criticos}</b>. Filtro PERFEITO: <b>{rep} repetidas</b> e Soma <b>{soma}</b>."
            jogos.append({"Titulo": "JOGO 1: SNIPER (LÓGICA)", "Numeros": base1_final, "Razao": txt1, "Tag": "ATAQUE"})
            sucesso = True
            break
        tentativas += 1
    
    # MODO DE SEGURANÇA (Se falhou o loop)
    if not sucesso:
        # Gera apenas com foco em Repetidas (Ignora Soma para não travar)
        base1_final = sorted(base1[:15]) # Pega a última tentativa
        txt1 = f"⚠️ <b>MODO DE SEGURANÇA:</b> O filtro de Soma estava muito rígido. Gereio o jogo focado em <b>Repetidas ({len(set(base1_final)&set(ultimas))})</b> e Atrasados."
        jogos.append({"Titulo": "JOGO 1: SNIPER (MODO SEGURO)", "Numeros": base1_final, "Razao": txt1, "Tag": "ATAQUE"})

    # === JOGO 2: VARIAÇÃO ===
    tentativas = 0
    sucesso = False
    while tentativas < 3000:
        base2 = [atrasados_criticos[0]] if atrasados_criticos else [] 
        pool = quentes[:18]
        np.random.shuffle(pool)
        for n in pool:
            if n not in base2 and len(base2) < 15: base2.append(n)
            
        base2 = sorted(base2[:15])
        rep = len(set(base2) & set(ultimas))
        soma = sum(base2)
        
        # Verifica se não é igual ao Jogo 1
        diferente = base2 != jogos[0]['Numeros']
        
        if (8 <= rep <= 11) and (175 <= soma <= 225) and diferente:
            txt2 = f"⚖️ <b>ESTRATÉGIA:</b> Mantive o <b>{atrasados_criticos[0]}</b> mas variei o resto. Soma calibrada em <b>{soma}</b>."
            jogos.append({"Titulo": "JOGO 2: EQUILÍBRIO", "Numeros": base2, "Razao": txt2, "Tag": "MISTO"})
            sucesso = True
            break
        tentativas += 1
        
    if not sucesso:
        # Fallback Jogo 2
        txt2 = "⚠️ <b>MODO DE SEGURANÇA:</b> Variação gerada sem filtro de Soma para garantir o jogo."
        jogos.append({"Titulo": "JOGO 2: EQUILÍBRIO (MODO SEGURO)", "Numeros": base2, "Razao": txt2, "Tag": "MISTO"})

    # === JOGO 3: HEDGE (CONTRA-CICLO) ===
    # Este é mais fácil de gerar, raramente trava
    excluidos = set(ciclo + atrasados_criticos)
    pool_seguro = [x for x in range(1,26) if x not in excluidos]
    
    tentativas = 0
    base3 = []
    sucesso = False
    
    while tentativas < 2000:
        np.random.shuffle(pool_seguro)
        base3 = sorted(pool_seguro[:15])
        if len(base3) < 15: 
            rest = list(excluidos)
            np.random.shuffle(rest)
            base3 += rest[:(15-len(base3))]
            base3 = sorted(base3)
            
        rep = len(set(base3) & set(ultimas))
        
        if 6 <= rep <= 10: 
            txt3 = f"🛡️ <b>ESTRATÉGIA:</b> Excluí propositalmente <b>{list(excluidos)}</b>. Se o atrasado falhar, aqui está sua proteção."
            jogos.append({"Titulo": "JOGO 3: ANTI-SISTEMA", "Numeros": base3, "Razao": txt3, "Tag": "DEFESA"})
            sucesso = True
            break
        tentativas += 1
        
    if not sucesso:
         jogos.append({"Titulo": "JOGO 3: ANTI-SISTEMA", "Numeros": base3, "Razao": "Modo de segurança ativado para garantir o jogo.", "Tag": "DEFESA"})

    return jogos

# --- 5. INTERFACE ---
st.sidebar.markdown("## 🧮 CARTEIRA")
uploaded_file = st.sidebar.file_uploader("📂 Carregar Arquivo", type="txt")
manual_input = st.sidebar.text_area("Digitar jogo:", height=80)

with st.spinner('Calibrando Filtros...'):
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
    st.title("🧿 LOTOQUANT | SYSTEM V8.2")
    st.caption(f"Concurso: {ult['Concurso']} | Sistema Anti-Travamento: ATIVO")
    
    ciclo = analisar_ciclo(df)
    atrasos = calcular_atrasos(df)
    criticos = [k for k,v in atrasos.items() if v >= 2]
    
    # PAINEL ESPIONAGEM
    st.markdown("### 📊 RAIO-X DO SORTEIO")
    st.markdown(f"""
    <div class='info-panel'>
        <div class='info-box' style='border-color:#a371f7'>
            <div class='info-title'>ATRASADOS (>2 Jogos)</div>
            <div class='info-value'>{criticos if criticos else "Nenhum Crítico"}</div>
        </div>
        <div class='info-box' style='border-color:#3fb950'>
            <div class='info-title'>FALTAM NO CICLO</div>
            <div class='info-value'>{ciclo if ciclo else "Ciclo Fechado"}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 GERAR JOGOS BLINDADOS"):
        stats = calcular_rsi(df)
        jogos = gerar_jogos_ultimate(stats, dezenas_ult, ciclo, atrasos)
        
        txt_out = f"--- CONCURSO {ult['Concurso']+1} ---\n\n"
        
        for jogo in jogos:
            nums = jogo['Numeros']
            txt_out += f"{jogo['Titulo']}: {nums}\n"
            rep = len(set(nums) & set(dezenas_ult))
            soma = sum(nums)
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div class='game-badge'>{jogo['Tag']}</div>
                    <h3 style='color:#58a6ff'>{jogo['Titulo']}</h3>
                    <div class='ai-reason'>{jogo['Razao']}</div>
                    <div style='display:flex; justify-content:space-between; font-size:13px; color:#8b949e; margin-top:10px;'>
                        <span>REPETIDAS: <b style='color:#fff'>{rep}</b></span>
                        <span>SOMA: <b style='color:#fff'>{soma}</b></span>
                    </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(5)
                html_bolas = ""
                for n in nums:
                    css = ""
                    if n in criticos: css = "fixa"
                    elif n in dezenas_ult: css = "repetida"
                    html_bolas += f"<div class='number-box {css}'>{n:02d}</div>"
                st.markdown(f"<div class='numbers-grid'>{html_bolas}</div></div>", unsafe_allow_html=True)
        
        st.download_button("💾 SALVAR JOGOS", data=txt_out, file_name="jogos_ultimate.txt")

else:
    st.error("Erro ao conectar. Tente recarregar.")