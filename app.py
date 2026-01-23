import streamlit as st
import pandas as pd
import requests
import numpy as np
import time
from typing import List, Set, Dict, Tuple, Optional
from io import StringIO
import re

# --- 1. CONFIGURAÇÃO SYSTEM KERNEL ---
st.set_page_config(
    page_title="LotoQuant | STRATEGIST V16.0",
    page_icon="♟️",
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
    
    .ball-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; margin-bottom: 15px; }
    .ball { 
        background: #000; border: 1px solid #333; color: #888; 
        border-radius: 50%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-weight: bold; 
    }
    
    .b-fixa { border-color: #a371f7; color: #a371f7; box-shadow: 0 0 5px #a371f744; } 
    .b-esq { border-color: #ff4b4b; color: #ff4b4b; box-shadow: 0 0 8px #ff4b4b44; } 
    .b-rep { border-color: #238636; color: #238636; }
    .b-gold { border-color: #f1c232; color: #f1c232; box-shadow: 0 0 5px #f1c23244; }
    
    /* Auditoria Texto */
    .audit-box { 
        background-color: #000; border-left: 4px solid #00ff00; 
        padding: 10px; font-size: 13px; color: #ccc; font-family: 'Consolas', monospace;
        white-space: pre-line;
    }
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

# --- 3. ENGINE ---
class LotoEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.last_draw = set(df.iloc[-1]['draw'])
        self.universe = set(range(1, 26))
        self.PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
        self.MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

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

# --- 4. THE SHERIFF (VALIDATOR V16) ---
def validate_game_tactical(
    game: List[int], 
    engine: LotoEngine, 
    target_odd: int, 
    strict_sum: bool = True
) -> Tuple[bool, str]:
    
    g_set = set(game)
    report = ""
    valid = True
    
    # 1. Pontas (01/02 e 24/25)
    ponta_ini = game[0] <= 2
    ponta_fim = game[-1] >= 24
    if ponta_ini and ponta_fim: report += f"Pontas: {game[0]:02d} / {game[-1]:02d} ✅\n"
    else: report += f"Pontas: {game[0]:02d} / {game[-1]:02d} ❌\n"; valid = False

    # 2. Ímpares (Soberano)
    impares = len([x for x in game if x % 2 != 0])
    pares = 15 - impares
    
    # Validação exata do alvo (8 ou 7)
    if impares == target_odd:
        report += f"Ímpares: {impares} | Pares: {pares} ✅ (Alvo Atingido)\n"
    else:
        # Tolerância de +/- 1 apenas se não for Zebra Estrita
        if abs(impares - target_odd) <= 0: # Sem tolerância para teste rigoroso
             report += f"Ímpares: {impares} | Pares: {pares} ❌ (Meta era {target_odd})\n"; valid = False
        else:
             report += f"Ímpares: {impares} ❌\n"; valid = False

    # 3. Moldura (9 ou 10)
    moldura = len(g_set.intersection(engine.MOLDURA))
    if 9 <= moldura <= 10: report += f"Moldura: {moldura} ✅\n"
    else: report += f"Moldura: {moldura} ❌\n"; valid = False

    # 4. Primos (4 a 6)
    n_primos = len(g_set.intersection(engine.PRIMOS))
    if 4 <= n_primos <= 6: report += f"Primos: {n_primos} ✅\n"
    else: report += f"Primos: {n_primos} ❌\n"; valid = False
        
    # 5. Soma (180 a 210) - RELAXÁVEL no J3
    soma = sum(game)
    if 180 <= soma <= 210: 
        report += f"Soma: {soma} ✅\n"
    else: 
        if strict_sum:
            report += f"Soma: {soma} ❌ (Rigorosa)\n"; valid = False
        else:
            report += f"Soma: {soma} ⚠️ (Liberada p/ manter Paridade)\n"
        
    # 6. Sequência (Max 4)
    max_seq = 0; curr_seq = 1
    for i in range(len(game)-1):
        if game[i+1] == game[i] + 1: curr_seq += 1
        else: max_seq = max(max_seq, curr_seq); curr_seq = 1
    max_seq = max(max_seq, curr_seq)
    
    if max_seq <= 4: report += f"Sequência Máx: {max_seq} ✅"
    else: report += f"Sequência Máx: {max_seq} ❌"
    
    return valid, report

# --- 5. THE GENERATOR (TACTICAL) ---
def generate_tactical_game(
    target_repeats: int, 
    mandatory_nums: Set[int], 
    banned_nums: Set[int],
    engine: LotoEngine,
    weights: Dict[int, float],
    target_odd_count: int, # NOVO: Meta explícita de ímpares
    strict_sum_rule: bool = True,
    max_attempts: int = 5000
) -> Tuple[List[int], str, str]:
    
    last_draw = engine.last_draw
    universe = engine.universe
    
    for _ in range(max_attempts):
        pool_repeats = list(last_draw - banned_nums)
        pool_absents = list((universe - last_draw) - banned_nums)
        
        np.random.shuffle(pool_repeats)
        np.random.shuffle(pool_absents)
        
        sel_rep = list(mandatory_nums.intersection(last_draw))
        sel_abs = list(mandatory_nums.intersection(universe - last_draw))
        
        need_rep = target_repeats - len(sel_rep)
        if len(pool_repeats) < need_rep: continue
        
        # Seleção com viés RSI
        pool_repeats.sort(key=lambda x: weights.get(x, 0), reverse=True)
        candidates_rep = pool_repeats[:need_rep + 6] 
        np.random.shuffle(candidates_rep)
        sel_rep += candidates_rep[:need_rep]
        
        slots = 15 - len(sel_rep) - len(sel_abs)
        if len(pool_absents) < slots: continue

        pool_absents.sort(key=lambda x: weights.get(x, 0), reverse=True)
        candidates_abs = pool_absents[:slots + 6]
        np.random.shuffle(candidates_abs)
        sel_abs += candidates_abs[:slots]
        
        candidate = sorted(sel_rep + sel_abs)
        
        # TRIBUNAL TÁTICO
        is_valid, report = validate_game_tactical(
            candidate, engine, target_odd_count, strict_sum_rule
        )
        
        if is_valid:
            return candidate, "JOGO APROVADO", report
    
    return [], "FALHA ESTATÍSTICA", ""

# --- 6. UI LAYER ---
df = fetch_data()

if df is not None:
    engine = LotoEngine(df)
    last_draw_set = engine.last_draw
    cycle = engine.get_cycle_missing()
    delays = engine.get_delays()
    rsi_weights = engine.get_rsi_score()
    last_contest = df.iloc[-1]
    
    # MAIN SCREEN
    critical_all = [k for k,v in delays.items() if v >= 2]
    critical_all.sort(key=lambda x: delays[x], reverse=True)
    
    # DIVISÃO DE FORÇAS (A e B)
    # Garante que temos pelo menos 2 números para cada lado. Se tiver menos de 4, repete.
    if len(critical_all) >= 4:
        squad_a = critical_all[:2] # Para J2
        squad_b = critical_all[2:4] # Para J3
    elif len(critical_all) >= 2:
        squad_a = [critical_all[0]]
        squad_b = [critical_all[1]]
    else:
        squad_a = critical_all
        squad_b = critical_all
    
    st.title("LOTOQUANT STRATEGIST V16.0")
    st.markdown(f"**CONCURSO:** {last_contest['id']} | **DIVISÃO TÁTICA:** A/B")
    
    c1, c2, c3 = st.columns(3)
    c1.success(f"🦅 **J1:** Força Total {critical_all}")
    c2.info(f"🌊 **J2:** Esquadrão A {squad_a}")
    c3.warning(f"🛡️ **J3:** Esquadrão B {squad_b}")

    if st.button("EXECUTAR ESTRATÉGIA MILITAR"):
        games_output = []
        progress_bar = st.progress(0)
        
        # --- JOGO 1: CARGA TOTAL ---
        # Regra: Todos os atrasados. 8 Ímpares.
        mandatories_g1 = set(cycle + critical_all) # Todos
        g1, status1, report1 = generate_tactical_game(
            9, mandatories_g1, set(), engine, rsi_weights, target_odd_count=8, strict_sum_rule=True
        )
        if g1:
            games_output.append({
                "Title": "JOGO 1: SNIPER (TOTAL)", "Game": g1, 
                "Reason": "Força Máxima + Padrão 8 Ímpares.", "Report": report1, "Special": mandatories_g1
            })
        progress_bar.progress(33)
        
        # --- JOGO 2: ESQUADRÃO A ---
        # Regra: Só Atrasados A. PROIBIDO Atrasados B. 8 Ímpares.
        mandatories_g2 = set(cycle + squad_a)
        # Banimos o Squad B para garantir a divisão, e alguns fillers do J1 para variar
        fillers_g1 = [x for x in g1 if x not in mandatories_g1]
        banned_g2 = set(squad_b) | set(fillers_g1[:3])
        
        g2, status2, report2 = generate_tactical_game(
            10, mandatories_g2, banned_g2, engine, rsi_weights, target_odd_count=8, strict_sum_rule=True
        )
        
        # Fallback: Se travar, libera os fillers do J1, mas mantém proibição do Squad B
        if not g2:
             g2, status2, report2 = generate_tactical_game(
                10, mandatories_g2, set(squad_b), engine, rsi_weights, target_odd_count=8, strict_sum_rule=True
            )

        if g2:
            report2 += f"\n⚔️ Divisão: Usou {squad_a}, Baniu {squad_b}."
            games_output.append({
                "Title": "JOGO 2: TENDÊNCIA (SQUAD A)", "Game": g2, 
                "Reason": "Divisão A + Padrão 8 Ímpares.", "Report": report2, "Special": mandatories_g2
            })
        progress_bar.progress(66)

        # --- JOGO 3: ESQUADRÃO B (ZEBRA) ---
        # Regra: Só Atrasados B. PROIBIDO Atrasados A. 7 Ímpares (Inverso).
        # + Resgate Global
        
        used_numbers = set(g1) | set(g2)
        forgotten_numbers = engine.universe - used_numbers
        
        # Obrigatórios: Squad B + Esquecidos
        mandatories_g3 = set(squad_b) | forgotten_numbers
        
        # Banidos: Squad A (Se possível)
        banned_g3 = set(squad_a)
        
        # Zebra: Meta 7 Ímpares. Strict Sum = False (Afrouxa soma pra garantir paridade)
        g3, status3, report3 = generate_tactical_game(
            8, mandatories_g3, banned_g3, engine, rsi_weights, target_odd_count=7, strict_sum_rule=False
        )
        
        # Fallback
        if not g3:
             g3, status3, report3 = generate_tactical_game(
                8, mandatories_g3, set(), engine, rsi_weights, target_odd_count=7, strict_sum_rule=False
            )

        if g3:
            report3 += f"\n⚔️ Divisão: Usou {squad_b}. Inverteu para 7 Ímpares."
            report3 += f"\n🔗 Resgate: {len(forgotten_numbers)} números."
            games_output.append({
                "Title": "JOGO 3: RESGATE (SQUAD B)", "Game": g3, 
                "Reason": "Divisão B + Zebra 7 Ímpares + Resgate.", "Report": report3, 
                "Special": set(squad_b), "Forgotten": forgotten_numbers 
            })
        progress_bar.progress(100)
        
        # RENDER
        for g_data in games_output:
            nums = g_data["Game"]
            if not nums: continue 
            
            special_nums = g_data.get("Special", set())
            forgotten_nums = g_data.get("Forgotten", set())
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div class='card-header'>
                        <span style='color:#fff; font-weight:bold'>{g_data['Title']}</span>
                        <span style='background:#333; padding:2px 8px; border-radius:4px; font-size:12px'>V16.0</span>
                    </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(5)
                html = ""
                for n in nums:
                    css = ""
                    if n in {1, 2, 24, 25}: css = "b-gold" 
                    elif n in forgotten_nums: css = "b-esq" 
                    elif n in special_nums: css = "b-fixa" 
                    elif n in last_draw_set: css = "b-rep" 
                    html += f"<div class='ball {css}'>{n:02d}</div>"
                st.markdown(f"<div class='ball-grid'>{html}</div>", unsafe_allow_html=True)
                
                st.markdown(f"<div class='audit-box'>{g_data['Report']}</div></div>", unsafe_allow_html=True)

else:
    st.error("Erro de conexão. Tente recarregar.")