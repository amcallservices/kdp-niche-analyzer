import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# 1. Configurazione Pagina - Forza lo stato espanso all'avvio
st.set_page_config(
    page_title="KDP Niche Analyzer Ultimate 2026", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="expanded" # Forza la sidebar aperta all'avvio
)

# 2. CSS per UI Professionale, RIMOZIONE MENU E SIDEBAR FISSA
st.markdown("""
    <style>
        /* Nasconde il menu in alto a destra e il footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* BLOCCA LA SIDEBAR: Nasconde il pulsante "X" o la freccia per chiuderla */
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* Rende la sidebar non richiudibile e fissa */
        section[data-testid="stSidebar"] {
            min-width: 350px !important;
            max-width: 350px !important;
        }

        /* Opzionale: Rimuove il margine superiore */
        .block-container {
            padding-top: 1rem;
        }
        
        /* Stile Metriche */
        .stMetric { 
            background-color: #ffffff !important; 
            padding: 15px; 
            border-radius: 10px; 
            border: 1px solid #e0e0e0; 
            border-left: 5px solid #ff9900; 
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05); 
        }
        [data-testid="stMetricValue"] { color: #1e1e1e !important; font-size: 1.8rem !important; }
        [data-testid="stMetricLabel"] { color: #555555 !important; font-weight: bold !important; }
        
        /* Box Keyword */
        .keyword-box { 
            padding: 12px; 
            background-color: #f0f7f9; 
            color: #004455 !important; 
            border-radius: 8px; 
            margin-bottom: 12px; 
            border-left: 5px solid #00a8cc; 
            font-weight: 500;
        }
    </style>
""", unsafe_allow_html=True)

# LA TUA CHIAVE API
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

# Inizializzazione Session State
if 'target_keyword' not in st.session_state:
    st.session_state['target_keyword'] = ""

# --- FUNZIONI DI CALCOLO ---

def stima_vendite_mensili(bsr):
    if bsr <= 0: return 0
    if bsr <= 1000: return 600
    if bsr <= 5000: return 200
    if bsr <= 15000: return 90
    if bsr <= 50000: return 30
    if bsr <= 100000: return 10
    return 2

def calcola_royalty_netta(prezzo, pagine, colore):
    if prezzo <= 0: return 0.0
    if colore == "Bianco e Nero":
        costo_stampa = 2.15 if pagine <= 108 else 0.60 + (pagine * 0.012)
    else: 
        costo_stampa = 0.60 + (pagine * 0.042)
        if costo_stampa < 2.15: costo_stampa = 2.15
    royalty = (prezzo * 0.60) - costo_stampa
    return round(royalty, 2) if royalty > 0 else 0.0

# --- CORE SCRAPER (15 LIBRI + DEEP SCAN) ---

def get_amazon_data(marketplace, keyword, pagine, colore):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(marketplace, "amazon.it")
    country = 'it' if marketplace == "Italia" else 'us'
    
    # Forza la ricerca esclusivamente nella categoria Libri
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        res = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': target_url, 'render': 'true', 'country_code': country})
        if res.status_code != 200: return None
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
        results = []
        progress_bar = st.progress(0)
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            img_tag = item.find('img', class_='s-image')
            cover_url = img_tag['src'] if img_tag else ""
            
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}") if p_whole and p_frac else 0.0
            
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            bsr = 0
            is_self = False
            link_tag = item.find('a', class_='a-link-normal s-no-outline')
            if link_tag:
                book_url = f"https://www.{domain}" + link_tag['href']
                res_d = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': book_url, 'country_code': country})
                if res_d.status_code == 200:
                    d_soup = BeautifulSoup(res_d.text, 'html.parser').get_text().lower()
                    bsr_m = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', d_soup)
                    if bsr_m: bsr = int(bsr_m.group(1).replace('.', '').replace(',', ''))
                    is_self = "indipendentemente pubblicato" in d_soup or "independently published" in d_soup

            royalty = calcola_royalty_netta(price, pagine, colore)
            vendite = stima_vendite_mensili(bsr)
            
            results.append({
                "Copertina": cover_url, "Libro": title, "Prezzo": price, 
                "Royalty": royalty, "Recensioni": reviews, "BSR": bsr if bsr > 0 else "N/D",
                "Vendite/Mese": vendite, "Self-Pub": "Sì" if is_self else "No"
            })
            progress_bar.progress((i + 1) / len(items))
            
        return pd.DataFrame(results)
    except: return None

# --- UI SIDEBAR (ORA FISSA E SEMPRE APERTA) ---
with st.sidebar:
    st.title("🛡️ KDP Strategy Lab")
    if st.button("🔄 Reset Totale"):
        st.session_state['target_keyword'] = ""
        st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Ingegneria della Keyword")
    with st.expander("Generatore Automatico", expanded=True):
        arg = st.text_input("Argomento:", placeholder="es. Yoga")
        pub = st.text_input("Target:", placeholder="es. Donne in Gravidanza")
        ben = st.text_input("Beneficio:", placeholder="es. Alleviare il mal di schiena")
        
        if arg and pub and ben:
            st.caption("Clicca per caricare la keyword:")
            k1 = f"{arg} per {pub}: {ben}"
            if st.button(f"🎯 {k1}"): 
                st.session_state['target_keyword'] = k1
                st.rerun()
            k2 = f"Esercizi di {arg} per {pub} per {ben}"
            if st.button(f"📦 {k2}"): 
                st.session_state['target_keyword'] = k2
                st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Mercato", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key_input = st.text_input("🔍 Keyword sotto Analisi", value=st.session_state['target_keyword'])
    pagine = st.number_input("Pagine stimate", min_value=24, value=120)
    colore = st.selectbox("Interno", ["Bianco e Nero", "A Colori (Premium)"])
    obiettivo = st.radio("Obiettivo:", ["Royalty", "Lead Gen", "Authority"])
    
    run = st.button("LANCIA ANALISI PROFONDA", type="primary", use_container_width=True)

# --- LOGICA MAIN ---
if run and key_input:
    with st.spinner("Analisi esclusiva su Libri ed Ebook in corso..."):
        df = get_amazon_data(mkt, key_input, pagine, colore)
        if df is not None:
            st.success("Dati Ricevuti!")
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
            
            avg_p = df["Prezzo"].mean()
            avg_r = df["Royalty"].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            
            st.markdown("---")
            st.header(f"📈 Verdetto Professionale: {key_input.upper()}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_r:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            
            score = 50
            if avg_p > 13: score += 20
            if self_ratio > 40: score += 20
            if df["Recensioni"].mean() < 200: score += 10
            c4.metric("Opportunity Score", f"{score}/100")

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📝 Analisi Fattibilità")
                if score >= 70: st.success("✅ **NICCHIA VALIDATA**")
                elif avg_p < 11: st.error("❌ **MARGINI INSUFFICIENTI**")
                else: st.warning("⚠️ **CONCORRENZA NOTEVOLE**")

            with col_b:
                st.subheader("💡 Espansione Nicchia")
                kw = key_input.lower()
                st.markdown(f"<div class='keyword-box'><b>Versione Workbook:</b> Libro di esercizi {kw}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='keyword-box'><b>Versione Strategica:</b> {kw} per principianti</div>", unsafe_allow_html=True)
        else:
            st.error("Errore di connessione. Riprova tra 60 secondi.")
