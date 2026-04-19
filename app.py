import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE UI & SIDEBAR "CLINICA"
# ==============================================================================
st.set_page_config(
    page_title="KDP SURGICAL NICHE VALIDATOR v2.0",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] {
            min-width: 440px !important;
            max-width: 440px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        
        /* Diagnosi Box nella Sidebar */
        .diagnosis-box {
            background-color: #161b22;
            border: 1px solid #3182ce;
            padding: 15px;
            border-radius: 8px;
            color: #90cdf4;
            font-size: 0.9rem;
            margin-bottom: 15px;
        }

        /* Stile Metriche e Card */
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #3182ce !important; border-radius: 12px !important; }
        .keyword-alt-card { background-color: #f3e5f5; border-left: 5px solid #673ab7; padding: 15px; border-radius: 8px; color: #4527a0 !important; }
        .editorial-card { background-color: #ffffff; border-top: 5px solid #f78166; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .persona-card { background-color: #f0f9ff; border-left: 5px solid #0369a1; padding: 20px; border-radius: 10px; color: #0369a1; }
    </style>
""", unsafe_allow_html=True)

# --- CHIAVE API WEBSCRAPING.AI ---
WS_API_KEY = "LA_TUA_CHIAVE_API"

# ==============================================================================
# 2. MOTORE DI RAGIONAMENTO CLINICO
# ==============================================================================
class KDPDiagnostic:
    @staticmethod
    def generate_surgical_keyword(type_book, target, pain, dream):
        """Ragionamento professionale per la creazione della cura editoriale."""
        # Logica: Strumento + Patologia + Paziente + Prognosi
        kw = f"{type_book} per {pain} in {target}: Protocollo per {dream}"
        return kw

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
# 3. CORE SCRAPER (WEBSCRAPING.AI)
# ==============================================================================
def scrape_books_surgical(mkt, keyword, pages, is_color):
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
            roy = round((price * 0.60) - (2.15 if pages <= 108 else 0.60 + (pages * 0.012)), 2)
            results.append({
                "Copertina": img, "Titolo": title, "Prezzo": price, 
                "Royalty_Est": roy, "Self-Pub": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "N/D"
            })
            p_bar.progress((i + 1) / len(items))
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 4. SIDEBAR: PROTOCOLLO DIAGNOSTICO
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🩺 KDP SURGICAL LAB")
    st.markdown("""<div class="diagnosis-box"><b>OBIETTIVO:</b> Eseguire una dissezione del mercato per identificare nervi scoperti e nicchie non curate dai grandi editori.</div>""", unsafe_allow_html=True)

    if st.button("🔄 RESET PROTOCOLLO", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("📋 Anamnesi del Mercato")
    with st.expander("Parametri Diagnostici", expanded=True):
        p_type = st.selectbox("Strumento (Tipo)", ["Manuale Pratico", "Workbook di Esercizi", "Ricettario Strategico", "Diario di Trasformazione", "Guida Passo-Passo"])
        p_target = st.text_input("Anatomia (Target)", placeholder="es. Imprenditori in Burnout")
        p_pain = st.text_input("Patologia (Dolore)", placeholder="es. Insonnia Cronica")
        p_dream = st.text_input("Prognosi (Sogno)", placeholder="es. Sonno Profondo in 7 giorni")
    
    # RAGIONAMENTO CHIRURGICO PER GENERAZIONE KEYWORD
    if p_target and p_pain and p_dream:
        surgical_kw = KDPDiagnostic.generate_surgical_keyword(p_type, p_target, p_pain, p_dream)
        st.info(f"👨‍⚕️ **Diagnosi:** Il paziente cerca un '{p_type}' perché la 'patologia' ({p_pain}) è insopportabile.")
        if st.button(f"💉 INIETTA KEYWORD: {surgical_kw}", use_container_width=True):
            st.session_state['kw_active'] = surgical_kw; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Mercato Operativo", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Bisturi (Keyword Focus)", value=st.session_state['kw_active'])
    
    if query:
        with st.expander("💡 Espansione Diagnostica (Autocomplete)"):
            suggs = KDPDiagnostic.get_amazon_suggestions(query, mkt)
            for s in suggs:
                if st.button(f"🔎 {s}", key=f"s_{s}", use_container_width=True):
                    st.session_state['kw_active'] = s; st.rerun()

    st.markdown("---")
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    run = st.button("LANCIA DISSEZIONE NICCHIA", type="primary", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: VERDETTO CLINICO
# ==============================================================================
if run and query:
    st.header(f"🩺 Risultati dell'Operazione: {query.upper()}")
    
    st.markdown(f"""
    <div class="persona-card">
        <b>PIANO DI CURA:</b> Utilizzare un <b>{p_type}</b> per eradicare <b>{p_pain}</b> nel target <b>{p_target}</b>.
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Esecuzione scansione profonda..."):
        df = scrape_books_surgical(mkt, query, pgs, False)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            avg_roy = df['Royalty_Est'].mean()
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo di Mercato", f"{avg_p:.2f} €")
            c2.metric("Utile a Intervento (Royalty)", f"{avg_roy:.2f} €")
            c3.metric("Opportunity Score", "75/100" if avg_p > 13 else "40/100")

            # VERDETTO CHIRURGICO
            st.markdown("---")
            if avg_p > 13:
                st.success("✅ **OPERAZIONE CONSIGLIATA:** La nicchia presenta margini sani. Il 'paziente' è disposto a pagare per la soluzione.")
                st.header("✍️ Prescrizione Editoriale")
                st.markdown(f"""
                <div class="editorial-card">
                    <span style="color:#cf222e; font-weight:bold; font-size:1.2rem;">TITOLO SUGGERITO:</span><br>
                    <b>Protocollo {p_pain.title()}:</b> Il Metodo {p_type} per {p_target} che vogliono {p_dream}.<br><br>
                    <span style="color:#24292f; font-style:italic;">Bozza Trama:</span><br>
                    "Se sei un {p_target} e la tua vita è limitata da {p_pain}, questo {p_type} è il farmaco letterario di cui hai bisogno..."
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("⚠️ **OPERAZIONE RISCHIOSA:** Margini troppo bassi. Il rischio di 'emorragia finanziaria' con le Ads è elevato.")
        else:
            st.error("Errore Amazon. Riprova tra 60 secondi.")
