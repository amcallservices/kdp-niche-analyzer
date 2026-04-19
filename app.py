import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE SUITE ELITE & UI PERSONALIZZATA
# ==============================================================================
st.set_page_config(
    page_title="KDP NICHE ANALYZER ELITE v.2026",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Iniezione CSS per Sidebar Dark, Fissa e Metriche ad alto contrasto
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR DARK */
        section[data-testid="stSidebar"] {
            min-width: 400px !important;
            max-width: 400px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #f0f6fc !important;
        }
        [data-testid="stSidebar"] input {
            background-color: #161b22 !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }

        /* METRICHE */
        .stMetric {
            background-color: #ffffff !important;
            border: 1px solid #d0d7de !important;
            border-left: 8px solid #f78166 !important;
            padding: 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
        }
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }

        /* BOX STRATEGICI */
        .strategy-card {
            background-color: #f6f8fa;
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #d0d7de;
            margin-bottom: 10px;
        }
        .highlight { color: #0969da; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI BUSINESS (GRATUITA & API-LESS)
# ==============================================================================
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

class KDPFreeTools:
    """Strumenti di analisi gratuita senza API aggiuntive."""
    
    @staticmethod
    def get_amazon_suggestions(keyword, mkt_code):
        """Simula Publisher Rocket: estrae i suggerimenti reali di Amazon Autocomplete."""
        mkt_map = {"Italia": "it", "USA": "com", "Spagna": "es", "Francia": "fr", "Germania": "de"}
        suffix = mkt_map.get(mkt_code, "it")
        url = f"https://completion.amazon.com/api/2017/suggestions?limit=10&prefix={urllib.parse.quote(keyword)}&alias=stripbooks&mid=ATVPDKIKX0DER"
        if suffix == "it": url = url.replace("com", "it").replace("ATVPDKIKX0DER", "APJ6JRA9NG5V4")
        
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return [s['value'] for s in r.json()['suggestions']]
        except: return []
        return []

    @staticmethod
    def get_google_trends_link(keyword):
        """Genera link gratuito a Google Trends."""
        encoded = urllib.parse.quote(keyword)
        return f"https://trends.google.it/trends/explore?q={encoded}&date=today%2012-m"

class KDPBrain:
    @staticmethod
    def estimate_sales(bsr):
        if bsr <= 0: return 0
        if bsr <= 1500: return 500
        if bsr <= 10000: return 180
        if bsr <= 50000: return 40
        if bsr <= 100000: return 12
        return 2

    @staticmethod
    def calculate_royalty(price, pages, is_color):
        if price <= 0: return 0.0
        cost = 2.15 if not is_color else 0.60 + (pages * 0.045)
        if pages > 108 and not is_color: cost = 0.60 + (pages * 0.012)
        royalty = (price * 0.60) - cost
        return round(royalty, 2) if royalty > 0 else 0.0

# ==============================================================================
# 3. CORE SCRAPER (FOCALIZZATO LIBRI)
# ==============================================================================
def scrape_amazon_elite(mkt, keyword, pages, color_mode):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    country = 'it' if mkt == "Italia" else 'us'
    
    # &i=stripbooks garantisce solo Libri ed Ebook
    url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        res = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': url, 'render': 'true', 'country_code': country})
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
        data = []
        p_bar = st.progress(0)
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            bsr = 0
            is_self = False
            link_tag = item.find('a', class_='a-link-normal s-no-outline')
            if link_tag:
                p_url = f"https://www.{domain}" + link_tag['href']
                # Deep scan per BSR ed Editore
                res_p = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': p_url, 'country_code': country})
                if res_p.status_code == 200:
                    ps = BeautifulSoup(res_p.text, 'html.parser').get_text().lower()
                    m = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', ps)
                    if m: bsr = int(m.group(1).replace('.', '').replace(',', ''))
                    is_self = any(x in ps for x in ["indipendentemente pubblicato", "independently published", "kdp"])

            roy = KDPBrain.calculate_royalty(price, pages, color_mode == "A Colori")
            sales = KDPBrain.estimate_sales(bsr)
            
            data.append({
                "Copertina": img, "Titolo": title, "Prezzo": price, 
                "Royalty Netta": f"{roy} €", "Recensioni": reviews, 
                "BSR": bsr if bsr > 0 else "N/D", "Vendite Est.": sales,
                "Profitto": f"{round(sales * roy, 2)} €", "Self-Pub": "Sì" if is_self else "No"
            })
            p_bar.progress((i + 1) / len(items))
            
        return pd.DataFrame(data)
    except: return None

# ==============================================================================
# 4. SIDEBAR STRATEGICA (DARK & FISSA)
# ==============================================================================
if 'kw' not in st.session_state: st.session_state['kw'] = ""

with st.sidebar:
    st.title("🛡️ KDP STRATEGY HUB")
    if st.button("🔄 NUOVA ANALISI", use_container_width=True):
        st.session_state['kw'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Ingegneria della Keyword")
    with st.expander("Generatore Strategico", expanded=True):
        arg = st.text_input("Argomento:", placeholder="es. Yoga")
        pub = st.text_input("Target:", placeholder="es. Anziani")
        ben = st.text_input("Beneficio:", placeholder="es. flessibilità")
        if arg and pub and ben:
            k1 = f"{arg} per {pub}: {ben}"
            if st.button(f"🎯 Usa: {k1}"): st.session_state['kw'] = k1; st.rerun()
            k2 = f"Manuale di {arg} per {pub} per {ben}"
            if st.button(f"📦 Usa: {k2}"): st.session_state['kw'] = k2; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Analisi", value=st.session_state['kw'])
    
    # SUGGERIMENTI GRATUITI (LIVE)
    if query:
        with st.expander("💡 Suggerimenti Autocomplete (Gratis)"):
            suggs = KDPFreeTools.get_amazon_data_suggestions(query, mkt) if 'query' in locals() else []
            for s in suggs:
                if st.button(f"🔎 {s}", key=s):
                    st.session_state['kw'] = s; st.rerun()

    st.markdown("---")
    pgs = st.number_input("Pagine", min_value=24, value=120)
    stampa = st.selectbox("Stampa", ["Bianco e Nero", "A Colori"])
    
    run = st.button("AVVIA DEEP SCAN", type="primary", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD RISULTATI
# ==============================================================================
if run and query:
    st.header(f"📊 Business Intelligence: {query.upper()}")
    
    # Link a Google Trends (Gratis)
    trends_url = KDPFreeTools.get_google_trends_link(query)
    st.markdown(f"🔗 [Apri Analisi Trend su Google (Gratis)]({trends_url})")

    with st.spinner("Scansione editoriale in corso..."):
        df = scrape_amazon_elite(mkt, query, pgs, stampa)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
            
            # Calcolo Metriche
            df['Profit_N'] = df['Profitto'].str.replace(' €', '').astype(float)
            df['Royalty_N'] = df['Royalty Netta'].str.replace(' €', '').astype(float)
            avg_p = df['Prezzo'].mean()
            avg_r = df['Royalty_N'].mean()
            s_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_r:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(s_ratio)}%")
            
            # Sostenibilità ADS (Funzione Gratis)
            ads_check = "SÌ" if avg_r > 3.50 else "NO"
            c4.metric("Sostenibilità ADS", ads_check, help="Se la royalty è sotto i 3.50€, fare Ads è molto rischioso.")

            st.markdown("---")
            col_l, col_r = st.columns(2)
            with col_l:
                st.subheader("📝 Verdetto di Fattibilità")
                if s_ratio > 40 and avg_p > 12.90:
                    st.success("✅ **NICCHIA VALIDATA**: Alta presenza di Self-Publisher e margini sani per le Ads.")
                else:
                    st.warning("⚠️ **ATTENZIONE**: Nicchia dominata da grandi brand o margini troppo bassi.")

            with col_r:
                st.subheader("🧠 Suggerimento Strategico")
                st.info(f"Punta su un titolo che includa '{query}' e aggiungi un sottotitolo focalizzato sul 'Beneficio' inserito nella sidebar.")
        else:
            st.error("Errore di connessione. Riprova tra un minuto.")
