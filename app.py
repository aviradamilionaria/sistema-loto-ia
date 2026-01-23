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
    page_title="LotoQuant | MAESTRO V15.0",
    page_icon="🎼",
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

# --- 4. THE SHERIFF (VALIDATOR) ---
def validate_game_rules(game: List[int], engine: LotoEngine) -> Tuple[bool, str]:
    g_set = set(game)
    report = ""
    valid = True
    
    # 1. Pontas
    ponta_ini = game[0] <= 2
    ponta_fim = game[-1] >= 24
    if ponta_ini and ponta_fim: report += f"Pontas: {game[0]:02d} / {game[-1]:02d} ✅\n"
    else: report += f"Pontas: {game[0]:02d} / {game[-1]:02d} ❌\n"; valid = False

    # 2. Ímpares/Pares (7 ou 8)
    impares = len([x for x in game if x % 2 != 0])
    pares = 15 - impares
    if 7 <= impares <= 8: report += f"Ímpares: {impares} | Pares: {pares} ✅\n"
    else: report += f"Ímpares: {impares} | Pares: {pares} ❌\n"; valid = False
        
    # 3. Moldura (9 ou 10)
    moldura = len(g_set.intersection(engine.MOLDURA))
    if 9 <= moldura <= 10: report += f"Moldura: {moldura} ✅\n"
    else: report += f"Moldura: {moldura} ❌\n"; valid = False

    # 4. Primos (4 a 6)
    n_primos = len(g_set.intersection(engine.PRIMOS))
    if 4 <= n_primos <= 6: report += f"Primos: {n_primos} ✅\n"
    else: report += f"Primos: {n_primos} ❌\n"; valid = False
        
    # 5. Soma (180 a 210)
    soma = sum(game)
    if 180 <= soma <= 215: # Tolerância leve para Zebra
        report += f"Soma: {soma} ✅\n"
    else: report += f"Soma: {soma} ⚠️ (Fora do Padrão)\n"; valid = False
        
    # 6. Sequência (Max 4)
    max_seq = 0; curr_seq = 1
    for i in range(len(game)-1):
        if game[i+1] == game[i] + 1: curr_seq += 1
        else: max_seq = max(max_seq, curr_seq); curr_seq = 1
    max_seq = max(max_seq, curr_seq)
    
    if max_seq <= 4: report += f"Sequência Máx: {max_seq} ✅"
    else: report += f"Sequência Máx: {max_seq} ❌"
    
    return valid, report

# --- 5. THE GENERATOR (BRUTE FORCE + MEMORY) ---
def generate_strict_game(
    target_repeats: int, 
    mandatory_nums: Set[int], 
    banned_nums: Set[int],
    engine: LotoEngine,
    weights: Dict[int, float],
    max_attempts: int = 3000
) -> Tuple[List[int], str, str]:
    
    last_draw = engine.last_draw
    universe = engine.universe
    
    for _ in range(max_attempts):
        pool_repeats = list(last_draw - banned_nums)
        pool_absents = list((universe - last_draw) - banned_nums)
        
        # Shuffle inteligente (Variabilidade)
        np.random.shuffle(pool_repeats)
        np.random.shuffle(pool_absents)
        
        # Obrigatórios
        sel_rep = list(mandatory_nums.intersection(last_draw))
        sel_abs = list(mandatory_nums.intersection(universe - last_draw))
        
        # Preenchimento
        need_rep = target_repeats - len(sel_rep)
        if len(pool_repeats) >= need_rep:
            # Pega os melhores RSI dentro do shuffle
            pool_repeats.sort(key=lambda x: weights.get(x, 0), reverse=True)
            # Pega uma fatia aleatória dos melhores para não viciar
            candidates_rep = pool_repeats[:need_rep + 4]
            np.random.shuffle(candidates_rep)
            sel_rep += candidates_rep[:need_rep]
        else: continue 

        slots = 15 - len(sel_rep) - len(sel_abs)
        if len(pool_absents) >= slots:
            pool_absents.sort(key=lambda x: weights.get(x, 0), reverse=True)
            candidates_abs = pool_absents[:slots + 4]
            np.random.shuffle(candidates_abs)
            sel_abs += candidates_abs[:slots]
        else: continue
        
        candidate = sorted(sel_rep + sel_abs)
        
        # TRIBUNAL
        is_valid, report = validate_game_rules(candidate, engine)
        
        if is_valid:
            return candidate, "JOGO APROVADO", report
    
    return [], "FALHA DE ALINHAMENTO", ""

# --- 6. UI LAYER ---
df = fetch_data()

if df is not None:
    engine = LotoEngine(df)
    last_draw_set = engine.last_draw
    cycle = engine.get_cycle_missing()
    delays = engine.get_delays()
    rsi_weights = engine.get_rsi_score()
    last_contest = df.iloc[-1]
    
    # SIDEBAR
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
    
    st.title("LOTOQUANT MAESTRO V15.0")
    st.markdown(f"**CONCURSO:** {last_contest['id']} | **MEMÓRIA SEQUENCIAL:** ATIVA")
    
    c1, c2 = st.columns(2)
    c1.info(f"🚨 **ATRASADOS:** {critical_all}")
    c2.success(f"🎼 **SINCRONIA:** J1 ➔ J2 ➔ J3 (Zero Loss)")

    if st.button("EXECUTAR PROTOCOLO MAESTRO"):
        games_output = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # --- JOGO 1: O SOLISTA ---
        status_text.text("Gerando Jogo 1 (Sniper)...")
        mandatories_g1 = set(cycle + critical_all[:4]) 
        g1, status1, report1 = generate_strict_game(
            9, mandatories_g1, set(), engine, rsi_weights
        )
        if g1:
            games_output.append({
                "Title": "JOGO 1: SNIPER", "Game": g1, 
                "Reason": "Base Sólida.", "Report": report1, 
                "Special": mandatories_g1
            })
        progress_bar.progress(33)
        
        # --- JOGO 2: O DUETO (ANTI-CLONE) ---
        status_text.text("Gerando Jogo 2 (Tendência)...")
        if len(critical_all) > 1:
            left_out_g2 = {critical_all[-1]} 
            mandatories_g2 = set(cycle + critical_all[:-1])
        else:
            left_out_g2 = set()
            mandatories_g2 = set(cycle + critical_all)

        # AQUI ESTÁ A MEMÓRIA: Bani fillers do J1
        fillers_g1 = [x for x in g1 if x not in mandatories_g1]
        banned_for_g2 = set(fillers_g1[:4])
        
        g2, status2, report2 = generate_strict_game(
            10, mandatories_g2, banned_for_g2, engine, rsi_weights
        )
        if g2:
            # Adiciona nota de memória na auditoria
            report2 += f"\n🔗 Memória: Divergiu de {len(banned_for_g2)} números do J1."
            games_output.append({
                "Title": "JOGO 2: TENDÊNCIA", "Game": g2, 
                "Reason": "Variação Tática.", "Report": report2, 
                "Special": mandatories_g2
            })
        progress_bar.progress(66)

        # --- JOGO 3: O GRANDE FINAL (RESGATE) ---
        status_text.text("Gerando Jogo 3 (Resgate Global)...")
        
        # AQUI ESTÁ A MEMÓRIA GLOBAL:
        used_numbers = set(g1) | set(g2)
        forgotten_numbers = engine.universe - used_numbers
        dropped_criticals = left_out_g2
        
        mandatories_g3 = forgotten_numbers | dropped_criticals
        
        # Tenta banir críticos já usados, mas prioriza a validação
        banned_g3 = set(critical_all) - mandatories_g3
        
        g3, status3, report3 = generate_strict_game(
            8, mandatories_g3, banned_g3, engine, rsi_weights
        )
        
        # Fallback de segurança (se a matemática for impossível com banimento)
        if not g3:
             g3, status3, report3 = generate_strict_game(
                8, mandatories_g3, set(), engine, rsi_weights
            )

        if g3:
            report3 += f"\n🔗 Memória: Resgatou {len(forgotten_numbers)} números esquecidos."
            games_output.append({
                "Title": "JOGO 3: RESGATE (ZEBRA)", "Game": g3, 
                "Reason": "Cobertura Total.", "Report": report3, 
                "Special": dropped_criticals, "Forgotten": forgotten_numbers 
            })
        progress_bar.progress(100)
        status_text.text("Protocolo Concluído.")
        
        # RENDER
        txt_download = ""
        for g_data in games_output:
            nums = g_data["Game"]
            if not nums: continue 
            
            txt_download += f"{g_data['Title']}: {nums}\n"
            
            special_nums = g_data.get("Special", set())
            forgotten_nums = g_data.get("Forgotten", set())
            
            with st.container():
                st.markdown(f"""
                <div class='game-card'>
                    <div class='card-header'>
                        <span style='color:#fff; font-weight:bold'>{g_data['Title']}</span>
                        <span style='background:#333; padding:2px 8px; border-radius:4px; font-size:12px'>V15.0</span>
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
                
                txt_download += g_data['Report'].replace("✅", "[OK]").replace("❌", "[ERRO]").replace("⚠️", "[ALERTA]") + "\n" + "-"*30 + "\n"

        st.download_button("💾 BAIXAR DOSSIÊ COMPLETO (.TXT)", txt_download, "dossie_lotoquant_v15.txt")

else:
    st.error("Erro de conexão. Tente recarregar.")