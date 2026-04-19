import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (ULTRA DARK & HIGH CONTRAST)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 4.0",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] {
            min-width: 480px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }

        /* FIX METRICHE */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* BOX LOGICA AI SIDEBAR */
        .ai-sidebar-res {
            background-color: #1c2128; border: 1px solid #3182ce; padding: 15px;
            border-radius: 8px; color: #90cdf4; font-size: 0.9rem; margin-bottom: 15px;
        }

        /* PIANO EDITORIALE - HIGH CONTRAST DARK */
        .editorial-container {
            background-color: #0d1117; 
            border: 2px solid #30363d; 
            padding: 35px; 
            border-radius: 15px; 
            margin-bottom: 25px; 
            border-top: 10px solid #238636;
        }
        .title-option { color: #ffd700 !important; font-size: 1.7rem; font-weight: 900; display: block; margin-bottom: 12px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .marketing-angle { color: #58a6ff !important; font-weight: 700; font-size: 1.1rem; margin-bottom: 15px; display: block; font-family: 'Courier New', Courier, monospace; }
        .plot-detailed { color: #e6edf3 !important; line-height: 1.9; font-size: 1.1rem; white-space: pre-wrap; margin-bottom: 30px; }

        /* PIVOT CARD (REINDIRIZZAMENTO) */
        .pivot-card {
            background-color: #161b22; border: 1px solid #444c56; padding: 25px;
            border-radius: 12px; margin-bottom: 20px; border-left: 8px solid #673ab7;
            color: #f0f6fc !important;
        }
        .pivot-item { color: #d1c4e9 !important; font-weight: bold; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CLIENT SETUP & SECRETS
# ==============================================================================
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    WS_API_KEY = st.secrets["WS_API_KEY"]
    client = openai.OpenAI(api_key=OPENAI_KEY)
    API_READY = True
except Exception:
    st.error("⚠️ Configurazione Secret (OPENAI_API_KEY / WS_API_KEY) non trovata.")
    API_READY = False

# ==============================================================================
# 3. SURGICAL AI REASONING ENGINE
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_3_keywords(p_type, p_target, p_pain, p_dream):
        """Genera 3 opzioni di keyword chirurgiche basate sull'idea dell'utente."""
        prompt = f"""
        Sei un Direttore Marketing KDP. L'utente vuole scrivere un '{p_type}' per '{p_target}'.
        Il problema principale è '{p_pain}' e il sogno è '{p_dream}'.
        
        GENERA 3 OPZIONI DI KEYWORD LONG-TAIL:
        Opzione 1: Massima ricerca (Mainstream)
        Opzione 2: Nicchia chirurgica (Specifico)
        Opzione 3: Angolo innovativo (Disruptive)
        
        Per ogni opzione fornisci KEYWORD e una breve LOGICA.
        Formatta come: 1. [KEYWORD] | [LOGICA]
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def executive_audit(df, query, p_target):
        titles = " | ".join(df['Titolo'].tolist()[:20])
        avg_price = df['Prezzo'].mean()
        prompt = f"Analizza 50 competitor Amazon Libri per '{query}'. Prezzo: {avg_price:.2f}€. Titoli: {titles}. Esegui un audit di 5 righe per il target '{p_target}'."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Genera 5 proposte editoriali (Libri/Ebook) sulla keyword '{kw}'.
        Genere: {p_type} | Target: {p_target} | Problema: {p_pain} | Sogno: {p_dream}.
        Per ogni opzione: 
        1. TITOLO (SEO & Trigger)
        2. ANGOLO DI MARKETING (Perché compra?)
        3. TRAMA DETTAGLIATA (Almeno 200 parole, struttura capitoli e trasformazione).
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. DEEP SCAN 50 (ONLY CATEGORICAL BOOKS)
# ==============================================================================
def run_deep_scan(mkt, keyword, pages_count):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    for page_num in range(1, 5):
        if len(results) >= 50: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page_num}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=30)
            if response.status_code != 200: continue
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            for item in items:
                item_text = item.get_text().lower()
                # Categorical Shield: Filtro metadati libro
                book_triggers = ['copertina', 'pagine', 'kindle', 'formato', 'paperback', 'hardcover', 'editor', 'editore', 'ebook', 'volumi', 'edizione']
                if not any(x in item_text for x in book_triggers): continue

                title = item.h2.text.strip() if item.h2 else "N/A"
                img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                roy = round((price * 0.6) - (2.15 if pages_count <= 108 else 0.60 + (pages_count * 0.012)), 2)
                results.append({"Preview": img, "Titolo": title, "Prezzo": price, "Royalty": roy, "Self-Pub": "Sì" if "independently" in item_text or "pubblicato" in item_text else "No"})
                if len(results) >= 50: break
        except: break
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR: LABORATORIO DI IDEAZIONE
# ==============================================================================
if 'kw_options' not in st.session_state: st.session_state['kw_options'] = ""
if 'final_query' not in st.session_state: st.session_state['final_query'] = ""

with st.sidebar:
    st.title("🛡️ KDP STRATEGY LAB")
    st.info("Su cosa vuoi scrivere oggi?")
    
    with st.container():
        p_type = st.selectbox("Formato/Genere", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"])
        p_target = st.text_input("Target Lettore", placeholder="es. Architetti junior")
        p_pain = st.text_input("Problema/Conflitto", placeholder="es. gestione software BIM")
        p_dream = st.text_input("Sogno/Risultato", placeholder="es. progettazione fluida")
    
    if st.button("🧠 GENERA KEYWORD IPOTETICHE AI", use_container_width=True, type="primary") and API_READY:
        with st.spinner("L'AI sta analizzando angoli profittevoli..."):
            st.session_state['kw_options'] = SurgicalAI.brainstorm_3_keywords(p_type, p_target, p_pain, p_dream)

    if st.session_state['kw_options']:
        st.markdown(f'<div class="ai-sidebar-res"><b>Strategie suggerite:</b><br>{st.session_state["kw_options"]}</div>', unsafe_allow_html=True)
        st.session_state['final_query'] = st.text_input("Copia e incolla qui la tua keyword preferita:", value="")

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    pgs = st.number_input("Pagine Stimate", value=120)
    
    run_btn = st.button("🚀 LANCIA ANALISI MASSIVA (50 LIBRI)", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: ANALISI & MASTER PLAN
# ==============================================================================
if run_btn and st.session_state['final_query'] and API_READY:
    query = st.session_state['final_query']
    st.header(f"📊 Deep Analysis Categorica: {query.upper()}")
    
    with st.spinner("Scansione di 50 competitor editoriali..."):
        df = run_deep_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            audit_res = SurgicalAI.executive_audit(df, query, p_target)
            st.markdown(f'<div class="ai-audit-card"><b>🤖 AI EXECUTIVE AUDIT:</b><br>{audit_res}</div>', unsafe_allow_html=True)

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
                st.header("✍️ Piano Editoriale di Pubblicazione (Testo Garantito)")
                with st.spinner("L'AI sta redigendo i Master Plan..."):
                    master_plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, query)
                    formatted_plan = (master_plan
                        .replace("TITOLO:", " <span class='title-option'>")
                        .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
                        .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                        .replace("1.", "<br><b>1.</b>").replace("2.", "<br><b>2.</b>")
                        .replace("3.", "<br><b>3.</b>").replace("4.", "<br><b>4.</b>")
                        .replace("5.", "<br><b>5.</b>")
                    )
                    st.markdown(f'<div class="editorial-container">{formatted_plan}</div> </div>', unsafe_allow_html=True)
            else:
                st.markdown("---")
                st.header("🔄 Reindirizzamento Strategico (Pivot)")
                st.warning("⚠️ Score insufficiente. Lo Stratega AI consiglia nuovi angoli:")
                pivot_res = SurgicalAI.genera_pivot(p_target, p_pain, p_dream, query)
                st.markdown(f'<div class="pivot-card"><b>Consigli di Riposizionamento:</b><br>{pivot_res.replace("1.", "<br><b>1.</b>").replace("2.", "<br><b>2.</b>").replace("3.", "<br><b>3.</b>")}</div>', unsafe_allow_html=True)
        else:
            st.error("Nessun libro trovato. Verifica che la keyword sia pertinente al settore Libri.")
