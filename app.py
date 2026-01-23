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
    page_title="LotoQuant | KERNEL V9.1",
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

    def get_rsi(self) -> Dict[int, float]:
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

# --- 4. DETERMINISTIC GENERATOR ---
def generate_game_deterministic(
    target_repeats: int, 
    mandatory_nums: Set[int], 
    banned_nums: Set[int],
    last_draw: Set[int],
    universe: Set[int],
    rsi_scores: Dict[int, float]
) -> Tuple[List[int], str]:
    
    # Pools
    pool_repeats = list(last_draw - banned_nums)
    pool_absents = list((universe - last_draw) - banned_nums)
    
    # Handle Mandatories
    mandatory_in_repeats = mandatory_nums.intersection(last_draw)
    mandatory_in_absents = mandatory_nums.intersection(universe - last_draw)
    
    if len(mandatory_in_repeats) > target_repeats: return [], "Error: Repeats overflow."
    
    # Select Repeats
    selected_repeats = list(mandatory_in_repeats)
    needed_repeats = target_repeats - len(selected_repeats)
    available_repeats = [x for x in pool_repeats if x not in selected_repeats]
    available_repeats.sort(key=lambda x: rsi_scores.get(x, 50), reverse=True) # Intelligent Sort
    
    if len(available_repeats) < needed_repeats: return [], "Error: Not enough repeats."
    selected_repeats += available_repeats[:needed_repeats]
    
    # Select Absents
    selected_absents = list(mandatory_in_absents)
    slots_left = 15 - len(selected_repeats) - len(selected_absents)
    available_absents = [x for x in pool_absents if x not in selected_absents]
    available_absents.sort(key=lambda x: rsi_scores.get(x, 50), reverse=True) # Intelligent Sort
    
    if len(available_absents) < slots_left: return [], "Error: Not enough absents."
    selected_absents += available_absents[:slots_left]
    
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
    
    # LISTA DE ATRASADOS CRÍTICOS (>2 JOGOS)
    critical = [k for k,v in delays.items() if v >= 2]
    critical.sort(key=lambda x: delays[x], reverse=True)
    
    st.title("LOTOQUANT KERNEL V9.1 (HARD HEDGE)")
    st.markdown(f"**CONCURSO:** {df.iloc[-1]['id']} | **STATUS:** 🟢 ONLINE")
    
    # HUD CORRIGIDO (MOSTRA TODOS)
    c1, c2 = st.columns(2)
    c1.info(f"🚨 **ATRASADOS CRÍTICOS:** {critical}")
    c2.success(f"♻️ **REPETIDAS TRAVADAS:** 9 / 10 / 8")

    if st.button("EXECUTAR SINTAXE DE GERAÇÃO"):
        games_output = []
        
        # --- GAME 1: SNIPER (9 Repetidas) ---
        # Fixa Ciclo + Top 2 Atrasados
        mandatories_g1 = set(cycle + critical[:2])
        g1, msg1 = generate_game_deterministic(
            target_repeats=9, 
            mandatory_nums=mandatories_g1,
            banned_nums=set(),
            last_draw=last_draw_set,
            universe=engine.universe,
            rsi_scores=rsi
        )
        games_output.append({
            "Title": "JOGO 1: SNIPER (9 REPETIDAS)",
            "Game": g1,
            "Type": "ATAQUE",
            "Reason": f"Obrigatório: {sorted(list(mandatories_g1))}. Completado com Melhores RSI."
        })
        
        # --- GAME 2: TENDÊNCIA (10 Repetidas) ---
        # Fixa Top 1 Atrasado
        mandatories_g2 = {critical[0]} if critical else set()
        g2, msg2 = generate_game_deterministic(
            target_repeats=10, 
            mandatory_nums=mandatories_g2,
            banned_nums=set(), 
            last_draw=last_draw_set,
            universe=engine.universe,
            rsi_scores=rsi
        )
        games_output.append({
            "Title": "JOGO 2: TENDÊNCIA (10 REPETIDAS)",
            "Game": g2,
            "Type": "MISTO",
            "Reason": f"Obrigatório: {list(mandatories_g2)}. Limite superior de repetidas."
        })

        # --- GAME 3: HARD HEDGE (8 Repetidas) ---
        # BANIR TODOS OS CRÍTICOS (HARD HEDGE)
        banned_g3 = set(critical + cycle)
        g3, msg3 = generate_game_deterministic(
            target_repeats=8, 
            mandatory_nums=set(),
            banned_nums=banned_g3,
            last_draw=last_draw_set,
            universe=engine.universe,
            rsi_scores=rsi
        )
        games_output.append({
            "Title": "JOGO 3: HEDGE (ZEBRA 8 REPETIDAS)",
            "Game": g3,
            "Type": "DEFESA",
            "Reason": f"🚫 EXCLUÍDOS: {sorted(list(banned_g3))}. Aposta na falha total dos atrasados."
        })
        
        # RENDER
        txt_download = ""
        for g_data in games_output:
            nums = g_data["Game"]
            if not nums: continue 
            
            txt_download += f"{g_data['Title']}: {nums}\n"
            rep_count = len(set(nums) & last_draw_set)
            
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
                    if n in critical: css = "b-fixa" # Roxo
                    elif n in last_draw_set: css = "b-rep" # Verde
                    html += f"<div class='ball {css}'>{n:02d}</div>"
                st.markdown(f"<div class='ball-grid'>{html}</div></div>", unsafe_allow_html=True)

        st.download_button("💾 DOWNLOAD BUFFER", txt_download, "system_v9.txt")