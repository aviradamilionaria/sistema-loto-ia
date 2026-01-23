import streamlit as st
import pandas as pd
import requests
import numpy as np
from typing import List, Set, Dict, Tuple, Optional
from io import StringIO
import re

# --- 1. CONFIGURAÇÃO SYSTEM KERNEL ---
st.set_page_config(
    page_title="LotoQuant | KERNEL V9.4",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS HIGH-TECH
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; font-family: 'Consolas', monospace; }
    .stButton>button { 
        background: #003300; color: #00ff00; border: 1px solid #00ff00; 
        font-family: 'Consolas', monospace; font-size: 20px; height: 70px; width: 100%;
        text-transform: uppercase; transition: all 0.2s;
    }
    .stButton>button:hover { background: #00ff00; color: #000; box-shadow: 0 0 15px #00ff00; }
    
    .game-card { background: #0d1117; border: 1px solid #30363d; padding: 15px; margin-bottom: 20px; position: relative; }
    .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 10px; }
    .reason-text { font-size: 12px; color: #8b949e; margin-bottom: 10px; border-left: 2px solid #58a6ff; padding-left: 10px; }
    
    .ball-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; }
    .ball { 
        background: #000; border: 1px solid #333; color: #888; 
        border-radius: 50%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; 
    }
    
    .b-fixa { border-color: #a371f7; color: #a371f7; box-shadow: 0 0 5px #a371f744; } /* Crítico Principal */
    .b-rec { border-color: #d29922; color: #d29922; box-shadow: 0 0 5px #d2992244; } /* Recuperado */
    .b-rep { border-color: #238636; color: #238636; }
    .success-tag { color: #238636; font-weight: bold; }
    
    /* Estilo do Conferidor */
    .result-box { border-left: 5px solid #333; padding: 10px; margin-bottom: 5px; background: #0a0a0a; }
    .win-11 { border-color: #e69138; }
    .win-12 { border-color: #f1c232; }
    .win-13 { border-color: #00ff00; box-shadow: 0 0 10px #00ff0033; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LAYER ---
@st.cache_data(ttl=60)
def fetch_data() -> Optional[pd.DataFrame]:
    ENDPOINTS = [
        "https://raw.githubusercontent.com/guilhermeasn/loteria.json/master/data/lotofacil.json", 
        "https://loteriascaixa-api.herokuapp.com/api/lotofacil",
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    ]
    for url in ENDPOINTS:
        try:
            resp = requests.get(url, timeout=5, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                processed = []
                for game in data:
                    draw = game.get('dezenas') or game.get('listaDezenas')
                    if draw:
                        processed.append({'id': game['concurso'], 'draw': [int(x) for x in draw]})
                if processed:
                    return pd.DataFrame(processed).sort_values('id').reset_index(drop=True)
        except: continue
    return None

# --- 3. CORE ANALYTICS ---
class LotoEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.last_draw = set(df.iloc[-1]['draw'])
        self.universe = set(range(1, 26))
        
    def get_cycle_missing(self) -> List[int]:
        accumulated = set()
        for i in range(len(self.df)-1, -1, -1):
            accumulated.update(self.df.iloc[i]['draw'])
            if len(accumulated) == 25:
                new_cycle_nums = set()
                for j in range(i+1, len(self.df)):
                    new_cycle_nums.update(self.df.iloc[j]['draw'])
                return sorted(list(self.universe - new_cycle_nums))
        return []

    def get_delays(self) -> Dict[int, int]:
        delays = {}
        for num in self.universe:
            count = 0
            for i in range(len(self.df)-1, -1, -1):
                if num not in self.df.iloc[i]['draw']: count += 1
                else: break
            delays[num] = count
        return delays

    # RSI Simplificado para performance (sem biblioteca externa pesada se não precisar)
    def get_rsi_score(self) -> Dict[int, float]:
        # Cálculo simples de frequência recente (últimos 10 jogos) como peso
        weights = {}
        last_10 = self.df.tail(10)
        for num in self.universe:
            count = sum(1 for _, row in last_10.iterrows() if num in row['draw'])
            weights[num] = count * 10 # Score 0 a 100
        return weights

# --- 4. DETERMINISTIC GENERATOR ---
def generate_game_deterministic(
    target_repeats: int, 
    mandatory_nums: Set[int], 
    banned_nums: Set[int],
    last_draw: Set[int],
    universe: Set[int],
    weights: Dict[int, float]
) -> Tuple[List[int], str]:
    
    pool_repeats = list(last_draw - banned_nums)
    pool_absents = list((universe - last_draw) - banned_nums)
    
    mandatory_in_repeats = mandatory_nums.intersection(last_draw)
    mandatory_in_absents = mandatory_nums.intersection(universe - last_draw)
    
    if len(mandatory_in_repeats) > target_repeats: return [], "Erro: Estouro de Repetidas"
    
    selected_repeats = list(mandatory_in_repeats)
    needed_repeats = target_repeats - len(selected_repeats)
    
    available_repeats = [x for x in pool_repeats if x not in selected_repeats]
    available_repeats.sort(key=lambda x: weights.get(x, 0), reverse=True)
    
    if len(available_repeats) < needed_repeats: return [], "Erro: Falta de Repetidas"
    selected_repeats += available_repeats[:needed_repeats]
    
    selected_absents = list(mandatory_in_absents)
    slots_left = 15 - len(selected_repeats) - len(selected_absents)
    if slots_left < 0: return [], "Erro: Estouro Total"
    
    available_absents = [x for x in pool_absents if x not in selected_absents]
    available_absents.sort(key=lambda x: weights.get(x, 0), reverse=True)
    
    if len(available_absents) < slots_left: return [], "Erro: Falta de Ausentes"
    selected_absents += available_absents[:slots_left]
    
    return sorted(selected_repeats + selected_absents), "Sucesso"

# --- 5. UI LAYER ---
df = fetch_data()

if df is not None:
    engine = LotoEngine(df)
    last_draw_set = engine.last_draw
    cycle = engine.get_cycle_missing()
    delays = engine.get_delays()
    rsi_weights = engine.get_rsi_score()
    
    last_contest = df.iloc[-1]
    
    # === BARRA LATERAL: CONFERIDOR (RESTAURADO) ===
    st.sidebar.title("🧾 CONFERIDOR")
    st.sidebar.markdown(f"**Base:** Concurso {last_contest['id']}")
    
    uploaded_file = st.sidebar.file_uploader("Carregar Arquivo .txt", type="txt")
    manual_input = st.sidebar.text_area("Ou cole aqui:", height=100)
    
    games_to_check = []
    
    if uploaded_file:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        for line in stringio:
            nums = [int(n) for n in re.findall(r'\d+', line)][:15]
            if len(nums) == 15: games_to_check.append(nums)
    elif manual_input:
        raw = [int(n) for n in re.findall(r'\d+', manual_input)]
        for i in range(0, len(raw), 15):
            if len(raw[i:i+15]) == 15: games_to_check.append(raw[i:i+15])
            
    if games_to_check:
        st.sidebar.markdown("---")
        total_prize = 0
        for i, game in enumerate(games_to_check):
            hits = len(set(game) & set(last_contest['draw']))
            css_class = ""
            money = 0
            if hits == 11: css_class="win-11"; money=6
            if hits == 12: css_class="win-12"; money=12
            if hits >= 13: css_class="win-13"; money=30 # Estimado
            
            total_prize += money
            
            st.sidebar.markdown(f"""
            <div class='result-box {css_class}'>
                Jogo {i+1}: <b style='color:#fff'>{hits} Pts</b>
            </div>
            """, unsafe_allow_html=True)
        
        if total_prize > 0:
            st.sidebar.success(f"💰 PRÊMIO: R$ {total_prize},00")
        else:
            st.sidebar.warning("Nenhum prêmio.")

    # === TELA PRINCIPAL ===
    critical_all = [k for k,v in delays.items() if v >= 2]
    critical_all.sort(key=lambda x: delays[x], reverse=True)
    
    st.title("LOTOQUANT KERNEL V9.4 (COMPLETE)")
    st.markdown(f"**CONCURSO:** {last_contest['id']} | **RODÍZIO:** ATIVO")
    
    c1, c2 = st.columns(2)
    c1.info(f"🚨 **ATRASADOS:** {critical_all}")
    c2.success(f"♻️ **MODO HEDGE:** ON")

    if st.button("EXECUTAR ESTRATÉGIA"):
        games_output = []
        
        # --- GAME 1: COBERTURA TOTAL (TODOS OS CRÍTICOS) ---
        mandatories_g1 = set(cycle + critical_all[:4]) # Max 4 críticos
        g1, msg1 = generate_game_deterministic(
            9, mandatories_g1, set(), last_draw_set, engine.universe, rsi_weights
        )
        games_output.append({
            "Title": "JOGO 1: SNIPER (COBERTURA TOTAL)",
            "Game": g1, "Type": "ATAQUE",
            "Reason": f"Obrigatório: {sorted(list(mandatories_g1))}. Alvo: 15 pontos se saírem todos.",
            "Special": mandatories_g1
        })
        
        # --- GAME 2: SELETIVO (DEIXA UM DE FORA) ---
        if len(critical_all) > 1:
            left_out_g2 = {critical_all[-1]} # O último crítico fica de fora
            mandatories_g2 = set(cycle + critical_all[:-1])
        else:
            left_out_g2 = set()
            mandatories_g2 = set(cycle + critical_all)
            
        g2, msg2 = generate_game_deterministic(
            10, mandatories_g2, set(), last_draw_set, engine.universe, rsi_weights
        )
        games_output.append({
            "Title": "JOGO 2: TENDÊNCIA (VARIAÇÃO)",
            "Game": g2, "Type": "MISTO",
            "Reason": f"Deixou o {list(left_out_g2)} de fora para o Jogo 3 pegar.",
            "Special": mandatories_g2
        })

        # --- GAME 3: RECUPERADOR (PEGA O ESQUECIDO) ---
        mandatories_g3 = left_out_g2
        banned_g3 = mandatories_g2
        
        # Tenta gerar. Se falhar por falta de números, relaxa o banimento
        g3, msg3 = generate_game_deterministic(
            8, mandatories_g3, banned_g3, last_draw_set, engine.universe, rsi_weights
        )
        
        if not g3:
            # Relaxa: Bane só o #1 Atrasado
            banned_g3 = {critical_all[0]} if critical_all else set()
            g3, msg3 = generate_game_deterministic(
                8, mandatories_g3, banned_g3, last_draw_set, engine.universe, rsi_weights
            )
            reason_txt = f"⚠️ Recuperou {list(mandatories_g3)}, mas relaxou banimentos."
        else:
            reason_txt = f"♻️ ESTRATÉGIA DE RESGATE: Fixou o esquecido {list(mandatories_g3)} e baniu {sorted(list(banned_g3))}."

        games_output.append({
            "Title": "JOGO 3: RESGATE (ZEBRA)",
            "Game": g3, "Type": "DEFESA",
            "Reason": reason_txt,
            "Special": mandatories_g3
        })
        
        # RENDER
        txt_download = ""
        for g_data in games_output:
            nums = g_data["Game"]
            if not nums: continue 
            
            txt_download += f"{g_data['Title']}: {nums}\n"
            rep_count = len(set(nums) & last_draw_set)
            
            special_nums = g_data.get("Special", set())
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div class='card-header'>
                        <span style='color:#fff; font-weight:bold'>{g_data['Title']}</span>
                        <span style='background:#333; padding:2px 8px; border-radius:4px; font-size:12px'>{g_data['Type']}</span>
                    </div>
                    <div class='reason-text'>{g_data['Reason']}</div>
                    <div style='margin-bottom:10px; font-size:12px; color:#666;'>
                        REPETIDAS: <span class='success-tag'>{rep_count}</span> | SOMA: {sum(nums)}
                    </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(5)
                html = ""
                for n in nums:
                    css = ""
                    if n in special_nums: css = "b-fixa" 
                    elif n in left_out_g2 and g_data['Title'] == "JOGO 3: RESGATE (ZEBRA)": css = "b-rec"
                    elif n in last_draw_set: css = "b-rep"
                    html += f"<div class='ball {css}'>{n:02d}</div>"
                st.markdown(f"<div class='ball-grid'>{html}</div></div>", unsafe_allow_html=True)

        st.download_button("💾 BAIXAR JOGOS (.TXT)", txt_download, "lotoquant_v94.txt")

else:
    st.error("Erro de conexão. Tente recarregar.")