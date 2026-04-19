import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. CONFIGURAZIONE UI ELITE DARK
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER AI SURGICAL",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] {
            min-width: 450px !important;
            max-width: 450px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        
        /* FIX METRICHE */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* BOX RAGIONAMENTO GPT */
        .gpt-logic-box {
            background-color: #1c2128; border: 1px solid #3182ce; padding: 15px;
            border-radius: 8px; color: #90cdf4; font-size: 0.88rem; margin-bottom: 20px;
            border-left: 5px solid #3182ce;
        }
        .ai-audit-card {
            background-color: #fff9db; border-left: 6px solid #fab005; padding: 20px;
            border-radius: 10px; color: #856404; margin-bottom: 25px;
        }
        .editorial-card { 
            background-color: #ffffff; border: 1px solid #e1e4e8; padding: 20px; 
            border-radius: 12px; margin-bottom: 15px; border-top: 4px solid #28a745; 
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CHIAVI API
# ==============================================================================
WS_API_KEY = "50867242-8e16-4f72-b142-caef181401f6"
OPENAI_API_KEY = "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"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ==============================================================================
# 3. MOTORE DI RAGIONAMENTO OMNICOMPRENSIVO (GPT-4o)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        """Generazione Keyword con Analisi Strategica preventiva."""
        prompt = f"""
        Analizza come un esperto di KDP Marketing:
        Formato: {p_type} | Target: {p_target} | Dolore: {p_pain} | Sogno: {p_dream}
        
        Compito:
        1. Crea una sola Keyword Long Tail chirurgica.
        2. Spiega la psicologia dell'acquisto in 2 righe.
        Formato: KEYWORD: [testo] | LOGICA: [testo]
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"ERRORE API: {str(e)}"

    @staticmethod
    def ai_data_audit(df, query, p_target):
        """Analizza i dati reali di Amazon e fornisce un verdetto aziendale."""
        avg_price = df['Prezzo'].mean()
        self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
        titles = " | ".join(df['Titolo'].tolist()[:10])
        
        prompt = f"""
        Sei il Direttore Strategico. Analizza questi dati reali di Amazon per la keyword '{query}':
        - Prezzo Medio: {avg_price:.2f}€
        - % Autori Indipendenti: {self_ratio}%
        - Titoli Competitor: {titles}
        
        Fornisci un Audit di 3 righe sulla fattibilità per un autore che punta al target '{p_target}'.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except:
            return "Audit non disponibile."

    @staticmethod
    def genera_piano_editoriale(p_type, p_target, p_pain, p_dream, kw):
        """Genera 5 Proposte editoriali (Titolo + Trama) ad alto impatto."""
        prompt = f"""
        Genera 5 opzioni di pubblicazione per '{kw}'.
        Target: {p_target}. Risolvi {p_pain} per ottenere {p_dream}.
        Per ogni opzione scrivi: TITOLO e una TRAMA di 2 righe molto persuasiva.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except:
            return "Piano editoriale non disponibile."

# ==============================================================================
# 4. CORE SCRAPER (20 COMPETITOR)
# ==============================================================================
def run_strategic_scan(mkt, keyword, pages):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        response = requests.get(
            'https://api.webscraping.ai/html',
            params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'},
            timeout=30
        )
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:20]
        results = []
        for item in items:
            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            roy = round((price * 0.6) - (2.15 if pages <= 108 else 0.60 + (pages * 0.012)), 2)
            results.append({"Preview": img, "Titolo": title, "Prezzo": price, "Royalty": roy, "Self-Pub": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"})
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 5. SIDEBAR: BRAIN AI
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""
if 'ai_logic' not in st.session_state: st.session_state['ai_logic'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY AI COMMAND")
    if st.button("🔄 RESET", use_container_width=True):
        st.session_state['kw_active'] = ""; st.session_state['ai_logic'] = ""; st.rerun()

    st.markdown("---")
    with st.expander("👤 Profilazione Buyer Persona", expanded=True):
        p_type = st.selectbox("Formato", ["Manuale", "Workbook", "Diario", "Guida"])
        p_target = st.text_input("Target", placeholder="es. Trader principianti")
        p_pain = st.text_input("Dolore", placeholder="es. perdere soldi per emotività")
        p_dream = st.text_input("Sogno", placeholder="es. entrate costanti ogni mese")
    
    if st.button("🧠 GENERA STRATEGIA GPT-4o", use_container_width=True, type="primary"):
        with st.spinner("L'AI sta ragionando..."):
            res = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
            if "KEYWORD:" in res:
                st.session_state['kw_active'] = res.split("KEYWORD:")[1].split("|")[0].strip()
                st.session_state['ai_logic'] = res.split("LOGICA:")[1].strip()
            else:
                st.error(res) # Mostra l'errore reale delle API

    if st.session_state['ai_logic']:
        st.markdown(f'<div class="gpt-logic-box"><b>AI STRATEGY:</b><br>{st.session_state["ai_logic"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Analisi", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine", min_value=24, value=120)
    run_btn = st.button("LANCIA DISSEZIONE", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD PRINCIPALE: AUDIT & REDAZIONE AI
# ==============================================================================
if run_btn and query:
    st.header(f"📊 Report Chirurgico: {query.upper()}")
    
    with st.spinner("Scansione competitor e Audit AI in corso..."):
        df = run_strategic_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            # --- AUDIT AI SUI DATI REALI ---
            audit_report = SurgicalAI.ai_data_audit(df, query, p_target)
            st.markdown(f'<div class="ai-audit-card"><b>🤖 AI EXECUTIVE AUDIT:</b><br>{audit_report}</div>', unsafe_allow_html=True)
            
            st.dataframe(df, column_config={"Preview": st.column_config.ImageColumn("Copertina")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            o_score = 40
            if avg_p > 13: o_score += 30
            if self_ratio > 40: o_score += 30
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Indie Ratio", f"{int(self_ratio)}%")
            c3.metric("Opportunity Score", f"{o_score}/100")

            # --- PIANO EDITORIALE GPT ---
            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Piano Editoriale Consigliato (GPT-4o)")
                piano = SurgicalAI.genera_piano_editorial(p_type, p_target, p_pain, p_dream, query)
                st.markdown(f'<div class="editorial-card">{piano}</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Score insufficiente. L'AI sconsiglia l'investimento su questa keyword specifica.")
        else:
            st.error("Errore Amazon. Riprova tra 60 secondi.")
