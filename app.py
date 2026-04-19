import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (ETERNAL SIDEBAR & HIGH CONTRAST)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 7.6", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; 
            border-right: 1px solid #30363d;
            min-width: 450px !important;
        }

        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }

        /* BANNER VERDETTO NEGATIVO */
        .negative-verdict {
            background-color: #3d0a0a !important; color: #ff6b6b !important; padding: 30px; border-radius: 15px;
            text-align: center; font-weight: 900; font-size: 1.8rem; margin: 30px 0;
            border: 2px solid #ff6b6b; box-shadow: 0 0 20px rgba(255, 107, 107, 0.2);
        }

        .ebook-suggestion-card {
            background-color: #0b0e14 !important; border: 2px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
        }
        .ebook-title { color: #ffd700 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 8px; }
        .ebook-plot { color: #e6edf3 !important; line-height: 1.7 !important; font-size: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE API & PERSISTENZA
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ Configurazione OpenAI mancante.")
    API_READY = False

if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0

# ==============================================================================
# 3. MOTORE DI SCAN (UNIQUE CENTURION)
# ==============================================================================
def run_unique_centurion_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    unique_results = []
    seen_titles = set()
    p_bar = st.progress(0)
    
    for page in range(1, 15): 
        if len(unique_results) >= 100: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(target_url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
        try:
            response = requests.get(api_url, timeout=35)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            for item in items:
                item_text = item.get_text().lower()
                if not any(x in item_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
                title_elem = item.h2.text.strip() if item.h2 else "N/A"
                if title_elem in seen_titles or title_elem == "N/A": continue
                seen_titles.add(title_elem)
                price_match = re.search(r'([0-9]+[,.][0-9]{2})', item_text)
                price = float(price_match.group(1).replace(',', '.')) if price_match else 0.0
                unique_results.append({
                    "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                    "Titolo": title_elem, "Prezzo": price, "Self": "Sì" if "independently" in item_text else "No"
                })
                if len(unique_results) >= 100: break
            p_bar.progress(len(unique_results) / 100)
        except: continue
    p_bar.empty()
    return pd.DataFrame(unique_results)

# ==============================================================================
# 4. SIDEBAR (ALWAYS VISIBLE)
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 7.6")
    if st.button("🔄 NUOVA SESSIONE (Reset)"):
        for key in ['results_df', 'ebook_ideas', 'kw_active', 'score']: 
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    st.markdown("---")
    genere = st.selectbox("Genere", ["Saggio", "Manuale", "Business", "Romanzo", "Psicologico", "Ricettario"])
    target = st.text_input("Target", placeholder="es. Ingegneri")
    dolore = st.text_input("Problema", placeholder="es. gestione tempo")
    sogno = st.text_input("Risultato", placeholder="es. produttività")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        p = f"Genera UNA keyword Long-Tail per '{genere}' rivolto a '{target}'. Dolore: {dolore}. Rispondi: KEYWORD: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].strip()

    if 'kw_active' in st.session_state:
        final_q = st.text_input("Keyword da analizzare:", value=st.session_state.kw_active)
        mkt = st.selectbox("Mercato", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        run_btn = st.button("🚀 ANALIZZA 100 LIBRI UNICI", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: DECISION LOGIC
# ==============================================================================
if 'run_btn' in locals() and run_btn and API_READY:
    with st.spinner("Scansione in corso..."):
        df = run_unique_centurion_scan(mkt, final_q)
        if not df.empty:
            st.session_state.results_df = df
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13 else 0) + (30 if self_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_ebook = f"L'analisi per '{final_q}' è POSITIVA. Genera 3 titoli e 3 trame (100 parole) per eBook. Formato: TITOLO: [testo] | TRAMA: [testo]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_ebook}]).choices[0].message.content
            else:
                st.session_state.ebook_ideas = "NEGATIVE"

if st.session_state.results_df is not None:
    st.header(f"📊 Report: {final_q.upper()}")
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    # --- LOGICA DI VISUALIZZAZIONE CONDIZIONALE ---
    if st.session_state.score >= 60:
        st.success(f"✅ ANALISI POSITIVA ({st.session_state.score}/100)")
        st.header("🎯 Suggerimenti eBook")
        ebooks = st.session_state.ebook_ideas.split("TITOLO:")
        for eb in ebooks[1:]:
            parts = eb.split("| TRAMA:")
            if len(parts) > 1:
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {parts[0].strip()}</span><p class="ebook-plot">{parts[1].strip()}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="negative-verdict">❌ ANALISI NEGATIVA ({st.session_state.score}/100)</div>', unsafe_allow_html=True)
        st.warning("⚠️ Questa nicchia non ha parametri di profitto sufficienti. La competizione è troppo alta o i prezzi troppo bassi.")
        st.info("💡 **Consiglio dello Stratega AI:** Torna alla sidebar, modifica leggermente il Target o il Dolore e clicca di nuovo su **'GENERA KEYWORD AI'** per trovare un angolo d'attacco migliore.")
