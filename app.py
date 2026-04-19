import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE UI PROFESSIONALE (SIDEBAR DARK E FISSA)
# ==============================================================================
st.set_page_config(
    page_title="KDP STRATEGIC ANALYZER ELITE",
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
        
        /* Box di Logica Strategica */
        .reasoning-box {
            background-color: #161b22;
            border: 1px solid #3182ce;
            padding: 15px;
            border-radius: 8px;
            color: #90cdf4;
            font-size: 0.85rem;
            margin-bottom: 15px;
            border-left: 4px solid #3182ce;
        }

        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; border-radius: 12px !important; }
        
        /* KEYWORD ALTERNATIVE IN VIOLA */
        .keyword-alt-card { 
            background-color: #f3e5f5; 
            border: 1px solid #d1c4e9;
            border-left: 5px solid #673ab7; 
            padding: 15px; 
            border-radius: 8px; 
            color: #4527a0 !important; 
            margin-bottom: 10px;
        }

        .editorial-card { background-color: #ffffff; border-top: 5px solid #f78166; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .persona-card { background-color: #f0f9ff; border-left: 5px solid #0369a1; padding: 20px; border-radius: 10px; color: #0369a1; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORE DI LOGICA STRATEGICA (AI RATIONALE)
# ==============================================================================
# INSERISCI QUI LA TUA CHIAVE WEBSCRAPING.AI
WS_API_KEY = "INSERISCI_LA_TUA_CHIAVE_QUI"

class StrategicAI:
    @staticmethod
    def generate_surgical_keyword(format_type, target, pain, dream):
        """Genera una keyword Long-Tail basata sulla dissezione del bisogno."""
        return f"{format_type} di {pain} per {target}: Protocollo per {dream}"

    @staticmethod
    def get_strategy_rationale(target, pain, dream):
        """Spiegazione del posizionamento psicografico."""
        return f"""
        <b>Logica Strategica:</b> Il target <i>'{target}'</i> è attualmente bloccato dall'ostacolo <i>'{pain}'</i>. 
        La keyword proposta agisce come ponte logico verso <i>'{dream}'</i>, posizionando il libro non come un acquisto, ma come una soluzione necessaria.
        """

    @staticmethod
    def calculate_royalty(price, pages):
        if price <= 0: return 0.0
        # Stima costi stampa 2026
        cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
        return round((price * 0.60) - cost, 2)

# ==============================================================================
# 3. MOTORE DI SCRAPING RESILIENTE (WEBSCRAPING.AI)
# ==============================================================================
def scrape_books_elite(mkt, keyword, pages):
    if not WS_API_KEY or "INSERISCI" in WS_API_KEY:
        st.error("🔑 Manca la API Key di WebScraping.ai nella sezione del codice.")
        return None

    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        response = requests.get(
            'https://api.webscraping.ai/html',
            params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential', 'timeout': 20000},
            timeout=30
        )
        
        if response.status_code != 200:
            st.error(f"❌ Amazon/API Error (Status {response.status_code}). Riprova tra 60s.")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
        if not items:
            st.warning("🧐 Nessun libro trovato. Prova una keyword meno specifica.")
            return None

        results = []
        p_bar = st.progress(0)
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            
            # Parsing Prezzo con correzione refuso
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            
            # Calcolo BSR simulato per velocità (ottimizzazione crediti)
            bsr_rand = 0 # In un'app reale qui faresti il deep scan del link prodotto
            
            roy = StrategicAI.calculate_royalty(price, pages)
            results.append({
                "Copertina": img,
                "Titolo": title,
                "Prezzo": price,
                "Royalty Est.": f"{roy} €",
                "KDP": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"
            })
            p_bar.progress((i + 1) / len(items))
        
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"⚠️ Errore di connessione: {str(e)}")
        return None

# ==============================================================================
# 4. SIDEBAR: DISSEZIONE PSICOGRAFICA & ISTRUZIONI
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY COMMAND")
    
    with st.expander("📖 Istruzioni d'Uso", expanded=False):
        st.markdown("""
        1. **Identikit:** Definisci il formato e il target.
        2. **Logica AI:** Leggi il ragionamento strategico generato.
        3. **Iniezione:** Clicca 'Applica' per caricare la keyword chirurgica.
        4. **Analisi:** Se lo score è > 60, il sistema redige titoli e trama.
        """)

    if st.button("🔄 NUOVA ANALISI", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("👤 Analisi del Target & Libro")
    with st.expander("Configurazione Modello", expanded=True):
        p_type = st.selectbox("Formato Libro", ["Manuale Pratico", "Workbook", "Diario Strategico", "Guida Passo-Passo"])
        p_target = st.text_input("Lettore Ideale", placeholder="es. Manager in burnout")
        p_pain = st.text_input("Dolore (Problema)", placeholder="es. gestione email")
        p_dream = st.text_input("Sogno (Risultato)", placeholder="es. libertà digitale")
    
    if p_target and p_pain and p_dream:
        rationale = StrategicAI.get_strategy_rationale(p_target, p_pain, p_dream)
        st.markdown(f"""<div class="reasoning-box">{rationale}</div>""", unsafe_allow_html=True)
        
        surgical_kw = StrategicAI.generate_surgical_keyword(p_type, p_target, p_pain, p_dream)
        if st.button(f"🎯 APPLICA KEYWORD: {surgical_kw}", use_container_width=True):
            st.session_state['kw_active'] = surgical_kw; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Focus Keyword", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    
    run = st.button("LANCIA ANALISI DI MERCATO", type="primary", use_container_width=True)

# ==============================================================================
# 5. MAIN DASHBOARD: VERDETTO & REDAZIONE
# ==============================================================================
if run and query:
    st.header(f"📊 Dashboard Strategica: {query.upper()}")
    
    st.markdown(f"""
    <div class="persona-card">
        <b>POSIZIONAMENTO:</b> Utilizzo di un <b>{p_type}</b> per risolvere <b>{p_pain}</b> nel target <b>{p_target}</b>.
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Esecuzione scansione categorica Libri..."):
        df = scrape_books_elite(mkt, query, pgs)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            # Opportunity Score Semplificato
            o_score = 40
            if avg_p > 13: o_score += 30
            if len(df[df["KDP"] == "Sì"]) > 5: o_score += 30
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Opportunity Score", f"{o_score}/100")
            c3.metric("Status", "VALIDA" if o_score >= 60 else "NON VALIDA")

            # SEZIONE KEYWORD ALTERNATIVE (VIOLA)
            st.markdown("---")
            st.subheader("💡 Keyword Strategiche Alternative")
            ca1, ca2 = st.columns(2)
            ca1.markdown(f"<div class='keyword-alt-card'><b>Pivot Problema:</b><br>Come risolvere {p_pain} per {p_target}</div>", unsafe_allow_html=True)
            ca2.markdown(f"<div class='keyword-alt-card'><b>Pivot Formato:</b><br>Eserciziario pratico {p_target}</div>", unsafe_allow_html=True)

            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Proposta Editoriale Sbloccata")
                col_t, col_p = st.columns([1, 1.5])
                with col_t:
                    st.subheader("📌 Titoli Hook")
                    st.markdown(f"<div class='editorial-card'><b>Titolo:</b> {query.title()}<br><small>Sottotitolo: Il metodo per {p_dream}</small></div>", unsafe_allow_html=True)
                with col_p:
                    st.subheader("📖 Bozza Trama")
                    st.markdown(f"<div class='editorial-card'><p>Sei stanco di combattere con {p_pain}? Come {p_target}, meriti di ottenere finalmente {p_dream}. Questo {p_type} ti guiderà passo dopo passo...</p></div>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ La keyword non ha superato i test di profitto. Utilizza i Pivot suggeriti sopra per una nuova analisi.")
