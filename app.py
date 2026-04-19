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
    page_title="KDP NICHE & PERSONA ANALYZER ELITE",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Iniezione CSS per Sidebar DARK, FISSA, Rimozione Menu e Grafica Professionale
st.markdown("""
    <style>
        /* Nasconde menu Streamlit e footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* BLOCCA LA SIDEBAR: Impedisce la chiusura */
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* --- SIDEBAR DARK STYLE --- */
        section[data-testid="stSidebar"] {
            min-width: 420px !important;
            max-width: 420px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }

        /* Testi in bianco per Sidebar Dark */
        [data-testid="stSidebar"] .stMarkdown p, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p {
            color: #f0f6fc !important;
        }

        /* Input Sidebar per contrasto Dark */
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }

        /* --- MAIN AREA STYLE --- */
        .stMetric {
            background-color: #ffffff !important;
            border: 1px solid #d0d7de !important;
            border-left: 8px solid #0969da !important;
            padding: 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
        }
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #656d76 !important; }

        /* PERSONA CARD */
        .persona-card {
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
            padding: 20px;
            border-radius: 10px;
            color: #0369a1;
            margin-bottom: 20px;
            border-left: 5px solid #0369a1;
        }

        /* KEYWORD SUGGESTION CARDS */
        .keyword-alt-card {
            background-color: #ffffff;
            border: 1px solid #e1e4e8;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #28a745;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI BUSINESS E INTELLIGENZA (PERSONA + PROFITTO)
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
        if bsr <= 50000: return 50
        return 5

    @staticmethod
    def calculate_royalty(price, pages, is_color):
        if price <= 0: return 0.0
        cost = 2.15 if not is_color else 0.60 + (pages * 0.045)
        if pages > 108 and not is_color: cost = 0.60 + (pages * 0.012)
        royalty = (price * 0.60) - cost
        return round(royalty, 2) if royalty > 0 else 0.0

    @staticmethod
    def persona_alignment_score(titles, pain, desire):
        """Valuta quanto i libri esistenti parlano al dolore/sogno della Persona."""
        matches = 0
        keywords = (str(pain) + " " + str(desire)).lower().split()
        for t in titles:
            if any(kw in t.lower() for kw in keywords if len(kw) > 3):
                matches += 1
        return int((matches / len(titles)) * 100) if titles else 0

# ==============================================================================
# 3. CORE SCRAPER (CATEGORICO LIBRI & EBOOK)
# ==============================================================================
def scrape_exclusive_books(mkt, keyword, pages, is_color):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    country = 'it' if mkt == "Italia" else 'us'
    
    # FORZA CATEGORIA LIBRI (&i=stripbooks)
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
            
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
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
                "Royalty_Val": roy, "Recensioni": reviews, 
                "BSR": bsr if bsr > 0 else "N/D", "Vendite": sales,
                "Profitto": round(sales * roy, 2), "Self-Pub": "Sì" if is_self else "No"
            })
            p_bar.progress((i + 1) / len(items))
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 4. SIDEBAR: PERSONA LAB & STRATEGIA (DARK & FISSA)
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ PERSONA STRATEGY LAB")
    if st.button("🔄 NUOVA ANALISI", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("👤 Identikit Persona")
    with st.expander("Definisci il Lettore", expanded=True):
        p_target = st.text_input("Target", placeholder="es. Mamme in carriera")
        p_pain = st.text_input("Il Dolore (Problema)", placeholder="es. stress cronico")
        p_dream = st.text_input("Il Sogno (Desiderio)", placeholder="es. equilibrio casa-lavoro")
    
    st.markdown("---")
    st.subheader("🛠️ Ingegneria della Keyword")
    if p_pain and p_dream:
        k_gen = f"{p_pain.capitalize()} per {p_target}: Guida per {p_dream}"
        if st.button(f"🎯 Usa: {k_gen}"): 
            st.session_state['kw_active'] = k_gen; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Finale", value=st.session_state['kw_active'])
    
    if query:
        with st.expander("💡 Suggerimenti Autocomplete"):
            suggs = KDPFreeTools.get_amazon_suggestions(query, mkt)
            for s in suggs:
                if st.button(f"🔎 {s}", key=s): st.session_state['kw_active'] = s; st.rerun()

    st.markdown("---")
    pgs = st.number_input("Pagine", min_value=24, value=120)
    is_color = st.checkbox("Stampa a Colori")
    run = st.button("AVVIA ANALISI TARGETIZZATA", type="primary", use_container_width=True)

# ==============================================================================
# 5. MAIN DASHBOARD: VERDETTO PERSONA & PROFITTO
# ==============================================================================
if run and query:
    st.header(f"📊 Business Intelligence: {query.upper()}")
    
    # Card Persona
    st.markdown(f"""
    <div class="persona-card">
        <b>Buyer Persona:</b> {p_target} <br>
        <b>Problema:</b> {p_pain} | <b>Obiettivo:</b> {p_dream}
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Scansione categorica libri in corso..."):
        df = scrape_exclusive_books(mkt, query, pgs, is_color)
        
        if df is not None and not df.empty:
            # Mostra Tabella
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
            
            # Calcolo Metriche
            avg_p = df['Prezzo'].mean()
            avg_roy = df['Royalty_Val'].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            align_score = KDPBrain.persona_alignment_score(df['Titolo'].tolist(), p_pain, p_dream)
            
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_roy:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            c4.metric("Persona Alignment", f"{align_score}%")

            st.markdown("---")
            col_l, col_r = st.columns(2)
            
            with col_l:
                st.subheader("🏁 Verdetto sulla Persona")
                if align_score < 35:
                    st.success("✅ **BUCO DI MERCATO**: I libri esistenti non parlano direttamente del dolore della tua persona. Hai una grande opportunità di differenziazione.")
                else:
                    st.warning("⚠️ **MERCATO CONSAPEVOLE**: Molti titoli parlano già di questi temi. Devi trovare un angolo unico o un design superiore.")
                
                if avg_roy > 3.50:
                    st.success(f"✅ **MARGINE SANO**: La royalty media è di {avg_roy:.2f}€. Hai budget per le Ads.")
                else:
                    st.error(f"❌ **MARGINE BASSO**: Royalty di {avg_roy:.2f}€. Fare pubblicità sarà difficile.")

            with col_r:
                st.subheader("💡 Keyword Strategiche Alternative")
                ca1, ca2 = st.columns(2)
                ca1.markdown(f"<div class='keyword-alt-card'><b>Focus Problema:</b><br>{p_pain.title()} {p_target.lower()}</div>", unsafe_allow_html=True)
                ca2.markdown(f"<div class='keyword-alt-card'><b>Focus Metodo:</b><br>Workbook {query.lower()}</div>", unsafe_allow_html=True)
        else:
            st.error("Amazon ha limitato la scansione. Riprova tra 60 secondi.")
