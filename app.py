import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (MASTER DARK & HIGH CONTRAST)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 3.4",
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

        /* FIX COLORI METRICHE */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #444c56 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 15px !important; border-radius: 12px !important; }

        /* BOX RAGIONAMENTO AI */
        .gpt-logic-box { background-color: #1c2128; border-left: 5px solid #3182ce; padding: 15px; border-radius: 8px; color: #90cdf4; font-size: 0.88rem; margin-bottom: 20px; }
        .ai-audit-card { background-color: #fff9db; border-left: 6px solid #fab005; padding: 20px; border-radius: 10px; color: #856404; margin-bottom: 25px; }
        
        /* PIANO EDITORIALE - NUOVO STILE AD ALTO CONTRASTO DARK */
        .editorial-container {
            background-color: #161b22; 
            border: 1px solid #30363d; 
            padding: 30px; 
            border-radius: 15px; 
            margin-bottom: 25px; 
            border-top: 8px solid #238636;
        }
        .title-option { color: #ffd700 !important; font-size: 1.6rem; font-weight: 800; display: block; margin-bottom: 10px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .marketing-angle { color: #58a6ff !important; font-weight: 700; font-size: 1rem; margin-bottom: 15px; display: block; font-family: monospace; }
        .plot-detailed { color: #c9d1d9 !important; line-height: 1.8; font-size: 1.05rem; white-space: pre-wrap; }

        /* PIVOT CARD */
        .pivot-card {
            background-color: #1c2128; border: 1px solid #444c56; padding: 20px;
            border-radius: 12px; margin-bottom: 20px; border-left: 6px solid #673ab7;
            color: #f0f6fc !important;
        }
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
    st.error("⚠️ Configurazione Secret mancante o errata.")
    API_READY = False

# ==============================================================================
# 3. CLASSE SURGICAL AI (RAGIONAMENTO OMNIBUS)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        prompt = f"Esperto KDP. Genera keyword Long Tail per Amazon Libri. Genere: {p_type}, Target: {p_target}, Dolore: {p_pain}, Sogno: {p_dream}. Output: KEYWORD: [testo] | LOGICA: [testo]"
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def executive_audit(df, query, p_target):
        titles = " | ".join(df['Titolo'].tolist()[:20]) # Analizza più titoli per l'audit
        avg_price = df['Prezzo'].mean()
        prompt = f"Analizza 50 competitor per '{query}'. Prezzo Medio: {avg_price:.2f}€. Titoli: {titles}. Esegui un audit di 5 righe per il target '{p_target}'."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Editor-in-Chief KDP. Genera 5 proposte editoriali (Libri/Ebook) sulla keyword '{kw}'.
        Genere: {p_type}. Target: {p_target}. Problema: {p_pain}. Sogno: {p_dream}.
        Per ogni opzione fornisci:
        - TITOLO: SEO impact.
        - ANGOLO DI MARKETING: Perché attira il target.
        - TRAMA DETTAGLIATA: Almeno 180 parole, struttura e benefici.
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. MOTORE DI SCRAPING (PAGINAZIONE FINO A 50 RISULTATI)
# ==============================================================================
def run_strategic_scan(mkt, keyword, pages_count):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    # LOOP PAGINAZIONE PER RAGGIUNGERE 50 LIBRI
    for page_num in range(1, 5): # Scansiona fino a 4 pagine per trovare 50 libri "puliti"
        if len(results) >= 50: break
        
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page_num}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=30)
            if response.status_code != 200: continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                item_text = item.get_text().lower()
                book_triggers = ['copertina', 'pagine', 'kindle', 'formato', 'paperback', 'hardcover', 'editor', 'editore', 'ebook', 'volumi', 'edizione', 'illustrato']
                if not any(x in item_text for x in book_triggers):
                    continue

                title = item.h2.text.strip() if item.h2 else "N/A"
                img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                
                cost = 2.15 if pages_count <= 108 else 0.60 + (pages_count * 0.012)
                roy = round((price * 0.6) - cost, 2)
                
                results.append({"Preview": img, "Titolo": title, "Prezzo": price, "Royalty": roy, "Self-Pub": "Sì" if "independently" in item_text or "pubblicato" in item_text else "No"})
                if len(results) >= 50: break
        except: break
        
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR: COMANDI
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""
if 'ai_logic' not in st.session_state: st.session_state['ai_logic'] = ""

with st.sidebar:
    st.title("🛡️ OMNI-STRATEGY AI")
    st.caption("Deep Scan 50 Libri | Filtro Categorico Attivo ✅")
    
    p_type = st.selectbox("Genere / Formato", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"])
    p_target = st.text_input("Target", placeholder="es. Insegnanti")
    p_pain = st.text_input("Problema", placeholder="es. stress")
    p_dream = st.text_input("Sogno", placeholder="es. calma")
    
    if st.button("🧠 GENERA STRATEGIA AI", use_container_width=True, type="primary"):
        res = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
        if "KEYWORD:" in res:
            st.session_state['kw_active'] = res.split("KEYWORD:")[1].split("|")[0].strip()
            st.session_state['ai_logic'] = res.split("LOGICA:")[1].strip()

    if st.session_state['ai_logic']:
        st.markdown(f'<div class="gpt-logic-box">{st.session_state["ai_logic"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Focus", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine Libro", value=120)
    run_btn = st.button("LANCIA DEEP SCAN", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD PRINCIPALE
# ==============================================================================
if run_btn and query and API_READY:
    st.header(f"📚 Report Deep Scan: {query.upper()}")
    
    with st.spinner("Scansione massiva di 50 competitor..."):
        df = run_strategic_scan(mkt, query, pgs)
        
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
                st.header("✍️ Piano Editoriale Strategico (Testo Garantito Leggibile)")
                master_plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, query)
                
                # FORMATTAZIONE CON FORZA COLORE PER DARK MODE
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
                st.warning("Score < 60. L'AI sconsiglia la redazione automatica.")
