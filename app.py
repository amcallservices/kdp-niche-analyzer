import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE SUITE ELITE & UI (SIDEBAR DARK E FISSA)
# ==============================================================================
st.set_page_config(
    page_title="KDP NICHE, PERSONA & EDITORIAL ANALYZER",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR DARK STYLE */
        section[data-testid="stSidebar"] {
            min-width: 420px !important;
            max-width: 420px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p { color: #f0f6fc !important; }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important;
        }

        /* METRICHE */
        .stMetric {
            background-color: #ffffff !important; border: 1px solid #d0d7de !important;
            border-left: 8px solid #0969da !important; padding: 20px !important;
            border-radius: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
        }
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }

        /* CARTE EDITORIALI */
        .editorial-card {
            background-color: #ffffff; border: 1px solid #e1e4e8;
            padding: 25px; border-radius: 12px; margin-bottom: 20px;
            border-top: 5px solid #f78166; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .title-option { color: #cf222e; font-size: 1.3rem; font-weight: bold; margin-bottom: 10px; display: block; }
        .plot-text { color: #24292f; font-style: italic; line-height: 1.6; }
        .persona-card {
            background-color: #f0f9ff; border: 1px solid #bae6fd;
            padding: 20px; border-radius: 10px; color: #0369a1;
            margin-bottom: 20px; border-left: 5px solid #0369a1;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI BUSINESS E GENERATORE CREATIVO
# ==============================================================================
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

class KDPFreeTools:
    @staticmethod
    def get_amazon_suggestions(keyword, mkt_code):
        mkt_map = {"Italia": "it", "USA": "com", "Spagna": "es", "Francia": "fr", "Germania": "de"}
        suffix = mkt_map.get(mkt_code, "it")
        url = f"https://completion.amazon.com/api/2017/suggestions?limit=10&prefix={urllib.parse.quote(keyword)}&alias=stripbooks&mid=ATVPDKIKX0DER"
        if suffix == "it": url = url.replace("com", "it").replace("ATVPDKIKX0DER", "APJ6JRA9NG5V4")
        try:
            r = requests.get(url)
            return [s['value'] for s in r.json()['suggestions']] if r.status_code == 200 else []
        except: return []

class KDPBrain:
    @staticmethod
    def estimate_sales(bsr):
        if bsr <= 0: return 0
        if bsr <= 1000: return 800
        if bsr <= 10000: return 200
        return 5

    @staticmethod
    def calculate_royalty(price, pages, is_color):
        if price <= 0: return 0.0
        cost = 2.15 if not is_color else 0.60 + (pages * 0.045)
        if pages > 108 and not is_color: cost = 0.60 + (pages * 0.012)
        return round((price * 0.60) - cost, 2)

    @staticmethod
    def generate_editorial_proposal(target, pain, dream, keyword):
        """Genera titoli e trama basati sulla Buyer Persona."""
        titles = [
            f"MAI PIÙ {pain.upper()}: Il Metodo Definitivo per {target} che vogliono {dream}",
            f"{keyword.title()}: La Guida Pratica per trasformare {pain} in {dream}",
            f"Oltre {pain.title()}: Strategie quotidiane per {target} alla ricerca di {dream}"
        ]
        plot = f"""
        Sei un {target} e ti senti esausto a causa di {pain}? Non sei solo. 
        In questo libro, scopriremo come abbattere finalmente le barriere che ti separano da {dream}. 
        Attraverso un percorso strutturato e testato, passeremo dalla frustrazione di {pain} alla libertà di {dream}. 
        Cosa troverai all'interno: tecniche pratiche, esercizi quotidiani e la mentalità necessaria per cambiare rotta. 
        Smetti di subire {pain} e inizia oggi il tuo viaggio verso {dream}.
        """
        return titles, plot

# ==============================================================================
# 3. CORE SCRAPER (CATEGORICO LIBRI)
# ==============================================================================
def scrape_books(mkt, keyword, pages, is_color):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    country = 'it' if mkt == "Italia" else 'us'
    url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    try:
        res = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': url, 'render': 'true', 'country_code': country})
        if res.status_code != 200: return None
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        results = []
        p_bar = st.progress(0)
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            bsr = 0
            is_self = False
            link_tag = item.find('a', class_='a-link-normal s-no-outline')
            if link_tag:
                p_url = f"https://www.{domain}" + link_tag['href']
                res_p = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': p_url, 'country_code': country})
                if res_p.status_code == 200:
                    ps = BeautifulSoup(res_p.text, 'html.parser').get_text().lower()
                    m = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', ps)
                    if m: bsr = int(m.group(1).replace('.', '').replace(',', ''))
                    is_self = any(x in ps for x in ["indipendentemente pubblicato", "independently published", "kdp"])
            roy = KDPBrain.calculate_royalty(price, pages, is_color)
            sales = KDPBrain.estimate_sales(bsr)
            results.append({
                "Copertina": img, "Titolo": title, "Prezzo": price, 
                "Royalty_Val": roy, "BSR": bsr if bsr > 0 else "N/D", 
                "Vendite": sales, "Profitto": round(sales * roy, 2), "Self-Pub": "Sì" if is_self else "No"
            })
            p_bar.progress((i + 1) / len(items))
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 4. SIDEBAR: PERSONA LAB (DARK & FISSA)
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY COMMAND")
    if st.button("🔄 NUOVA ANALISI", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("👤 Identikit Persona")
    with st.expander("Definisci Lettore", expanded=True):
        p_target = st.text_input("Chi è il lettore?", placeholder="es. Imprenditori stressati")
        p_pain = st.text_input("Qual è il suo dolore?", placeholder="es. insonnia da lavoro")
        p_dream = st.text_input("Cosa desidera?", placeholder="es. dormire 8 ore filate")
    
    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Focus", value=st.session_state['kw_active'])
    
    if query:
        with st.expander("💡 Suggerimenti Autocomplete"):
            suggs = KDPFreeTools.get_amazon_suggestions(query, mkt)
            for s in suggs:
                if st.button(f"🔎 {s}", key=s): st.session_state['kw_active'] = s; st.rerun()

    st.markdown("---")
    pgs = st.number_input("Pagine", min_value=24, value=120)
    is_color = st.checkbox("Stampa a Colori")
    run = st.button("AVVIA ANALISI E REDAZIONE", type="primary", use_container_width=True)

# ==============================================================================
# 5. MAIN DASHBOARD: REPORT & REDAZIONE LIBRO
# =================================================).
# ==============================================================================
if run and query:
    st.header(f"📊 Report & Proposta Editoriale: {query.upper()}")
    
    st.markdown(f"""
    <div class="persona-card">
        <b>Target:</b> {p_target} | <b>Problema:</b> {p_pain} | <b>Soluzione desiderata:</b> {p_dream}
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Analisi di mercato e generazione proposta in corso..."):
        df = scrape_books(mkt, query, pgs, is_color)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
            
            # Statistiche
            avg_p = df['Prezzo'].mean()
            avg_roy = df['Royalty_Val'].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_roy:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")

            # SEZIONE 6: PROPOSTA EDITORIALE (NUOVA CARATTERISTICA)
            st.markdown("---")
            st.header("✍️ Proposta Editoriale Strategica")
            st.info("Sulla base della Buyer Persona definita e dei dati di mercato, ecco le migliori opzioni per il tuo libro:")
            
            titles, plot = KDPBrain.generate_editorial_proposal(p_target, p_pain, p_dream, query)
            
            col_titles, col_plot = st.columns([1, 1.5])
            
            with col_titles:
                st.subheader("📌 Titoli Consigliati (Hook)")
                for t in titles:
                    st.markdown(f"<div class='editorial-card'><span class='title-option'>{t}</span></div>", unsafe_allow_html=True)
            
            with col_plot:
                st.subheader("📖 Bozza Trama (Persuasiva)")
                st.markdown(f"""
                <div class='editorial-card'>
                    <p class='plot-text'>{plot}</p>
                    <hr>
                    <small><b>Suggerimento:</b> Usa questa trama come base per la tua descrizione Amazon (A+ Content o Blurb) focalizzandoti sui benefici emotivi.</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Errore di connessione o limiti Amazon raggiunti. Riprova tra 60 secondi.")
