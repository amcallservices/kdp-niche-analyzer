import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
import io

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (MASTER DARK & HIGH CONTRAST)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 7.2",
    page_icon="🐜",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { min-width: 450px !important; background-color: #0d1117 !important; border-right: 1px solid #30363d; }

        /* METRICHE */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; font-size: 1.8rem !important; }
        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }

        /* CONTAINER PIANO EDITORIALE */
        .editorial-container {
            background-color: #0b0e14 !important; 
            border: 2px solid #30363d !important; 
            padding: 40px !important; 
            border-radius: 15px !important; 
            margin-bottom: 30px !important; 
            border-top: 12px solid #ffd700 !important;
        }
        .title-option { color: #ffd700 !important; font-size: 1.8rem !important; font-weight: 900 !important; display: block !important; margin-bottom: 12px !important; border-bottom: 1px solid #30363d !important; padding-bottom: 10px !important; }
        .marketing-angle { color: #58a6ff !important; font-weight: 700 !important; font-size: 1.1rem !important; margin-bottom: 15px !important; display: block !important; font-family: 'Courier New', monospace !important; }
        .plot-detailed { color: #e6edf3 !important; line-height: 1.9 !important; font-size: 1.15rem !important; white-space: pre-wrap !important; margin-bottom: 25px !important; }
        .ai-cover-prompt { background-color: #161b22 !important; border: 1px dashed #58a6ff !important; padding: 15px !important; color: #8b949e !important; font-size: 0.95rem !important; border-radius: 8px !important; }

        .gap-box { background-color: #fff9db; border-left: 10px solid #fab005; padding: 25px; border-radius: 10px; color: #856404; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE API & SESSIONE
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    # Cerchiamo la chiave OpenAI nei Secret per sicurezza
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ OpenAI API Key non trovata nei Secret di Streamlit.")
    API_READY = False

# Persistenza dati
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'audit' not in st.session_state: st.session_state.audit = ""
if 'plan' not in st.session_state: st.session_state.plan = ""

# ==============================================================================
# 3. LOGICA DI BUSINESS (ROYALTY MATH)
# ==============================================================================
def bsr_to_sales(bsr):
    if not bsr or bsr == 0: return 0
    if bsr < 1000: return 1200
    if bsr < 10000: return 350
    if bsr < 50000: return 70
    if bsr < 100000: return 20
    return 2

# ==============================================================================
# 4. MOTORE DI SCRAPING (SCRAPINGANT OPTIMIZED)
# ==============================================================================
def run_centurion_ant_scan(mkt, keyword, pgs):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    p_bar = st.progress(0)
    for page in range(1, 11): # Analisi profonda 10 pagine
        if len(results) >= 100: break
        
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        # Configurazione ScrapingAnt: browser=false consuma solo 1 credito
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(target_url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
        
        try:
            response = requests.get(api_url, timeout=35)
            # Fallback se serve JS
            if response.status_code != 200:
                response = requests.get(api_url.replace("browser=false", "browser=true"), timeout=45)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                item_text = item.get_text().lower()
                if not any(x in item_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
                
                title = item.h2.text.strip() if item.h2 else "N/A"
                img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
                
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                
                bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', item_text)
                bsr = int(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else 0
                
                results.append({
                    "Preview": img, "Titolo": title, "Prezzo": price, 
                    "BSR": bsr, "Self": "Sì" if "independently" in item_text else "No"
                })
                if len(results) >= 100: break
            p_bar.progress(len(results) / 100 if len(results) < 100 else 1.0)
        except: break
    
    p_bar.empty()
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR COMMAND CENTER
# ==============================================================================
with st.sidebar:
    st.title("🛡️ ANT-STRATEGY LAB 7.2")
    if st.button("🔄 NUOVA RICERCA (Reset)"):
        st.session_state.results_df = None
        st.session_state.plan = ""
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere", ["Saggio", "Manuale Tecnico", "Business", "Romanzo", "Ricettario", "Spirituale"])
    p_target = st.text_input("Target", placeholder="es. Trader")
    p_pain = st.text_input("Dolore", placeholder="es. perdite emotive")
    p_dream = st.text_input("Sogno", placeholder="es. profitto costante")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary") and API_READY:
        prompt = f"Genera UNA keyword Long-Tail per '{p_type}' rivolto a '{p_target}'. Dolore: {p_pain} | Sogno: {p_dream}. Risposta: KEYWORD: [testo] | LOGICA: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()
        st.session_state.kw_logic = res.split("LOGICA:")[1].strip()

    if 'kw_active' in st.session_state:
        st.info(f"**AI Strategy:** {st.session_state.kw_logic}")
        final_q = st.text_input("Keyword finale:", value=st.session_state.kw_active)
    
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    pgs = st.number_input("Pagine", value=120)
    run_btn = st.button("🚀 LANCIA CENTURION SCAN", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: ANALISI & PROFITTI
# ==============================================================================
if run_btn and API_READY:
    with st.spinner("Analisi ScrapingAnt in corso..."):
        df = run_centurion_ant_scan(mkt, final_q, pgs)
        if not df.empty:
            st.session_state.results_df = df
            # Audit Qualitativo
            titles = " | ".join(df['Titolo'].tolist()[:15])
            audit_prompt = f"Audit 100 libri per '{final_q}': {titles}. Identifica 3 gap per {p_target}."
            st.session_state.audit = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": audit_prompt}]).choices[0].message.content
            
            # Calcolo Financials
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            
            # Formula Royalty: $R = (P \cdot 0.6) - Cost$
            cost = 2.15 if pgs <= 108 else 0.60 + (pgs * 0.012)
            df['Est_Profit'] = df['BSR'].apply(bsr_to_sales) * ((df['Prezzo'] * 0.6) - cost)
            st.session_state.cash = df['Est_Profit'].sum() / 10
            st.session_state.score = 40 + (30 if avg_p > 13 else 0) + (30 if self_r > 45 else 0)
            
            if st.session_state.score >= 60:
                plan_prompt = f"Genera Master Plan 5 titoli/trame per '{final_q}'. Target: {p_target}."
                st.session_state.plan = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": plan_prompt}]).choices[0].message.content

# Mostriamo i risultati se presenti in sessione
if st.session_state.results_df is not None:
    st.header(f"📊 Report Strategico: {final_q.upper()}")
    st.markdown(f'<div class="gap-box"><b>🤖 AI EXECUTIVE AUDIT:</b><br>{st.session_state.audit}</div>', unsafe_allow_html=True)
    
    st.dataframe(st.session_state.results_df, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Punteggio Nicchia", f"{st.session_state.score}/100")
    c2.metric("Profitto Stimato/Mese", f"€ {int(st.session_state.cash)}")
    c3.metric("Indie Ratio", f"{int((len(st.session_state.results_df[st.session_state.results_df['Self'] == 'Sì']) / len(st.session_state.results_df)) * 100)}%")

    if st.session_state.plan:
        st.markdown("---")
        st.header("✍️ Master Plan Editoriale")
        f_plan = (st.session_state.plan
            .replace("TITOLO:", " <span class='title-option'>")
            .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
            .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
            .replace("AI COVER PROMPT:", "</div> <div class='ai-cover-prompt'>🎨 <b>AI COVER PROMPT:</b> ")
        )
        st.markdown(f'<div class="editorial-container">{f_plan}</div> </div>', unsafe_allow_html=True)
