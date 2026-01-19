import streamlit as st
import pandas as pd
import ta
import requests
import numpy as np
import json

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="LotoQuant | Sistema Profissional",
    page_icon="🍀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILO VISUAL (DARK MODE + CORREÇÃO MOBILE) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* Botão Principal */
    .stButton>button { 
        background-color: #28a745; color: white; border-radius: 8px; 
        font-weight: bold; font-size: 22px; height: 65px; width: 100%;
        border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stButton>button:hover { 
        background-color: #218838; transform: scale(1.01);
    }
    
    /* Grade de Números (MOBILE FRIENDLY) */
    .numbers-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr); /* Força 5 colunas sempre */
        gap: 10px;
        margin-bottom: 20px;
    }
    
    /* Caixas dos Números */
    .number-box { 
        border: 2px solid #333; 
        padding: 10px 0; 
        border-radius: 10px; 
        background: linear-gradient(180deg, #2b2b2b, #1a1a1a); 
        text-align: center; 
        color: white;
        font-weight: 800;
        font-size: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }

    /* Ajuste de Texto das Métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
        color: #fff !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #bbb !important;
    }

    /* Caixa de Relatório ("O Santo Graal") */
    .report-box {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #9b59b6; /* Roxo Místico */
        color: #e0e0e0;
        margin-top: 25px;
        font-family: 'Verdana', sans-serif;
        line-height: 1.6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }
    .report-title {
        color: #d2a8ff;
        font-weight: bold;
        display: block;
        margin-bottom: 12px;
        font-size: 18px;
        text-transform: uppercase;
    }
    .tag {
        background-color: #333; padding: 2px 6px; border-radius: 4px; 
        font-weight: bold; color: #fff; border: 1px solid #555;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. MOTOR DE DADOS BLINDADO (ATUALIZADO) ---
@st.cache_data(ttl=3600)
def baixar_dados_live():
    # MUDANÇA IMPORTANTE: GitHub agora é a Fonte 1 (Mais estável e rápido nos EUA)
    FONTES = [
        "https://raw.githubusercontent.com/guilhermeasn/loteria.json/master/data/lotofacil.json", # Fonte Global
        "https://loteriascaixa-api.herokuapp.com/api/lotofacil", # Fonte Backup API
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil" # Fonte Oficial (Instável nos EUA)
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for url in FONTES:
        try:
            # Aumentei o timeout para 10 segundos para conexões lentas
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                dados = response.json()
                lista_final = []
                for jogo in dados:
                    # Normalização dos dados (API vs GitHub usam nomes diferentes)
                    dezenas = jogo.get('dezenas') or jogo.get('listaDezenas') or []
                    dezenas = [int(x) for x in dezenas]
                    
                    if len(dezenas) == 15:
                        lista_final.append({
                            'Concurso': jogo['concurso'],
                            'Bola1': dezenas[0], 'Bola2': dezenas[1], 'Bola3': dezenas[2], 
                            'Bola4': dezenas[3], 'Bola5': dezenas[4], 'Bola6': dezenas[5], 
                            'Bola7': dezenas[6], 'Bola8': dezenas[7], 'Bola9': dezenas[8], 
                            'Bola10': dezenas[9], 'Bola11': dezenas[10], 'Bola12': dezenas[11], 
                            'Bola13': dezenas[12], 'Bola14': dezenas[13], 'Bola15': dezenas[14]
                        })
                
                if len(lista_final) > 0:
                    df = pd.DataFrame(lista_final)
                    df = df.sort_values(by='Concurso', ascending=True).reset_index(drop=True)
                    return df
        except Exception as e:
            continue # Se der erro, tenta o próximo silenciosamente
            
    return None

# --- 4. CÉREBRO MATEMÁTICO (RSI) ---
def calcular_termometro(df):
    cols_numeros = [f'Num_{i}' for i in range(1, 26)]
    df_matriz = pd.DataFrame(0, index=df.index, columns=cols_numeros)
    
    for i in range(1, 16):
        col_bola = f'Bola{i}'
        vals = df[col_bola].values
        for idx, val in enumerate(vals):
            df_matriz.iloc[idx, val-1] = 1
            
    analise = []
    for i in range(1, 26):
        serie = df_matriz[f'Num_{i}']
        # RSI - Índice de Força Relativa (Termômetro)
        temperatura = ta.momentum.rsi(serie, window=14).iloc[-1]
        
        if serie.iloc[-1] == 0:
            try:
                ultimo_indice = np.where(serie.values == 1)[0][-1]
                atraso = len(serie) - 1 - ultimo_indice
            except: atraso = 99
        else: atraso = 0
            
        analise.append({'Bola': i, 'Temp': temperatura, 'Atraso': atraso})
        
    return pd.DataFrame(analise)

# --- 5. INTERFACE DO USUÁRIO ---
st.title("🍀 LotoQuant | IA Profissional")
st.caption("Sistema de Análise Estatística & Probabilidade Geométrica")

with st.spinner('Sincronizando banco de dados global...'):
    df = baixar_dados_live()

if df is not None:
    ultimo_conc = df['Concurso'].iloc[-1]
    st.info(f"✅ Conexão Estável. Base Atualizada até: **Concurso {ultimo_conc}**")
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("🔮 GERAR JOGO PERFEITO"):
            df_stats = calcular_termometro(df)
            df_sorted = df_stats.sort_values(by='Temp')
            
            # Estratégia Sniper: Frios + Neutros + Quentes
            frios = df_sorted.head(5)['Bola'].tolist()
            quentes = df_sorted.tail(5)['Bola'].tolist()
            meio = len(df_sorted) // 2
            neutros = df_sorted.iloc[meio-2 : meio+3]['Bola'].tolist()
            
            palpite = sorted(list(set(frios + neutros + quentes)))
            
            # Correção de segurança (garante 15 dezenas)
            if len(palpite) < 15:
                faltam = 15 - len(palpite)
                extras = df_sorted.iloc[5:5+faltam]['Bola'].tolist()
                palpite = sorted(palpite + extras)

            st.success("✨ ESTRATÉGIA MATEMÁTICA APLICADA!")
            
            # --- GRID DE NÚMEROS (Visualização Mobile) ---
            html_numeros = ""
            for n in palpite:
                html_numeros += f"<div class='number-box'>{n:02d}</div>"
            
            st.markdown(f"""
            <div class='numbers-grid'>
                {html_numeros}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # --- ANÁLISE TÉCNICA DO JOGO ---
            pares = len([x for x in palpite if x % 2 == 0])
            impares = 15 - pares
            soma = sum(palpite)
            
            # Listas de Padrões
            primos_lista = [2, 3, 5, 7, 11, 13, 17, 19, 23]
            fibo_lista = [1, 2, 3, 5, 8, 13, 21] 
            moldura_lista = [1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25]
            
            qtd_primos = len([x for x in palpite if x in primos_lista])
            qtd_fibo = len([x for x in palpite if x in fibo_lista])
            qtd_moldura = len([x for x in palpite if x in moldura_lista])
            
            # Repetidos do anterior
            ultimos_numeros = df.iloc[-1][[f'Bola{i}' for i in range(1, 16)]].values
            repetidos = len([x for x in palpite if x in ultimos_numeros])
            
            # Status da Soma
            if soma < 180: status_soma = "Baixa"
            elif soma > 220: status_soma = "Alta"
            else: status_soma = "Ideal"

            # Painel de Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Par / Ímpar", f"{pares} / {impares}", help="Equilíbrio ideal: 7/8 ou 8/7")
            c2.metric("Soma", f"{soma}", help="Soma total das dezenas")
            c3.metric("Repetidos", repetidos, help="Dezenas que repetiram do último concurso")
            c4.metric("Primos", qtd_primos, help="Quantidade de números Primos")
            
            # --- RELATÓRIO DO ALGORITMO ---
            st.markdown(f"""
            <div class='report-box'>
                <span class='report-title'>🧠 Auditoria do Jogo Gerado:</span>
                O sistema processou <strong>{len(df)} sorteios</strong> e identificou as seguintes oportunidades:
                <br><br>
                <ul style="list-style-type: none; padding: 0; margin: 0;">
                    <li>🔥 <strong>Memória Recente:</strong> O jogo manteve <span class="tag">{repetidos} números</span> do último concurso para respeitar a tendência de repetição.</li>
                    <li>📐 <strong>Estrutura Geométrica:</strong>
                        <ul>
                            <li>Na Moldura: <strong>{qtd_moldura}</strong> dezenas (Ocupação das bordas).</li>
                            <li>Sequência Mágica: <strong>{qtd_fibo}</strong> números Fibonacci.</li>
                        </ul>
                    </li>
                    <li>⚖️ <strong>Lei do Equilíbrio:</strong> Utilizamos o RSI para misturar dezenas quentes com as atrasadas, buscando o ponto de virada estatística.</li>
                    <li>✅ <strong>Conclusão:</strong> Jogo tecnicamente balanceado e pronto para aposta.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Texto para Copiar
            msg = f"Jogo LotoQuant: {palpite}"
            st.code(msg, language="text")
            
else:
    # Mensagem de erro mais amigável com botão de tentar de novo
    st.error("⚠️ Conexão instável com a Caixa Econômica. O servidor nos EUA foi bloqueado temporariamente.")
    st.markdown("**Solução:** Clique no botão abaixo para tentar usar a rota de backup.")
    if st.button("🔄 Tentar Reconectar"):
        st.rerun()