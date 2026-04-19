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
st.set_page_config(page_title="KDP OMNI-REASONER 7.8", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #30363d; min-width: 450px !important; }
        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }
        .negative-verdict { background-color: #3d0a0a !important; color: #ff6b6b !important; padding: 30px; border-radius: 15px; text-align: center; font-weight: 900; border: 2px solid #ff6b6b; }
        .ebook-suggestion-card { background-color: #0b0e14 !important; border: 2px solid #ffd700 !important; padding: 25px !important; border-radius: 15px; margin-bottom: 20px !important; }
        .ebook-title { color: #ffd700 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; }
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

for key in ['results_df', 'ebook_ideas', 'score', 'kw_active', 'kw_logic']:
    if key not in st.session_state: st.session_state[key] = None if key != 'score' else 0

# ==============================================================================
# 3. MOTORE DI ESTRAZIONE CHIRURGICA (VERIDICITÀ DATI)
# ==============================================================================
def run_data_truth_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    unique_results = []
    seen_titles = set()
    p_bar = st.progress(0)
    
    for page in range(1, 15): 
        if len(unique_results) >= 100: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        # Forziamo browser=true per caricare i metadati nascosti (BSR e Publisher)
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(target_url)}&x-api-key={ANT_API_KEY}&browser=true&proxy_type=residential"
        
        try:
            response = requests.get(api_url, timeout=45)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                # Estrazione Titolo (Chiave per deduplicazione)
                title_elem = item.h2.text.strip() if item.h2 else "N/A"
                if title_elem in seen_titles or title_elem == "N/A": continue
                
                # --- ESTRAZIONE BSR (Logica Veritiera) ---
                # Cerchiamo nel testo dell'intero blocco o in span specifici
                full_text = item.get_text(separator=' ').lower()
                bsr = 0
                bsr_patterns = [r'n\.\s*([0-9.,]+)\s*in', r'posiziona\s*([0-9.,]+)\s*nella', r'rank\s*#?\s*([0-9.,]+)']
                for pattern in bsr_patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        bsr = int(match.group(1).replace('.', '').replace(',', ''))
                        break

                # --- RILEVAZIONE SELF-PUBLISHING (Logica Veritiera) ---
                is_self = "No"
                self_triggers = ['independently published', 'pubblicato indipendentemente', 'createspace', 'kdp', 'indipendente', 'self published']
                if any(trigger in full_text for trigger in self_triggers):
                    is_self = "Sì"

                # --- ESTRAZIONE PREZZO ---
                price = 0.0
                price_whole = item.find('span', 'a-price-whole')
                price_fraction = item.find('span', 'a-price-fraction')
                if price_whole and price_fraction:
                    price = float(f"{price_whole.text.replace(',','').replace('.','')}.{price_fraction.text}")
                
                if price > 0: # Solo se c'è un prezzo reale (escludiamo i non disponibili)
                    seen_titles.add(title_elem)
                    unique_results.append({
                        "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                        "Titolo": title_elem, 
                        "Prezzo": price, 
                        "BSR": bsr if bsr > 0 else "N/D", 
                        "Self": is_self
                    })
                
                if len(unique_results) >= 100: break
            p_bar.progress(len(unique_results) / 100)
        except: continue
    
    p_bar.empty()
    return pd.DataFrame(unique_results)

# ==============================================================================
# 4. SIDEBAR FISSA CON GENERI COMPLETI
# ==============================================================================
with st.sidebar:
    st.title("🛡️ DATA TRUTH LAB 7.8")
    if st.button("🔄 RESET"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"])
    p_target = st.text_input("Target")
    p_pain = st.text_input("Dolore")
    p_dream = st.text_input("Sogno")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        p = f"Genera UNA keyword Long-Tail per '{p_type}' rivolto a '{p_target}'. Dolore: {p_pain}. Rispondi: KEYWORD: [testo] | LOGICA: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()
        st.session_state.kw_logic = res.split("LOGICA:")[1].strip()

    if st.session_state.kw_active:
        st.info(f"**AI Logic:** {st.session_state.kw_logic}")
        final_q = st.text_input("Keyword da analizzare:", value=st.session_state.kw_active)
        mkt = st.selectbox("Mercato", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        run_btn = st.button("🚀 ANALIZZA 100 LIBRI (DATA TRUTH)", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: VERDETTO E ANALISI
# ==============================================================================
if 'run_btn' in locals() and run_btn and API_READY:
    with st.spinner("Estrazione dati veritieri in corso (100 libri)..."):
        df = run_data_truth_scan(mkt, final_q)
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
    st.header(f"📊 Report Veritiero: {final_q.upper()}")
    st.dataframe(st.session_state.results_df, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
    
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
        st.warning("⚠️ Parametri insufficienti: competizione troppo alta o margini ridotti.")
