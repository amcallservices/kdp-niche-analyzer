import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER SECRET EDITION",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { min-width: 450px !important; background-color: #0d1117 !important; }
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }
        .gpt-logic-box { background-color: #1c2128; border-left: 5px solid #3182ce; padding: 15px; border-radius: 8px; color: #90cdf4; font-size: 0.88rem; margin-bottom: 20px; }
        .ai-audit-card { background-color: #fff9db; border-left: 6px solid #fab005; padding: 20px; border-radius: 10px; color: #856404; margin-bottom: 25px; }
        .editorial-card { background-color: #ffffff; border-top: 4px solid #28a745; padding: 20px; border-radius: 12px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .keyword-alt-card { background-color: #f3e5f5; border-left: 5px solid #673ab7; padding: 15px; border-radius: 8px; color: #4527a0 !important; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ACCESSO AI SECRET E INIZIALIZZAZIONE
# ==============================================================================
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    WS_API_KEY = st.secrets["WS_API_KEY"]
    client = openai.OpenAI(api_key=OPENAI_KEY)
    API_READY = True
except Exception as e:
    st.error("⚠️ Configurazione Secret mancante. Controlla il file secrets.toml o le impostazioni di Streamlit Cloud.")
    API_READY = False

# ==============================================================================
# 3. MOTORE DI RAGIONAMENTO GPT (LOGICA CHIRURGICA)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        prompt = f"""
        Sei un esperto Senior di Amazon KDP Marketing. Esegui una diagnosi:
        - FORMATO: {p_type} | TARGET: {p_target} | DOLORE: {p_pain} | SOGNO: {p_dream}
        COMPITO:
        1. Crea una sola keyword 'Bisturi' (Long Tail) ad altissima conversione.
        2. Spiega il White Space psicologico in 2 righe.
        FORMATO RISPOSTA: KEYWORD: [testo] | LOGICA: [testo]
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def executive_audit(df, query, p_target):
        titles = " | ".join(df['Titolo'].tolist()[:10])
        avg_price = df['Prezzo'].mean()
        prompt = f"""
        Analizza questi 20 risultati Amazon per '{query}':
        - Prezzo Medio: {avg_price:.2f}€ | Titoli Competitor: {titles}
        Fornisci un audit chirurgico di 3 righe per il target '{p_target}'.
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_piano_5(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"Genera 5 titoli e 5 trame persuasive per un libro '{p_type}' basato sulla keyword '{kw}'. Target: {p_target}. Risolvi {p_pain} per {p_dream}."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. CORE SCRAPER (20 RISULTATI)
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
            
            # Calcolo Royalty via LaTeX Style
            # $$ Royalty = (Price \times 0.60) - Cost $$
            cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
            roy = round((price * 0.6) - cost, 2)
            
            results.append({"Preview": img, "Titolo": title, "Prezzo": price, "Royalty": roy, "Self-Pub": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"})
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 5. SIDEBAR COMMAND CENTER
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""
if 'ai_logic' not in st.session_state: st.session_state['ai_logic'] = ""

with st.sidebar:
    st.title("🛡️ OMNI-STRATEGY AI")
    st.info("💡 Chiavi API caricate correttamente dai Secret.")
    
    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['kw_active'] = ""; st.session_state['ai_logic'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("📋 Diagnosi Buyer Persona")
    p_type = st.selectbox("Formato", ["Manuale Pratico", "Workbook", "Diario", "Guida"])
    p_target = st.text_input("Target", placeholder="es. Trader principianti")
    p_pain = st.text_input("Dolore", placeholder="es. ansia da perdita")
    p_dream = st.text_input("Sogno", placeholder="es. disciplina e profitti")
    
    if st.button("🧠 GENERA STRATEGIA GPT-4o", use_container_width=True, type="primary") and API_READY:
        with st.spinner("L'AI sta dissezionando la nicchia..."):
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
    pgs = st.number_input("Pagine", min_value=24, value=120)
    run_btn = st.button("LANCIA ANALISI CHIRURGICA", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD PRINCIPALE
# ==============================================================================
if run_btn and query and API_READY:
    st.header(f"📊 Report di Mercato: {query.upper()}")
    
    with st.spinner("Analisi di 20 competitor e Audit AI..."):
        df = run_strategic_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            # Audit AI Qualitativo
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
                st.header("✍️ Piano Editoriale GPT-4o (5 Opzioni)")
                piano = SurgicalAI.genera_piano_5(p_type, p_target, p_pain, p_dream, query)
                st.markdown(f'<div class="editorial-card">{piano}</div>', unsafe_allow_html=True)
            
            # Pivot Card (Viola)
            st.markdown("---")
            st.subheader("🔄 Pivot Formato Suggeriti")
            fcols = st.columns(4)
            for i, f in enumerate(["Workbook", "Diario", "Manuale", "Prontuario"]):
                fcols[i].markdown(f"<div class='keyword-alt-card'><b>{f} Edition</b><br>{f} {query.split('per')[0]}</div>", unsafe_allow_html=True)
        else:
            st.error("Errore di scansione. Amazon potrebbe aver limitato la richiesta.")
