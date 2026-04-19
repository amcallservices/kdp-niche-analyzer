import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (ULTRA DARK & TRIPLE COMPARISON)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 5.0",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] {
            min-width: 480px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }

        /* FIX METRICHE */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; font-size: 1.8rem !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* WINNER BANNER */
        .winner-box {
            background-color: #238636; color: white; padding: 20px; border-radius: 12px;
            text-align: center; font-weight: 900; font-size: 1.5rem; margin-bottom: 30px;
            border: 2px solid #2ea043; box-shadow: 0 0 20px rgba(35, 134, 54, 0.4);
        }

        /* PIANO EDITORIALE - HIGH CONTRAST DARK */
        .editorial-container {
            background-color: #0d1117; 
            border: 2px solid #30363d; 
            padding: 35px; 
            border-radius: 15px; 
            margin-bottom: 25px; 
            border-top: 10px solid #ffd700;
        }
        .title-option { color: #ffd700 !important; font-size: 1.7rem; font-weight: 900; display: block; margin-bottom: 12px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .marketing-angle { color: #58a6ff !important; font-weight: 700; font-size: 1.1rem; margin-bottom: 15px; display: block; font-family: monospace; }
        .plot-detailed { color: #e6edf3 !important; line-height: 1.9; font-size: 1.1rem; white-space: pre-wrap; margin-bottom: 30px; }

        .keyword-card {
            background-color: #161b22; border: 1px solid #30363d; padding: 15px;
            border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #3182ce;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CLIENT SETUP & SECRETS
# ==============================================================================
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    WS_API_KEY = st.secrets["WS_API_KEY"]
    client = openai.OpenAI(api_key=OPENAI_KEY)
    API_READY = True
except Exception:
    st.error("⚠️ Configurazione Secret non trovata.")
    API_READY = False

# ==============================================================================
# 3. SURGICAL AI ENGINE (COMPARATIVE LOGIC)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_3_keywords(p_type, p_target, p_pain, p_dream):
        prompt = f"""
        Sei un Direttore Marketing KDP. Genera 3 diverse Keyword Long-Tail per un '{p_type}' rivolto a '{p_target}'.
        Problema: {p_pain} | Sogno: {p_dream}.
        REQUISITO: Restituisci SOLO le 3 keyword separate dal simbolo '||'. Senza numeri né introduzioni.
        Esempio: Keyword1 || Keyword2 || Keyword3
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Genera 5 proposte editoriali (Libri/Ebook) sulla keyword vincitrice: '{kw}'.
        Genere: {p_type} | Target: {p_target} | Problema: {p_pain} | Sogno: {p_dream}.
        Per ogni opzione: 1. TITOLO | 2. ANGOLO DI MARKETING | 3. TRAMA DETTAGLIATA (Almeno 200 parole).
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. DEEP SCAN ENGINE (50 LIBRI)
# ==============================================================================
def run_deep_scan(mkt, keyword, pages_count=120):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    for page_num in range(1, 4): # Ottimizzato per velocità su 3 scan
        if len(results) >= 40: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page_num}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=25)
            if response.status_code != 200: continue
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            for item in items:
                item_text = item.get_text().lower()
                book_triggers = ['copertina', 'pagine', 'kindle', 'formato', 'paperback', 'hardcover', 'editor', 'editore', 'ebook', 'volumi']
                if not any(x in item_text for x in book_triggers): continue

                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                
                title = item.h2.text.strip() if item.h2 else "N/A"
                results.append({
                    "Titolo": title, "Prezzo": price, 
                    "Self": 1 if "independently" in item_text or "pubblicato" in item_text else 0
                })
                if len(results) >= 40: break
        except: break
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR: LABORATORIO DI IDEAZIONE COMPARATIVA
# ==============================================================================
if 'kws' not in st.session_state: st.session_state['kws'] = []

with st.sidebar:
    st.title("⚔️ KDP NICHE BATTLE")
    st.info("L'AI analizzerà 3 strade diverse per la tua idea.")
    
    p_type = st.selectbox("Genere", ["Manuale Tecnico", "Saggio Scientifico", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario", "Spirituale / Esoterico"])
    p_target = st.text_input("Target", placeholder="es. Architetti")
    p_pain = st.text_input("Dolore", placeholder="es. burnout")
    p_dream = st.text_input("Sogno", placeholder="es. produttività calma")
    
    if st.button("🧠 GENERA 3 STRATEGIE", use_container_width=True, type="primary") and API_READY:
        res = SurgicalAI.brainstorm_3_keywords(p_type, p_target, p_pain, p_dream)
        st.session_state['kws'] = [k.strip() for k in res.split("||")]

    if st.session_state['kws']:
        st.markdown("### Keyword Identificate:")
        for i, k in enumerate(st.session_state['kws']):
            st.markdown(f'<div class="keyword-card"><b>OPZIONE {i+1}:</b><br>{k}</div>', unsafe_allow_html=True)

    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    run_all = st.button("🚀 LANCIA ANALISI COMPARATIVA", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: LA BATTAGLIA DELLE NICCHIE
# ==============================================================================
if run_all and st.session_state['kws'] and API_READY:
    st.header("🏁 Risultati della Comparazione Strategica")
    
    final_results = []
    cols = st.columns(3)
    
    for i, kw in enumerate(st.session_state['kws']):
        with cols[i]:
            st.subheader(f"Opzione {i+1}")
            st.caption(kw)
            with st.spinner(f"Analisi {kw}..."):
                df = run_deep_scan(mkt, kw)
                if not df.empty:
                    avg_p = df['Prezzo'].mean()
                    self_ratio = (df['Self'].sum() / len(df)) * 100
                    o_score = 40
                    if avg_p > 13.50: o_score += 30
                    if self_ratio > 40: o_score += 30
                    
                    st.metric("Score", f"{o_score}/100")
                    st.metric("Prezzo Medio", f"{avg_p:.2f} €")
                    st.metric("Indie Ratio", f"{int(self_ratio)}%")
                    
                    final_results.append({"kw": kw, "score": o_score, "price": avg_p, "self": self_ratio})
                else:
                    st.error("Nessun dato.")
                    final_results.append({"kw": kw, "score": 0, "price": 0, "self": 0})

    # CALCOLO VINCITORE
    if final_results:
        winner = max(final_results, key=lambda x: x['score'])
        
        st.markdown("---")
        st.markdown(f'<div class="winner-box">🏆 VINCITORE: {winner["kw"].upper()}</div>', unsafe_allow_html=True)
        
        if winner['score'] >= 60:
            with st.spinner("Redazione Master Plan per la nicchia vincente..."):
                plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, winner['kw'])
                
                # FORMATTAZIONE HIGH CONTRAST
                formatted_plan = (plan
                    .replace("TITOLO:", " <span class='title-option'>")
                    .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
                    .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                    .replace("1.", "<br><b>1.</b>").replace("2.", "<br><b>2.</b>")
                    .replace("3.", "<br><b>3.</b>").replace("4.", "<br><b>4.</b>")
                    .replace("5.", "<br><b>5.</b>")
                )
                st.markdown(f'<div class="editorial-container">{formatted_plan}</div> </div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ Nessuna delle nicchie analizzate ha superato lo score di 60. L'investimento è considerato ad alto rischio.")
