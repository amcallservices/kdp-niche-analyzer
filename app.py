import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE UI & SIDEBAR PROFESSIONALE
# ==============================================================================
st.set_page_config(
    page_title="KDP STRATEGIC ANALYZER PRO",
    page_icon="💎",
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
        
        /* Box di Ragionamento Strategico */
        .reasoning-box {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 15px;
            border-radius: 8px;
            color: #c9d1d9;
            font-size: 0.85rem;
            margin-bottom: 15px;
            border-left: 4px solid #f78166;
        }

        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; border-radius: 12px !important; }
        .keyword-alt-card { background-color: #f3e5f5; border-left: 5px solid #673ab7; padding: 15px; border-radius: 8px; color: #4527a0 !important; }
        .editorial-card { background-color: #ffffff; border-top: 5px solid #f78166; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .persona-card { background-color: #f0f9ff; border-left: 5px solid #0369a1; padding: 20px; border-radius: 10px; color: #0369a1; }
    </style>
""", unsafe_allow_html=True)

# --- CHIAVE API WEBSCRAPING.AI ---
WS_API_KEY = "LA_TUA_CHIAVE_API"

# ==============================================================================
# 2. MOTORE DI RAGIONAMENTO STRATEGICO (LOGICA "CHIRURGICA")
# ==============================================================================
class StrategicLogic:
    @staticmethod
    def generate_ai_keyword(format_type, target, pain, dream):
        """Dissezione psicologica per la creazione della keyword ad alta conversione."""
        # Logica: Angolo Editoriale + Conflitto + Target + Soluzione
        # Una keyword professionale deve essere specifica (Long Tail)
        return f"{format_type} per {pain} in {target}: Guida pratica per {dream}"

    @staticmethod
    def get_market_rationale(target, pain, dream):
        """Simula il ragionamento di un'IA di marketing."""
        return f"""
        <b>Analisi Strategica:</b> Il target <i>'{target}'</i> vive uno stato di tensione dovuto a <i>'{pain}'</i>. 
        Inserendo la promessa di <i>'{dream}'</i> nella keyword, attiviamo il trigger psicologico della 'trasformazione'. 
        Il formato scelto serve da ponte logico per la vendita.
        """

    @staticmethod
    def get_amazon_suggestions(keyword, mkt_code):
        mkt_map = {"Italia": "it", "USA": "com", "Spagna": "es", "Francia": "fr", "Germania": "de"}
        suffix = mkt_map.get(mkt_code, "it")
        url = f"https://completion.amazon.com/api/2017/suggestions?limit=10&prefix={urllib.parse.quote(keyword)}&alias=stripbooks"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            return [s['value'] for s in r.json()['suggestions']] if r.status_code == 200 else []
        except: return []

# ==============================================================================
# 3. CORE SCRAPER (CATEGORICO LIBRI)
# ==============================================================================
def scrape_books_elite(mkt, keyword, pages, is_color):
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
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_frac.text}") if p_w and p_frac else 0.0
            results.append({
                "Copertina": img, "Titolo": title, "Prezzo": price, 
                "Royalty_Est": round((price * 0.6) - 2.15, 2), "Self-Pub": "Sì" if "independently" in title.lower() else "No"
            })
            p_bar.progress((i + 1) / len(items))
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 4. SIDEBAR: IDENTIKIT & LOGICA AI
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY CONTROL")
    
    if st.button("🔄 RESET ANALISI", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("📊 Analisi del Target")
    with st.expander("Configurazione Modello", expanded=True):
        p_type = st.selectbox("Formato Libro", ["Manuale Pratico", "Workbook", "Ricettario", "Diario", "Guida Passo-Passo"])
        p_target = st.text_input("Lettore Ideale", placeholder="es. Manager sopraffatti")
        p_pain = st.text_input("Problema Specifico", placeholder="es. gestione delle email")
        p_dream = st.text_input("Risultato Desiderato", placeholder="es. svuotare la casella in 10 min")
    
    # LOGICA "CHIRURGICA" PER GENERAZIONE KEYWORD
    if p_target and p_pain and p_dream:
        reasoning = StrategicLogic.get_market_rationale(p_target, p_pain, p_dream)
        st.markdown(f"""<div class="reasoning-box">{reasoning}</div>""", unsafe_allow_html=True)
        
        final_kw = StrategicLogic.generate_ai_keyword(p_type, p_target, p_pain, p_dream)
        if st.button(f"🎯 APPLICA KEYWORD: {final_kw}", use_container_width=True):
            st.session_state['kw_active'] = final_kw; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Focus Keyword", value=st.session_state['kw_active'])
    
    if query:
        with st.expander("💡 Espansione Keyword"):
            suggs = StrategicLogic.get_amazon_suggestions(query, mkt)
            for s in suggs:
                if st.button(f"🔎 {s}", key=f"s_{s}", use_container_width=True):
                    st.session_state['kw_active'] = s; st.rerun()

    st.markdown("---")
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    run = st.button("LANCIA ANALISI MERCATO", type="primary", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: VERDETTO FINALE
# ==============================================================================
if run and query:
    st.header(f"📊 Dashboard Strategica: {query.upper()}")
    
    st.markdown(f"""
    <div class="persona-card">
        <b>POSIZIONAMENTO:</b> Questo <b>{p_type}</b> risolve il problema <b>{p_pain}</b> per il target <b>{p_target}</b>.
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Scansione in corso..."):
        df = scrape_books_elite(mkt, query, pgs, False)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Validazione", "OTTIMA" if avg_p > 13 else "BASSA")

            if avg_p > 13:
                st.success("✅ **OPPORTUNITÀ VALIDATA:** Il mercato è disposto a investire per risolvere questo problema.")
                st.header("✍️ Proposta Editoriale")
                st.markdown(f"""
                <div class="editorial-card">
                    <b>TITOLO SUGGERITO:</b> {query.title()}<br><br>
                    <i>Angolo di Marketing:</i> Sostituisci il dolore con la competenza attraverso un metodo strutturato.
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Errore Amazon. Riprova tra 60 secondi.")
