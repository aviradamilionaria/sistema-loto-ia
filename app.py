import streamlit as st
import pandas as pd
import requests
import numpy as np
from typing import List, Set, Dict, Tuple, Optional
from io import StringIO
import re

# --- 1. CONFIGURAÇÃO SYSTEM KERNEL ---
st.set_page_config(
    page_title="LotoQuant | KERNEL V9.5",
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
    
    .b-fixa { border-color: #a371f7; color: #a371f7; box-shadow: 0 0 5px #a371f744; } /* Obrigatório */
    .b-esq { border-color: #ff4b4b; color: #ff4b4b; box-shadow: 0 0 8px #ff4b4b44; } /* Esquecido (Resgatado) */
    .b-rep { border-color: #238636; color: #238636; }
    .success-tag { color: #238636; font-weight: bold; }
    
    /* Conferidor */
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

    def get_rsi_score(self) -> Dict[int, float]:
        weights = {}
        last_10 = self.df.tail(10)
        for num in self.universe:
            count = sum(1 for _, row in last_10.iterrows() if num in row['draw'])
            weights[num] = count * 10 
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
    
    # Pools
    pool_repeats = list(last_draw - banned_nums)
    pool_absents = list((universe - last_draw) - banned_nums)
    
    # Mandatories Handling
    # Force mandatories into the selection regardless of pool status (Critical Fix)
    mandatory_in_repeats = mandatory_nums.intersection(last_draw)
    mandatory_in_absents = mandatory_nums.intersection(universe - last_draw)
    
    # If mandatory exceeds target repeats, we adjust target repeats (Flexibility for Coverage)
    if len(mandatory_in_repeats) > target_repeats:
        target_repeats = len(mandatory_in_repeats)
    
    selected_repeats = list(mandatory_in_repeats)
    needed_repeats = target_repeats - len(selected_repeats)
    
    available_repeats = [x for x in pool_repeats if x not in selected_repeats]
    available_repeats.sort(key=lambda x: weights.get(x, 0), reverse=True)
    
    if len(available_repeats) < needed_repeats: 
        # Fallback: take all available
        needed_repeats = len(available_repeats)
    
    selected_repeats += available_repeats[:needed_repeats]
    
    # Absents
    selected_absents = list(mandatory_in_absents)
    slots_left = 15 - len(selected_repeats) - len(selected_absents)
    
    if slots_left < 0: return [], "Erro: Superlotação de números"
    
    available_absents = [x for x in pool_absents if x not in selected_absents]
    available_absents.sort(key=lambda x: weights.get(x, 0), reverse=True)
    
    if len(available_absents) < slots_left:
        # Emergency fill from repeats pool if absents run out (Rare)
        return [], "Erro: Falta de números no universo"
        
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
    
    # SIDEBAR CONFERIDOR
    st.sidebar.title("🧾 CONFERIDOR")
    st.sidebar.markdown(f"**Base:** Concurso {last_contest['id']}")
    uploaded_file = st.sidebar.file_uploader("Carregar .txt", type="txt")
    manual_input = st.sidebar.text_area("Colar jogos:", height=100)
    
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
            if hits >= 13: css_class="win-13"; money=30
            total_prize += money
            st.sidebar.markdown(f"<div class='result-box {css_class}'>Jogo {i+1}: <b style='color:#fff'>{hits} Pts</b></div>", unsafe_allow_html=True)
        if total_prize > 0: st.sidebar.success(f"💰 R$ {total_prize},00")
        else: st.sidebar.warning("Sem prêmio.")

    # MAIN SCREEN
    critical_all = [k for k,v in delays.items() if v >= 2]
    critical_all.sort(key=lambda x: delays[x], reverse=True)
    
    st.title("LOTOQUANT V9.5 (GLOBAL COVERAGE)")
    st.markdown(f"**CONCURSO:** {last_contest['id']} | **CERCAMENTO:** TOTAL (25/25)")
    
    c1, c2 = st.columns(2)
    c1.info(f"🚨 **ATRASADOS:** {critical_all}")
    c2.success(f"🌐 **GARANTIA:** Todos os 25 números serão jogados.")

    if st.button("GERAR CERCAMENTO TOTAL"):
        games_output = []
        
        # --- GAME 1: SNIPER (9 Repetidas) ---
        mandatories_g1 = set(cycle + critical_all[:4]) 
        g1, msg1 = generate_game_deterministic(
            9, mandatories_g1, set(), last_draw_set, engine.universe, rsi_weights
        )
        games_output.append({
            "Title": "JOGO 1: SNIPER (BASE)",
            "Game": g1, "Type": "ATAQUE",
            "Reason": f"Base sólida com Ciclo e Atrasados. {len(set(g1) & last_draw_set)} Repetidas.",
            "Special": mandatories_g1
        })
        
        # --- GAME 2: TENDÊNCIA (10 Repetidas) ---
        if len(critical_all) > 1:
            left_out_g2 = {critical_all[-1]} 
            mandatories_g2 = set(cycle + critical_all[:-1])
        else:
            left_out_g2 = set()
            mandatories_g2 = set(cycle + critical_all)
            
        g2, msg2 = generate_game_deterministic(
            10, mandatories_g2, set(), last_draw_set, engine.universe, rsi_weights
        )
        games_output.append({
            "Title": "JOGO 2: TENDÊNCIA",
            "Game": g2, "Type": "VARIAÇÃO",
            "Reason": f"Variação de força. {len(set(g2) & last_draw_set)} Repetidas.",
            "Special": mandatories_g2
        })

        # --- GAME 3: RESGATE GLOBAL (O ESQUECIDO) ---
        # 1. Identifica quem foi jogado em G1 e G2
        used_numbers = set(g1) | set(g2)
        
        # 2. Identifica quem NUNCA apareceu (Os Esquecidos)
        forgotten_numbers = engine.universe - used_numbers
        
        # 3. O Jogo 3 TEM QUE ter esses números
        mandatories_g3 = forgotten_numbers
        
        # 4. Banimentos: Tentamos banir o que já foi muito usado, mas Mandatories ganham prioridade
        banned_g3 = set(critical_all) - mandatories_g3 # Bane atrasados, exceto se eles forem os esquecidos
        
        g3, msg3 = generate_game_deterministic(
            8, mandatories_g3, banned_g3, last_draw_set, engine.universe, rsi_weights
        )
        
        # Se falhar, limpa banimentos (prioridade é cobrir os 25 números)
        if not g3:
            g3, msg3 = generate_game_deterministic(
                8, mandatories_g3, set(), last_draw_set, engine.universe, rsi_weights
            )
            
        reason_txt = f"🌐 CERCAMENTO: Resgatou {sorted(list(forgotten_numbers))}. Agora temos 25/25 cobertos."

        games_output.append({
            "Title": "JOGO 3: RESGATE (ZEBRA)",
            "Game": g3, "Type": "GLOBAL",
            "Reason": reason_txt,
            "Special": mandatories_g3, # Vai destacar em Roxo
            "Forgotten": forgotten_numbers # Vai destacar em Vermelho
        })
        
        # RENDER
        txt_download = ""
        for g_data in games_output:
            nums = g_data["Game"]
            if not nums: continue 
            
            txt_download += f"{g_data['Title']}: {nums}\n"
            rep_count = len(set(nums) & last_draw_set)
            
            special_nums = g_data.get("Special", set())
            forgotten_nums = g_data.get("Forgotten", set())
            
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
                    if n in forgotten_nums: css = "b-esq" # Vermelho (Resgatado Obrigatório)
                    elif n in special_nums: css = "b-fixa" # Roxo
                    elif n in last_draw_set: css = "b-rep" # Verde
                    html += f"<div class='ball {css}'>{n:02d}</div>"
                st.markdown(f"<div class='ball-grid'>{html}</div></div>", unsafe_allow_html=True)

        st.download_button("💾 BAIXAR JOGOS (.TXT)", txt_download, "lotoquant_v95.txt")

else:
    st.error("Erro de conexão. Tente recarregar.")