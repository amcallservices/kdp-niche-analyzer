import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (DARK MODE & CATEGORICAL UI)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 3.2",
    page_icon="📚",
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

        /* FIX COLORI METRICHE (Nero su Bianco per leggibilità) */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* BOX RAGIONAMENTO AI */
        .gpt-logic-box { background-color: #1c2128; border-left: 5px solid #3182ce; padding: 15px; border-radius: 8px; color: #90cdf4; font-size: 0.88rem; margin-bottom: 20px; }
        .ai-audit-card { background-color: #fff9db; border-left: 6px solid #fab005; padding: 20px; border-radius: 10px; color: #856404; margin-bottom: 25px; }
        
        /* CARTE EDITORIALI PROFESSIONALI */
        .editorial-card { 
            background-color: #ffffff; border: 1px solid #e1e4e8; padding: 30px; 
            border-radius: 15px; margin-bottom: 25px; border-top: 8px solid #28a745; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
        }
        .title-option { color: #cf222e; font-size: 1.5rem; font-weight: 800; display: block; margin-bottom: 10px; border-bottom: 2px solid #f6f8fa; padding-bottom: 10px; }
        .marketing-angle { color: #0969da; font-weight: 700; font-size: 0.95rem; margin-bottom: 15px; display: block; background: #f0f9ff; padding: 5px 10px; border-radius: 5px; }
        .plot-detailed { color: #24292f; line-height: 1.7; font-size: 1.05rem; white-space: pre-wrap; }

        /* PIVOT CARD DARK (REINDIRIZZAMENTO) */
        .pivot-card {
            background-color: #1c2128; border: 1px solid #444c56; padding: 20px;
            border-radius: 12px; margin-bottom: 20px; border-left: 6px solid #673ab7;
            color: #f0f6fc !important;
        }
        .pivot-card b { color: #d1c4e9 !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ACCESSO AI SECRET & CLIENT SETUP
# ==============================================================================
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    WS_API_KEY = st.secrets["WS_API_KEY"]
    client = openai.OpenAI(api_key=OPENAI_KEY)
    API_READY = True
except Exception:
    st.error("⚠️ Configurazione Secret mancante o errata (OPENAI_API_KEY o WS_API_KEY).")
    API_READY = False

# ==============================================================================
# 3. CLASSE SURGICAL AI (RAGIONAMENTO OMNIBUS)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        prompt = f"""
        Sei un esperto Senior di KDP Marketing. Diagnosi Persona:
        - FORMATO: {p_type} | TARGET: {p_target} | DOLORE: {p_pain} | SOGNO: {p_dream}
        COMPITO:
        1. Crea una keyword Long Tail chirurgica ad alta conversione ESCLUSIVAMENTE per Amazon Libri.
        2. Spiega la leva psicologica d'acquisto in 2 righe.
        RISPOSTA: KEYWORD: [testo] | LOGICA: [testo]
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def executive_audit(df, query, p_target):
        titles = " | ".join(df['Titolo'].tolist()[:15])
        avg_price = df['Prezzo'].mean()
        prompt = f"""
        Analizza 20 competitor Amazon Libri per '{query}'. Prezzo Medio: {avg_price:.2f}€. 
        Titoli trovati: {titles}.
        Fornisci un Audit Chirurgico per il target '{p_target}': perché questi libri vendono o dove falliscono.
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Agisci come Editor-in-Chief. Crea 5 proposte editoriali (Libri o Ebook) sulla keyword '{kw}'.
        Target: {p_target}. Dolore: {p_pain}. Sogno: {p_dream}.
        
        Per ogni opzione fornisci:
        1. TITOLO: Accattivante con trigger emotivo.
        2. ANGOLO DI MARKETING: La promessa unica del libro.
        3. TRAMA DETTAGLIATA: Almeno 180 parole che descrivano la struttura del libro e i benefici per il lettore.
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_pivot(p_target, p_pain, p_dream, kw_fallita):
        prompt = f"La keyword editoriale '{kw_fallita}' per '{p_target}' è satura. Suggerisci 3 Keyword Pivot basate su dolore '{p_pain}' e sogno '{p_dream}' specifiche per Libri/Ebook."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. MOTORE DI SCRAPING (CATEGORIZZAZIONE BLINDATA LIBRI)
# ==============================================================================
def run_strategic_scan(mkt, keyword, pages):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=30)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
        
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:25]
        results = []
        for item in items:
            item_text = item.get_text().lower()
            # Filtro per garantire che sia un libro e non merchandising
            book_triggers = ['copertina', 'pagine', 'kindle', 'formato', 'paperback', 'hardcover', 'editor', 'editore', 'ebook', 'volumi', 'edizione']
            if not any(x in item_text for x in book_triggers):
                continue

            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            
            cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
            roy = round((price * 0.6) - cost, 2)
            
            results.append({
                "Preview": img, "Titolo": title, "Prezzo": price, "Royalty": roy, 
                "Self-Pub": "Sì" if "independently" in item_text or "pubblicato" in item_text or "kdp" in item_text else "No"
            })
            if len(results) >= 20: break 
            
        return pd.DataFrame(results)
    except Exception: return None

# ==============================================================================
# 5. SIDEBAR: COMANDI E RAGIONAMENTO AI
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""
if 'ai_logic' not in st.session_state: st.session_state['ai_logic'] = ""

with st.sidebar:
    st.title("🛡️ KDP OMNI-REASONER 3.2")
    st.caption("Filtro Categorico Rigido: Solo Libri ed Ebook ✅")
    
    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['kw_active'] = ""; st.session_state['ai_logic'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("👤 Analisi Predittiva Target")
    
    # LISTA FORMATI ESTESA
    p_type = st.selectbox("Formato Editoriale", [
        "Manuale Pratico", 
        "Workbook / Eserciziario", 
        "Diario di Trasformazione", 
        "Guida Passo-Passo",
        "Ricettario Strategico",
        "Activity Book (Libro di Attività)",
        "Libro di Quiz e Test",
        "Planner / Agenda Specializzata",
        "Prontuario / Compendio",
        "Saggio Divulgativo",
        "Libro da Colorare (Coloring Book)",
        "Flashcards Book"
    ])
    
    p_target = st.text_input("Target (A chi si rivolge?)", placeholder="es. Insegnanti stressati")
    p_pain = st.text_input("Problema (Cosa lo affligge?)", placeholder="es. gestione della classe")
    p_dream = st.text_input("Sogno (Cosa desidera?)", placeholder="es. autorità e calma")
    
    if st.button("🧠 GENERA STRATEGIA AI", use_container_width=True, type="primary") and API_READY:
        with st.spinner("L'AI sta dissezionando il bisogno..."):
            res = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
            if "KEYWORD:" in res:
                st.session_state['kw_active'] = res.split("KEYWORD:")[1].split("|")[0].strip()
                st.session_state['ai_logic'] = res.split("LOGICA:")[1].strip()
            else: st.write(res)

    if st.session_state['ai_logic']:
        st.markdown(f'<div class="gpt-logic-box"><b>AI STRATEGIC INSIGHT:</b><br>{st.session_state["ai_logic"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    mkt = st.selectbox("Marketplace Amazon", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Focus Keyword", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    run_btn = st.button("LANCIA DISSEZIONE CHIRURGICA", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: VERDETTO E REDAZIONE FINALE
# ==============================================================================
if run_btn and query and API_READY:
    st.header(f"📚 Report Strategico: {query.upper()}")
    
    with st.spinner("Scansione categorica di 20 competitor editoriali..."):
        df = run_strategic_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            # Audit Qualitativo GPT
            audit_res = SurgicalAI.executive_audit(df, query, p_target)
            st.markdown(f'<div class="ai-audit-card"><b>🤖 AI EXECUTIVE AUDIT (Analisi Qualitativa):</b><br>{audit_res}</div>', unsafe_allow_html=True)

            st.dataframe(df, column_config={"Preview": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            avg_p = df['Prezzo'].mean()
            self_ratio = (len(df[df["Self-Pub"] == "Sì"]) / len(df)) * 100
            o_score = 40
            if avg_p > 13.50: o_score += 30
            if self_ratio > 40: o_score += 30
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Indie Ratio", f"{int(self_ratio)}%")
            c3.metric("Opportunity Score", f"{o_score}/100")

            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Master Plan di Pubblicazione (5 Opzioni)")
                with st.spinner("L'AI sta redigendo i contenuti SEO..."):
                    master_plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, query)
                    formatted_plan = (master_plan
                        .replace("TITOLO:", " <span class='title-option'>")
                        .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
                        .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                        .replace("1.", "<br><b>1.</b>").replace("2.", "<br><b>2.</b>")
                        .replace("3.", "<br><b>3.</b>").replace("4.", "<br><b>4.</b>")
                        .replace("5.", "<br><b>5.</b>")
                    )
                    st.markdown(f'<div class="editorial-card">{formatted_plan}</div> </div>', unsafe_allow_html=True)
            else:
                st.markdown("---")
                st.header("🔄 Reindirizzamento Strategico (AI Pivot)")
                st.warning("⚠️ Score insufficiente. Lo Stratega AI ha elaborato queste vie d'uscita per il settore Libri:")
                pivot_res = SurgicalAI.genera_pivot(p_target, p_pain, p_dream, query)
                st.markdown(f'<div class="pivot-card"><b>Analisi di Reindirizzamento:</b><br>{pivot_res.replace("1.", "<br><b>1.</b>").replace("2.", "<br><b>2.</b>").replace("3.", "<br><b>3.</b>")}</div>', unsafe_allow_html=True)
        else:
            st.error("Nessun libro trovato per questa keyword nel dipartimento editoriale. Verifica la pertinenza della keyword.")
