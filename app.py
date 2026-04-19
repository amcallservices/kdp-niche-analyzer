import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE UI & SIDEBAR DARK
# ==============================================================================
st.set_page_config(
    page_title="KDP NICHE & PERSONA VALIDATOR - ELITE",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
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

        .stMetric {
            background-color: #ffffff !important; border: 1px solid #d0d7de !important;
            border-left: 8px solid #0969da !important; padding: 20px !important;
            border-radius: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
        }
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }

        .editorial-card {
            background-color: #ffffff; border: 1px solid #e1e4e8;
            padding: 25px; border-radius: 12px; margin-bottom: 20px;
            border-top: 5px solid #f78166; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .title-option { color: #cf222e; font-size: 1.3rem; font-weight: bold; margin-bottom: 10px; display: block; }
        .plot-text { color: #24292f; font-style: italic; line-height: 1.6; }
        
        .keyword-alt-card {
            background-color: #f3e5f5; border: 1px solid #d1c4e9;
            padding: 15px; border-radius: 8px; margin-bottom: 10px;
            border-left: 5px solid #673ab7; color: #4527a0 !important;
        }

        .persona-card {
            background-color: #f0f9ff; border: 1px solid #bae6fd;
            padding: 20px; border-radius: 10px; color: #0369a1;
            margin-bottom: 20px; border-left: 5px solid #0369a1;
        }
    </style>
""", unsafe_allow_html=True)

# --- CHIAVE API WEBSCRAPING.AI (Sostituisci con la tua) ---
WS_API_KEY = "INSERISCI_QUI_LA_TUA_CHIAVE"

# ==============================================================================
# 2. LOGICA DI BUSINESS
# ==============================================================================
class KDPFreeTools:
    @staticmethod
    def get_amazon_suggestions(keyword, mkt_code):
        mkt_map = {"Italia": "it", "USA": "com", "Spagna": "es", "Francia": "fr", "Germania": "de"}
        suffix = mkt_map.get(mkt_code, "it")
        url = f"https://completion.amazon.com/api/2017/suggestions?limit=10&prefix={urllib.parse.quote(keyword)}&alias=stripbooks"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200: return [s['value'] for s in r.json()['suggestions']]
        except: return []
        return []

class KDPBrain:
    @staticmethod
    def estimate_sales(bsr):
        if bsr <= 0: return 0
        if bsr <= 1500: return 650
        if bsr <= 10000: return 150
        return 5

    @staticmethod
    def calculate_royalty(price, pages, is_color):
        if price <= 0: return 0.0
        cost = 2.15 if not is_color else 0.60 + (pages * 0.045)
        if pages > 108 and not is_color: cost = 0.60 + (pages * 0.012)
        return round((price * 0.60) - cost, 2)

    @staticmethod
    def generate_editorial_proposal(type_book, target, pain, dream, keyword):
        titles = [
            f"{type_book.upper()}: Basta {pain.capitalize()} per {target}",
            f"{keyword.title()}: Il Metodo per {dream}",
            f"Oltre {pain.capitalize()}: {type_book} Strategico per {target}"
        ]
        plot = f"Questo {type_book} è stato progettato per aiutare ogni {target} a superare {pain} e raggiungere finalmente {dream}."
        return titles, plot

# ==============================================================================
# 3. MOTORE DI SCRAPING (WEBSCRAPING.AI)
# ==============================================================================
def scrape_books_ws(mkt, keyword, pages, is_color):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    try:
        response = requests.get(
            'https://api.webscraping.ai/html',
            params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}
        )
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
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
                book_url = f"https://www.{domain}" + link_tag['href']
                res_p = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': book_url, 'proxy': 'residential'})
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
# 4. SIDEBAR: PERSONA & TIPOLOGIA LIBRO (MIRATA)
# ==============================================================================
if 'kw_active' not in st.session_state:
    st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY COMMAND")
    
    if st.button("🔄 NUOVA ANALISI", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("👤 Identikit Persona & Libro")
    with st.expander("Parametri Mirati", expanded=True):
        p_type = st.text_input("Angolo Editoriale", placeholder="es. Manuale, Workbook, Raccolta")
        p_target = st.text_input("Target", placeholder="es. Donne in carriera")
        p_pain = st.text_input("Problema", placeholder="es. gestione tempo")
        p_dream = st.text_input("Risultato", placeholder="es. equilibrio vita-lavoro")
    
    # GENERAZIONE KEYWORD MIRATA
    if p_type and p_pain and p_target:
        k_sug = f"{p_type.capitalize()} di {p_pain} per {p_target}"
        if st.button(f"🎯 Genera: {k_sug}", use_container_width=True):
            st.session_state['kw_active'] = k_sug; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Focus", value=st.session_state['kw_active'])
    
    if query:
        with st.expander("💡 Suggerimenti Autocomplete"):
            suggs = KDPFreeTools.get_amazon_suggestions(query, mkt)
            for s in suggs:
                if st.button(f"🔎 {s}", key=f"s_{s}", use_container_width=True):
                    st.session_state['kw_active'] = s; st.rerun()

    st.markdown("---")
    pgs = st.number_input("Pagine", min_value=24, value=120)
    is_color = st.checkbox("Stampa a Colori")
    run = st.button("LANCIA ANALISI", type="primary", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD PRINCIPALE
# ==============================================================================
if run and query:
    st.header(f"📊 Analisi di Mercato: {query.upper()}")
    
    st.markdown(f"""
    <div class="persona-card">
        <b>Formato:</b> {p_type} | <b>Target:</b> {p_target} | <b>Pain Point:</b> {p_pain}
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Scansione in corso..."):
        df = scrape_books_ws(mkt, query, pgs, is_color)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            avg_roy = df['Royalty_Val'].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            
            o_score = 40
            if avg_p > 13: o_score += 20
            if self_ratio > 45: o_score += 20
            if avg_roy > 3.5: o_score += 20
            
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_roy:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            c4.metric("Opportunity Score", f"{o_score}/100")

            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Proposta Editoriale Sbloccata")
                titles, plot = KDPBrain.generate_editorial_proposal(p_type, p_target, p_pain, p_dream, query)
                col_t, col_p = st.columns([1, 1.5])
                with col_t:
                    st.subheader("📌 Titoli Hook")
                    for t in titles:
                        st.markdown(f"<div class='editorial-card'><span class='title-option'>{t}</span></div>", unsafe_allow_html=True)
                with col_p:
                    st.subheader("📖 Bozza Trama")
                    st.markdown(f"<div class='editorial-card'><p class='plot-text'>{plot}</p></div>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ Score basso. Prova una delle alternative qui sotto:")
                rescue_kws = [f"{p_type} per principianti {p_target}", f"{p_type} pratico {p_pain}", f"Guida a {p_pain} {p_type}"]
                rcols = st.columns(3)
                for i, rk in enumerate(rescue_kws):
                    if rcols[i].button(f"🔍 Prova: {rk}", key=f"res_{i}", use_container_width=True):
                        st.session_state['kw_active'] = rk; st.rerun()

            st.markdown("---")
            st.subheader("💡 Keyword Strategiche Alternative (Viola)")
            ca1, ca2 = st.columns(2)
            ca1.markdown(f"<div class='keyword-alt-card'><b>Focus Problema:</b><br>{p_type.title()} su {p_pain.lower()}</div>", unsafe_allow_html=True)
            ca2.markdown(f"<div class='keyword-alt-card'><b>Focus Risultato:</b><br>{p_type.title()} per {p_dream.lower()}</div>", unsafe_allow_html=True)
        else:
            st.error("Errore Amazon. Riprova tra 60 secondi.")
