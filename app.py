import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM: PREMIUM SAAS DASHBOARD (DUAL-PANEL)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 12.3", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp { background-color: #f9fafb !important; }

        /* MAIN SIDEBAR (LEFT) */
        section[data-testid="stSidebar"] { 
            background-color: #1f2937 !important; 
            min-width: 320px !important;
            border-right: 1px solid #374151;
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] * { 
            color: #f3f4f6 !important; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        
        /* INPUT STYLES */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #374151 !important;
            border: 1px solid #4b5563 !important;
            color: white !important;
            border-radius: 6px !important;
        }

        /* TITLES */
        .program-title { 
            color: #111827 !important; 
            font-size: 2rem !important; 
            font-weight: 800; 
            margin-bottom: 1rem; 
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0.5rem;
        }
        .section-title {
            color: #374151 !important; 
            font-size: 1.2rem !important; 
            font-weight: 700; 
            margin-bottom: 1rem;
            margin-top: 1rem;
        }

        /* METRICS */
        [data-testid="stMetricValue"] { color: #2563eb !important; font-weight: 800 !important; font-size: 1.8rem !important; }
        [data-testid="stMetricLabel"] p { color: #6b7280 !important; font-weight: 600 !important; text-transform: uppercase; font-size: 0.8rem; }
        .stMetric { background-color: white !important; border: 1px solid #e5e7eb; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

        /* DATAFRAME */
        [data-testid="stDataFrame"] {
            background-color: white; padding: 1rem; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
        }

        /* AI RIGHT PANEL (Simulated 2nd Sidebar) */
        .ai-panel {
            background-color: white;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            height: 100%;
        }

        /* EBOOK CARDS */
        .ebook-card {
            background-color: white; border: 1px solid #e5e7eb; border-left: 4px solid #3b82f6; 
            padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .ebook-title { color: #111827 !important; font-weight: 800; font-size: 1.1rem; margin-bottom: 0.5rem; }
        .ebook-plot { color: #4b5563 !important; font-size: 0.95rem; }

        /* BUTTONS */
        .stButton button { border-radius: 6px !important; font-weight: 600 !important; }
        button[kind="primary"] { background-color: #2563eb !important; color: white !important; border: none !important; }
        button[kind="primary"]:hover { background-color: #1d4ed8 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE STATO
# ==============================================================================
for key in ['raw_data', 'filtered_data', 'suggestions', 'search_kw', 'score']:
    if key not in st.session_state: st.session_state[key] = None if key != 'score' else 0

# ==============================================================================
# 3. MOTORE DI SCRAPING
# ==============================================================================
def get_amazon_data(domain, keyword):
    ANT_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"
    SCRAPERAPI_KEY = st.secrets.get("SCRAPERAPI_KEY", "")
    WEBSCRAPINGAI_KEY = st.secrets.get("WEBSCRAPINGAI_KEY", "")
    
    def fetch_with_triple_fallback(p):
        amazon_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={p}"
        try:
            r = requests.get(f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(amazon_url)}&x-api-key={ANT_KEY}&browser=true&proxy_type=residential", timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        try:
            r = requests.get(f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={urllib.parse.quote(amazon_url)}&render=true", timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        try:
            r = requests.get(f"https://api.webscraping.ai/html?api_key={WEBSCRAPINGAI_KEY}&url={urllib.parse.quote(amazon_url)}&proxy=residential&js=true", timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        pages = list(executor.map(fetch_with_triple_fallback, range(1, 11)))
    
    results, seen = [], set()
    for html in pages:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'}) or soup.select('.s-result-item[data-asin]')
        for item in items:
            title_el = item.h2 or item.select_one('.a-size-medium') or item.select_one('.a-size-base-plus')
            title = title_el.text.strip() if title_el else ""
            if not title or title in seen: continue
            
            text = item.get_text(separator=' ').lower()
            
            # BSR Parsing (aggiornato per supportare formati internazionali come "Nr.")
            bsr_match = re.search(r'(?:n\.|nr\.|n\.º|#|rank)\s*([0-9.,]+)', text)
            bsr = float(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else np.nan
            
            # Recensioni Parsing
            rev_el = item.select_one('.a-icon-alt')
            reviews = 0
            if rev_el:
                rev_text_container = item.select_one('.a-size-base.s-underline-text')
                if rev_text_container:
                    try: reviews = int(re.sub(r'[^\d]', '', rev_text_container.text))
                    except: pass
            
            is_self = "Independent" if any(x in text for x in ['independently', 'kdp', 'indipendente', 'createspace']) else "Publishing House"
            
            # Prezzo Parsing
            price = 0.0
            price_el = item.select_one('.a-price .a-offscreen')
            if price_el:
                try: price = float(re.sub(r'[^\d.,]', '', price_el.text).replace(',', '.'))
                except: price = 0.0
                
            seen.add(title)
            results.append({"Titolo": title, "Prezzo": price, "BSR": bsr if not np.isnan(bsr) else "N/D", "Recensioni": reviews, "Editore": is_self})
            if len(results) >= 100: break
    return pd.DataFrame(results)

# ==============================================================================
# 4. MAIN SIDEBAR (MARKETPLACE & RICERCA DATI)
# ==============================================================================
marketplaces = {
    "us Amazon.com (US)": "amazon.com",
    "gb Amazon.co.uk (UK)": "amazon.co.uk",
    "de Amazon.de (Germany)": "amazon.de",
    "fr Amazon.fr (France)": "amazon.fr",
    "it Amazon.it (Italy)": "amazon.it",
    "es Amazon.es (Spain)": "amazon.es",
    "ca Amazon.ca (Canada)": "amazon.ca"
}

with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>MARKETPLACE & CATEGORY</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace *", list(marketplaces.keys()))
    domain = marketplaces[mkt_choice]
    
    amazon_categories = ["All Departments", "Books", "Kindle Store", "Audible Books & Originals"]
    cat_choice = st.selectbox("Category", amazon_categories)
    
    pub_choice = st.selectbox("Publisher Type *", ["All Publishers", "Publishing House", "Independent"])
    
    st.markdown("---")
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>SEARCH PARAMETERS</p>", unsafe_allow_html=True)
    search_input = st.text_input("Enter Keyword *")
    
    if st.button("🔍 Search Keyword", type="primary", use_container_width=True):
        if not search_input: st.error("Inserisci una keyword.")
        else:
            with st.spinner("Estraggo dati dal mercato selezionato..."):
                df = get_amazon_data(domain, search_input)
                if not df.empty:
                    st.session_state.raw_data = df
                    st.session_state.search_kw = search_input
                    st.session_state.suggestions = None # Reset vecchie analisi
                else:
                    st.error("Nessun dato trovato o blocco di rete. Riprova.")
                    
    if st.button("🔄 Clear Data", use_container_width=True):
        for key in ['raw_data', 'filtered_data', 'suggestions', 'search_kw']: st.session_state[key] = None
        st.rerun()

# ==============================================================================
# 5. CORE LAYOUT: RISULTATI (LEFT) E PANNELLO AI (RIGHT)
# ==============================================================================
if st.session_state.raw_data is not None:
    
    # Applica filtro Editore
    df = st.session_state.raw_data
    if pub_choice != "All Publishers":
        df = df[df['Editore'] == pub_choice]
    st.session_state.filtered_data = df

    # Dividiamo lo schermo: 70% Dati Mercato, 30% Pannello AI Analisi
    col_data, col_ai = st.columns([7, 3], gap="large")

    # --- COLONNA SINISTRA: DATI MERCATO ---
    with col_data:
        st.markdown(f"<div class='section-title'>Risultati per: <span style='color: #2563eb;'>'{st.session_state.search_kw}'</span></div>", unsafe_allow_html=True)
        
        # Metriche
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Libri Trovati", len(df))
            c2.metric("Prezzo Medio", f"{df['Prezzo'].mean():.2f}")
            c3.metric("Recensioni Medie", f"{int(df['Recensioni'].mean())}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Mostra chiaramente Titolo, Prezzo, BSR, Recensioni ed Editore
            st.dataframe(df[['Titolo', 'BSR', 'Prezzo', 'Recensioni', 'Editore']], use_container_width=True, height=500, hide_index=True)
        else:
            st.warning(f"Nessun libro trovato per il filtro '{pub_choice}'. Prova a selezionare 'All Publishers'.")

    # --- COLONNA DESTRA: PANNELLO AI (L'Ulteriore Sidebar) ---
    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.9rem; color:#4b5563;'>Genera una strategia editoriale specifica per i dati appena estratti.</p>", unsafe_allow_html=True)
        
        target_ai = st.text_input("Target Lettore (Opzionale)", placeholder="es. Principianti, Donne, ecc.")
        format_ai = st.selectbox("Formato Libro", ["Manuale Pratico", "Saggio", "Guida Passo-Passo", "Workbook", "Romanzo"])
        
        if st.button("🪄 Analizza e Genera Ideazione", type="primary", use_container_width=True):
            if df.empty:
                st.error("Nessun dato su cui lavorare.")
            else:
                with st.spinner("Elaborazione AI..."):
                    # Calcolo Score Interno per validazione
                    avg_p = df['Prezzo'].mean()
                    base_score = 40 + (30 if avg_p > 10 else 0)
                    if base_score >= 40: # Abbassata la soglia per permettere sempre l'uso del lab
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        prompt_book = f"""
                        Agisci come un Publisher. Keyword target: '{st.session_state.search_kw}'. Mercato: {mkt_choice}. Target: {target_ai}. Formato: {format_ai}.
                        Genera 3 idee di libri ottimizzati. Formato TASSATIVO:
                        TITOLO: [Testo]
                        TRAMA: [Testo]
                        ---
                        """
                        st.session_state.suggestions = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
                    else:
                        st.session_state.suggestions = "NEGATIVE"
        
        # Stampa Risultati AI all'interno del pannello
        if st.session_state.suggestions == "NEGATIVE":
            st.error("Mercato troppo povero per generare idee profittevoli.")
        elif st.session_state.suggestions:
            st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
            clean_suggestions = st.session_state.suggestions.replace("**", "")
            matches = re.findall(r'TITOLO:\s*(.*?)\s*TRAMA:\s*(.*?)(?=\nTITOLO:|\n---|---|$)', clean_suggestions, re.IGNORECASE | re.DOTALL)
            
            if matches:
                for t_clean, p_clean in matches:
                    st.markdown(f"""
                    <div style='background-color:#f3f4f6; padding:1rem; border-radius:6px; margin-bottom:1rem; border-left:3px solid #10b981;'>
                        <div style='font-weight:700; color:#111827; font-size:1rem; margin-bottom:0.5rem;'>{t_clean.strip()}</div>
                        <div style='color:#4b5563; font-size:0.85rem; line-height:1.4;'>{p_clean.strip()}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write(st.session_state.suggestions)
                
        st.markdown("</div>", unsafe_allow_html=True)
else:
    # Schermata di benvenuto quando non ci sono dati
    st.info("👈 Usa il pannello laterale per selezionare il Marketplace ed effettuare la ricerca.")
