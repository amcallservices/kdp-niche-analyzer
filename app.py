import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai # Assicurati di installare questa libreria

# ==============================================================================
# 1. CONFIGURAZIONE UI & DESIGN SYSTEM (ELITE DARK)
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
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #f0f6fc !important;
        }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important;
        }

        /* FIX METRICHE */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* BOX RAGIONAMENTO GPT */
        .gpt-logic-box {
            background-color: #1c2128;
            border: 1px solid #3182ce;
            padding: 15px;
            border-radius: 8px;
            color: #90cdf4;
            font-size: 0.88rem;
            margin-bottom: 20px;
            border-left: 5px solid #3182ce;
        }
        .keyword-alt-card { background-color: #f3e5f5; border-left: 5px solid #673ab7; padding: 15px; border-radius: 8px; color: #4527a0 !important; margin-bottom: 10px; }
        .editorial-card { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-top: 4px solid #28a745; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE CHIAVI API
# ==============================================================================
WS_API_KEY = "50867242-8e16-4f72-b142-caef181401f6"
OPENAI_API_KEY = "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"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ==============================================================================
# 3. MOTORE DI INTELLIGENZA GPT (LOGICA CHIRURGICA)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        """Usa GPT per generare una keyword basata sulla psicologia del profittevole."""
        prompt = f"""
        Sei un esperto Senior di Amazon KDP Marketing e uno Psicologo dei Consumi.
        Analizza questo caso clinico editoriale:
        - TIPO LIBRO: {p_type}
        - TARGET: {p_target}
        - PROBLEMA (PAIN): {p_pain}
        - DESIDERIO (DREAM): {p_dream}

        REGOLE:
        1. Genera una sola keyword 'Bisturi' (Long Tail) ad altissima conversione.
        2. Spiega in due righe il ragionamento psicologico dietro la scelta (White Space).
        3. Formato output: KEYWORD | RAGIONAMENTO
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o", # O "gpt-3.5-turbo"
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Errore AI: {str(e)} | Inserimento manuale consigliato."

    @staticmethod
    def genera_contenuti_editoriali(p_type, p_target, p_pain, p_dream, kw):
        """Genera 5 Proposte editoriali complete via GPT."""
        prompt = f"Genera 5 titoli e 5 trame brevi per un libro '{p_type}' basato sulla keyword '{kw}'. Il target è {p_target}. Focus sul risolvere {p_pain} per ottenere {p_dream}."
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except:
            return "Impossibile generare contenuti editoriali."

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
            roy = round((price * 0.6) - (2.15 if pages <= 108 else 0.60 + (pages * 0.012)), 2)
            results.append({"Preview": img, "Titolo": title, "Prezzo": price, "Royalty_Est": roy, "Self-Pub": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"})
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 5. SIDEBAR COMMAND CENTER
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""
if 'ai_reasoning' not in st.session_state: st.session_state['ai_reasoning'] = ""

with st.sidebar:
    st.title("🩺 KDP SURGICAL AI")
    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['kw_active'] = ""
        st.session_state['ai_reasoning'] = ""
        st.rerun()

    st.markdown("---")
    st.subheader("📋 Diagnosi del Lettore")
    with st.expander("Parametri della Persona", expanded=True):
        p_type = st.selectbox("Formato Libro", ["Manuale Pratico", "Workbook di Esercizi", "Diario di Trasformazione", "Guida Passo-Passo"])
        p_target = st.text_input("Identikit Target", placeholder="es. Mamme in carriera sopraffatte")
        p_pain = st.text_input("Patologia (Dolore)", placeholder="es. mancanza di tempo per se stesse")
        p_dream = st.text_input("Prognosi (Sogno)", placeholder="es. 1 ora di relax al giorno")
    
    # PULSANTE BRAINSTORMING GPT
    if st.button("🧠 GENERA KEYWORD CON GPT-4", use_container_width=True, type="primary"):
        with st.spinner("Analisi psicografica in corso..."):
            ai_output = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
            if "|" in ai_output:
                kw, logic = ai_output.split("|")
                st.session_state['kw_active'] = kw.strip()
                st.session_state['ai_reasoning'] = logic.strip()
            else:
                st.session_state['kw_active'] = ai_output

    if st.session_state['ai_reasoning']:
        st.markdown(f'<div class="gpt-logic-box"><b>AI LOGIC:</b> {st.session_state["ai_reasoning"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Focus", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine", min_value=24, value=120)
    run_btn = st.button("LANCIA DISSEZIONE MERCATO", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD PRINCIPALE
# ==============================================================================
if run_btn and query:
    st.header(f"📊 Analisi Chirurgica: {query.upper()}")
    
    with st.spinner("Scansione di 20 competitor..."):
        df = run_strategic_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            st.dataframe(df, column_config={"Preview": st.column_config.ImageColumn("Copertina")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            avg_roy = df['Royalty_Est'].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            o_score = 40
            if avg_p > 13: o_score += 30
            if self_ratio > 40: o_score += 30
            
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_roy:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            c4.metric("Opportunity Score", f"{o_score}/100")

            # SEZIONE EDITORIALE (5 PROPOSTE)
            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Piano Editoriale GPT-4")
                with st.spinner("Generazione 5 proposte..."):
                    piano = SurgicalAI.genera_contenuti_editoriali(p_type, p_target, p_pain, p_dream, query)
                    st.markdown(f'<div class="editorial-card">{piano}</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Score insufficiente. Prova a variare la keyword con il laboratorio AI.")
        else:
            st.error("Errore Amazon. Riprova tra 60 secondi.")
