import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (DARK SIDEBAR & METRIC FIX)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER MASTERPIECE 2.2",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] {
            min-width: 450px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p { color: #f0f6fc !important; }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important;
        }

        /* FIX METRICHE: Testo scuro su fondo bianco */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* BOX LOGICA AI */
        .gpt-logic-box { background-color: #1c2128; border-left: 5px solid #3182ce; padding: 15px; border-radius: 8px; color: #90cdf4; font-size: 0.88rem; margin-bottom: 20px; }
        .ai-audit-card { background-color: #fff9db; border-left: 6px solid #fab005; padding: 20px; border-radius: 10px; color: #856404; margin-bottom: 25px; }
        
        /* CARTE EDITORIALI */
        .editorial-card { 
            background-color: #ffffff; border: 1px solid #e1e4e8; padding: 25px; 
            border-radius: 12px; margin-bottom: 20px; border-top: 6px solid #28a745; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        }
        .title-option { color: #cf222e; font-size: 1.4rem; font-weight: bold; display: block; margin-bottom: 10px; }
        .marketing-logic { color: #0969da; font-weight: 600; font-size: 0.9rem; margin-bottom: 10px; display: block; }
        .plot-detailed { color: #24292f; line-height: 1.6; font-size: 1rem; }
        
        .keyword-alt-card { background-color: #f3e5f5; border-left: 5px solid #673ab7; padding: 15px; border-radius: 8px; color: #4527a0 !important; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ACCESSO AI SECRET & CONFIGURAZIONE AI
# ==============================================================================
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    WS_API_KEY = st.secrets["WS_API_KEY"]
    client = openai.OpenAI(api_key=OPENAI_KEY)
    API_READY = True
except Exception:
    st.error("⚠️ Configurazione Secret mancante (OPENAI_API_KEY o WS_API_KEY).")
    API_READY = False

class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        prompt = f"""
        Sei un esperto Senior di KDP Marketing. Diagnosi:
        - FORMATO: {p_type} | TARGET: {p_target} | DOLORE: {p_pain} | SOGNO: {p_dream}
        COMPITO:
        1. Crea una keyword 'Bisturi' (Long Tail) ad alta conversione per Amazon Libri.
        2. Spiega il White Space psicologico in 2 righe.
        RISPOSTA: KEYWORD: [testo] | LOGICA: [testo]
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def executive_audit(df, query, p_target):
        titles = " | ".join(df['Titolo'].tolist()[:10])
        avg_price = df['Prezzo'].mean()
        prompt = f"Analizza questi competitor editoriali per '{query}'. Prezzo Medio: {avg_price:.2f}€. Titoli: {titles}. Esegui un audit di 3 righe per il target '{p_target}' focalizzandoti su come battere i libri esistenti."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Sei un Editor di Bestseller Amazon KDP. Genera 5 proposte editoriali (Libri o Ebook) basate sulla keyword '{kw}'.
        Target: {p_target}. Problema: {p_pain}. Sogno: {p_dream}.
        
        Per ogni opzione fornisci:
        - TITOLO: Accattivante e SEO optimized.
        - LOGICA DI MARKETING: Perché questa specifica angolazione attirerà il target {p_target}.
        - TRAMA DETTAGLIATA: Descrizione ricca della struttura del libro, dei benefici e della trasformazione.
        
        Assicurati che le proposte siano adatte esclusivamente al formato libro/ebook.
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 3. MOTORE DI SCRAPING CATEGORICO (ONLY BOOKS & EBOOKS)
# ==============================================================================
def run_strategic_scan(mkt, keyword, pages):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    # IL PARAMETRO i=stripbooks BLOCCA LA RICERCA ALLA SOLA CATEGORIA LIBRI/EBOOK
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=30)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estrazione dei primi 20 risultati reali nel dipartimento libri
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:20]
        results = []
        for item in items:
            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
            roy = round((price * 0.6) - cost, 2)
            results.append({
                "Preview": img, 
                "Titolo": title, 
                "Prezzo": price, 
                "Royalty": roy, 
                "Self-Pub": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"
            })
        return pd.DataFrame(results)
    except Exception: return None

# ==============================================================================
# 4. SIDEBAR COMMAND CENTER
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""
if 'ai_logic' not in st.session_state: st.session_state['ai_logic'] = ""

with st.sidebar:
    st.title("🛡️ OMNI-STRATEGY AI")
    st.caption("Filtro Categorico: Libri ed Ebook Attivo ✅")
    
    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['kw_active'] = ""; st.session_state['ai_logic'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("📋 Diagnosi Buyer Persona")
    p_type = st.selectbox("Formato", ["Manuale Pratico", "Workbook", "Diario", "Guida Passo-Passo"])
    p_target = st.text_input("Target", placeholder="es. Trader")
    p_pain = st.text_input("Dolore", placeholder="es. ansia da perdita")
    p_dream = st.text_input("Sogno", placeholder="es. disciplina e profitto")
    
    if st.button("🧠 GENERA STRATEGIA AI", use_container_width=True, type="primary") and API_READY:
        with st.spinner("Diagnosi editoriale in corso..."):
            res = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
            if "KEYWORD:" in res:
                st.session_state['kw_active'] = res.split("KEYWORD:")[1].split("|")[0].strip()
                st.session_state['ai_logic'] = res.split("LOGICA:")[1].strip()
            else: st.write(res)

    if st.session_state['ai_logic']:
        st.markdown(f'<div class="gpt-logic-box"><b>AI LOGIC:</b><br>{st.session_state["ai_logic"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    mkt = st.selectbox("Marketplace Amazon", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Focus Keyword", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine Libro", min_value=24, value=120)
    run_btn = st.button("LANCIA ANALISI CATEGORICA", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: REPORT & MASTER PLAN
# ==============================================================================
if run_btn and query and API_READY:
    st.header(f"📚 Report Strategico: {query.upper()}")
    st.info("⚠️ Analisi ristretta esclusivamente al dipartimento Libri/Ebook.")
    
    with st.spinner("Analisi di 20 competitor editoriali..."):
        df = run_strategic_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            audit_res = SurgicalAI.executive_audit(df, query, p_target)
            st.markdown(f'<div class="ai-audit-card"><b>🤖 AI EXECUTIVE AUDIT:</b><br>{audit_res}</div>', unsafe_allow_html=True)

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

            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Master Plan Editoriale (5 Opzioni)")
                with st.spinner("Generazione trame dettagliate..."):
                    master_plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, query)
                    # Formattazione per visualizzazione carte pulite
                    formatted_plan = (master_plan
                        .replace("TITOLO:", " <span class='title-option'>")
                        .replace("LOGICA DI MARKETING:", "</span> <span class='marketing-logic'>")
                        .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                        .replace("- ", "<br>• ")
                    )
                    st.markdown(f'<div class="editorial-card">{formatted_plan}</div> </div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Score insufficiente (< 60). Prova ad affinare la keyword o il target.")
            
            # Pivot Format Suggeriti
            st.markdown("---")
            st.subheader("🔄 Pivot Formato Suggeriti")
            fcols = st.columns(4)
            for i, f in enumerate(["Workbook", "Diario", "Manuale", "Prontuario"]):
                fcols[i].markdown(f"<div class='keyword-alt-card'><b>{f} Edition</b><br>{f} {query.split('per')[0]}</div>", unsafe_allow_html=True)
        else:
            st.error("Errore di scansione. Verifica la connessione o i crediti API.")
