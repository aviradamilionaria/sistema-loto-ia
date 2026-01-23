import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import random
from typing import List, Set, Dict, Tuple, Optional
from io import StringIO
import re

# --- 1. CONFIGURAÇÃO SYSTEM KERNEL ---
st.set_page_config(
    page_title="LotoQuant | KERNEL V9.0",
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
    
    .hud-panel { border: 1px solid #333; background: #0a0a0a; padding: 15px; margin-bottom: 10px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .hud-stat { border-left: 3px solid #00ff00; padding-left: 10px; }
    .hud-label { font-size: 10px; color: #666; text-transform: uppercase; }
    .hud-val { font-size: 18px; color: #fff; font-weight: bold; }
    
    .game-card { background: #0d1117; border: 1px solid #30363d; padding: 15px; margin-bottom: 20px; position: relative; }
    .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 10px; }
    .reason-text { font-size: 12px; color: #8b949e; margin-bottom: 10px; border-left: 2px solid #58a6ff; padding-left: 10px; }
    
    .ball-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; }
    .ball { 
        background: #000; border: 1px solid #333; color: #888; 
        border-radius: 50%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; 
    }
    
    /* Syntax Highlighting Classes */
    .b-fixa { border-color: #a371f7; color: #a371f7; box-shadow: 0 0 5px #a371f744; }
    .b-rep { border-color: #238636; color: #238636; }
    .b-cold { border-color: #30363d; color: #555; }
    
    .success-tag { color: #238636; font-weight: bold; }
    .fail-tag { color: #f00; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LAYER (FAILOVER SYSTEM) ---
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

# --- 3. CORE ANALYTICS ENGINE ---
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
                # Cycle closed here. Look forward.
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

    def get_rsi(self) -> Dict[int, float]:
        # Calculate RSI for each ball
        matrix = pd.DataFrame(0, index=self.df.index, columns=list(self.universe))
        for idx, row in self.df.iterrows():
            matrix.loc[idx, row['draw']] = 1
        
        rsi_dict = {}
        for col in matrix.columns:
            series = matrix[col]
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_dict[col] = 100 - (100 / (1 + rs.iloc[-1]))
        return rsi_dict

# --- 4. DETERMINISTIC GENERATOR (NO MORE GUESSWORK) ---
def generate_game_deterministic(
    target_repeats: int, 
    mandatory_nums: Set[int], 
    banned_nums: Set[int],
    last_draw: Set[int],
    universe: Set[int],
    rsi_scores: Dict[int, float]
) -> Tuple[List[int], str]:
    
    # 1. Separate Universe into Pools
    pool_repeats = list(last_draw - banned_nums)
    pool_absents = list((universe - last_draw) - banned_nums)
    
    # 2. Handle Mandatory Numbers
    # Split mandatory into repeats and absents to count them correctly
    mandatory_in_repeats = mandatory_nums.intersection(last_draw)
    mandatory_in_absents = mandatory_nums.intersection(universe - last_draw)
    
    # Check feasibility
    if len(mandatory_in_repeats) > target_repeats:
        return [], "Error: Mandatory repeats exceed target."
    
    # 3. SELECT REPEATS (Deterministic Count)
    # We start with the mandatory ones
    selected_repeats = list(mandatory_in_repeats)
    
    # How many more do we need?
    needed_repeats = target_repeats - len(selected_repeats)
    
    # Filter pool (remove already selected)
    available_repeats = [x for x in pool_repeats if x not in selected_repeats]
    
    # Prioritize by RSI/Strength if possible
    available_repeats.sort(key=lambda x: rsi_scores.get(x, 50), reverse=True)
    
    # Force Sample
    if len(available_repeats) < needed_repeats:
        return [], "Error: Not enough repeats available."
    
    # Add the best remaining repeats
    selected_repeats += available_repeats[:needed_repeats]
    
    # 4. SELECT ABSENTS (The rest of the game)
    # Start with mandatory absents
    selected_absents = list(mandatory_in_absents)
    
    # Calculate how many slots left to reach 15
    slots_left = 15 - len(selected_repeats) - len(selected_absents)
    
    available_absents = [x for x in pool_absents if x not in selected_absents]
    available_absents.sort(key=lambda x: rsi_scores.get(x, 50), reverse=True)
    
    if len(available_absents) < slots_left:
        return [], "Error: Not enough absents available."
        
    selected_absents += available_absents[:slots_left]
    
    # 5. MERGE
    final_game = sorted(selected_repeats + selected_absents)
    
    return final_game, "Success"

# --- 5. UI LAYER ---
st.sidebar.title("🧮 AUDITORIA")
df = fetch_data()

if df is not None:
    engine = LotoEngine(df)
    last_draw_set = engine.last_draw
    cycle = engine.get_cycle_missing()
    delays = engine.get_delays()
    rsi = engine.get_rsi()
    
    # Critical Numbers logic
    critical = [k for k,v in delays.items() if v >= 2]
    # Sort critical by delay desc
    critical.sort(key=lambda x: delays[x], reverse=True)
    
    st.title("LOTOQUANT KERNEL V9.0")
    st.markdown(f"**CONCURSO:** {df.iloc[-1]['id']} | **STATUS:** ONLINE")
    
    # HUD
    c1, c2, c3 = st.columns(3)
    c1.metric("ATRASADO CRÍTICO", f"{critical[0] if critical else 'N/A'}")
    c2.metric("CICLO", f"{len(cycle)} Falta(m)")
    c3.metric("STATUS REPETIDAS", "Hardware Lock (8-10)")

    if st.button("EXECUTAR SINTAXE DE GERAÇÃO"):
        games_output = []
        
        # --- GAME 1: SNIPER (Logic) ---
        # Constraint: Must contain Top Criticals + Cycle. 
        # Constraint: EXACTLY 9 Repeats (Golden Standard).
        mandatories_g1 = set(cycle + critical[:2])
        g1, msg1 = generate_game_deterministic(
            target_repeats=9, # FORCE 9
            mandatory_nums=mandatories_g1,
            banned_nums=set(),
            last_draw=last_draw_set,
            universe=engine.universe,
            rsi_scores=rsi
        )
        games_output.append({
            "Title": "JOGO 1: SNIPER (DETERMINÍSTICO)",
            "Game": g1,
            "Type": "ATAQUE",
            "Reason": f"Algoritmo forçou 9 repetidas exatas. Fixou {sorted(list(mandatories_g1))}."
        })
        
        # --- GAME 2: EQUILIBRIUM ---
        # Constraint: Top Critical Only. 
        # Constraint: EXACTLY 10 Repeats (Limit).
        mandatories_g2 = {critical[0]} if critical else set()
        g2, msg2 = generate_game_deterministic(
            target_repeats=10, # FORCE 10
            mandatory_nums=mandatories_g2,
            banned_nums=set(), # No banned, just variance
            last_draw=last_draw_set,
            universe=engine.universe,
            rsi_scores=rsi
        )
        games_output.append({
            "Title": "JOGO 2: TENDÊNCIA (LIMITE)",
            "Game": g2,
            "Type": "MISTO",
            "Reason": f"Algoritmo forçou 10 repetidas (Limite Superior). Fixou {list(mandatories_g2)}."
        })

        # --- GAME 3: HEDGE (ZEBRA) ---
        # Constraint: EXCLUDE Game 1 Fixes.
        # Constraint: EXACTLY 8 Repeats (Limit Lower).
        banned_g3 = mandatories_g1
        g3, msg3 = generate_game_deterministic(
            target_repeats=8, # FORCE 8
            mandatory_nums=set(),
            banned_nums=banned_g3,
            last_draw=last_draw_set,
            universe=engine.universe,
            rsi_scores=rsi
        )
        games_output.append({
            "Title": "JOGO 3: HEDGE (EXCLUSÃO)",
            "Game": g3,
            "Type": "DEFESA",
            "Reason": f"Algoritmo baniu {sorted(list(banned_g3))}. Forçou 8 repetidas (Limite Inferior)."
        })
        
        # RENDER RESULTS
        txt_download = ""
        for g_data in games_output:
            nums = g_data["Game"]
            if not nums: continue # Skip errors
            
            txt_download += f"{g_data['Title']}: {nums}\n"
            rep_count = len(set(nums) & last_draw_set)
            
            # CSS Logic
            tag_class = "success-tag" if 8 <= rep_count <= 10 else "fail-tag"
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div class='card-header'>
                        <span style='color:#fff; font-weight:bold'>{g_data['Title']}</span>
                        <span style='background:#333; padding:2px 8px; border-radius:4px; font-size:12px'>{g_data['Type']}</span>
                    </div>
                    <div class='reason-text'>{g_data['Reason']}</div>
                    <div style='margin-bottom:10px; font-size:12px; color:#666;'>
                        REPETIDAS: <span class='{tag_class}'>{rep_count}</span> | SOMA: {sum(nums)}
                    </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(5)
                html = ""
                for n in nums:
                    css = ""
                    if n in critical: css = "b-fixa"
                    elif n in last_draw_set: css = "b-rep"
                    html += f"<div class='ball {css}'>{n:02d}</div>"
                st.markdown(f"<div class='ball-grid'>{html}</div></div>", unsafe_allow_html=True)

        st.download_button("💾 DOWNLOAD BUFFER", txt_download, "system_v9.txt")