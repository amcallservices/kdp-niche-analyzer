import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
import io

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (ALTO CONTRASTO & DARK)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 7.1",
    page_icon="💯",
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

        /* CONTAINER PIANO EDITORIALE - CONTRASTO TOTALE */
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
# 2. GESTIONE SESSIONE (IRON STATE)
# ==============================================================================
# Inizializziamo le variabili nella sessione per evitare che i dati spariscano
if 'df_results' not in st.session_state: st.session_state.df_results = None
if 'audit_report' not in st.session_state: st.session_state.audit_report = ""
if 'master_plan' not in st.session_state: st.session_state.master_plan = ""
if 'kw_surgical' not in st.session_state: st.session_state.kw_surgical = ""
if 'kw_logic' not in st.session_state: st.session_state.kw_logic = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'cash' not in st.session_state: st.session_state.cash = 0

# ==============================================================================
# 3. BUSINESS LOGIC & API
# ==============================================================================
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ OpenAI API Key mancante nei Secret.")
    API_READY = False

def bsr_to_sales(bsr):
    if not bsr or bsr == 0: return 0
    if bsr < 1000: return 1500
    if bsr < 10000: return 400
    if bsr < 50000: return 80
    if bsr < 100000: return 20
    return 2

# ==============================================================================
# 4. SURGICAL AI CLASS
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        prompt = f"Direttore Marketing KDP. Genera UNA keyword Long-Tail per '{p_type}' rivolto a '{p_target}'. Dolore: {p_pain} | Sogno: {p_dream}. Rispondi: KEYWORD: [testo] | LOGICA: [testo]"
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def get_market_audit(titles, p_target):
        prompt = f"Analizza 100 competitor KDP: {titles}. Identifica 3 lacune per '{p_target}' e scrivi un audit di 5 righe."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"Editor Bestseller. Genera 5 proposte per '{kw}'. Target: {p_target} | Genere: {p_type}. Ogni opzione: TITOLO, ANGOLO MARKETING, TRAMA (250 parole), AI COVER PROMPT."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 5. CENTURION SCANNER (100 LIBRI)
# ==============================================================================
def run_centurion_scan(mkt, keyword, pgs_count):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    p_bar = st.progress(0)
    for page in range(1, 11): 
        if len(results) >= 100: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': st.secrets["WS_API_KEY"], 'url': target_url, 'proxy': 'residential'}, timeout=35)
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
                results.append({"Preview": img, "Titolo": title, "Prezzo": price, "BSR": bsr, "Self": "Sì" if "independently" in item_text else "No"})
                if len(results) >= 100: break
            p_bar.progress(len(results) / 100 if len(results) < 100 else 1.0)
        except: break
    p_bar.empty()
    return pd.DataFrame(results)

# ==============================================================================
# 6. SIDEBAR: LABORATORIO
# ==============================================================================
with st.sidebar:
    st.title("🛡️ KDP STRATEGY LAB 7.1")
    if st.button("🔄 RESET TOTALE (Svuota Memoria)", use_container_width=True):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Formato", ["Saggio Scientifico", "Manuale Tecnico", "Business", "Romanzo", "Spirituale", "Ricettario"])
    p_target = st.text_input("Target", placeholder="es. Imprenditori")
    p_pain = st.text_input("Dolore", placeholder="es. poco tempo")
    p_dream = st.text_input("Sogno", placeholder="es. libertà")
    
    if st.button("🧠 GENERA KEYWORD AI", use_container_width=True, type="primary") and API_READY:
        res = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
        if "KEYWORD:" in res:
            st.session_state.kw_surgical = res.split("KEYWORD:")[1].split("|")[0].strip()
            st.session_state.kw_logic = res.split("LOGICA:")[1].strip()

    if st.session_state.kw_logic:
        st.info(f"**AI INSIGHT:** {st.session_state.kw_logic}")
        final_q = st.text_input("Keyword da analizzare:", value=st.session_state.kw_surgical)
    
    mkt = st.selectbox("Mercato Amazon", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    pgs = st.number_input("Pagine Libro", value=120)
    run_btn = st.button("🚀 LANCIA CENTURION SCAN", use_container_width=True)

# ==============================================================================
# 7. DASHBOARD: PERSISTENZA DEI RISULTATI
# ==============================================================================
if run_btn and final_q and API_READY:
    with st.spinner("Scansione di 100 competitor..."):
        df = run_centurion_scan(mkt, final_q, pgs)
        if not df.empty:
            st.session_state.df_results = df
            st.session_state.audit_report = SurgicalAI.get_market_audit(" | ".join(df['Titolo'].tolist()[:20]), p_target)
            
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            df['Est_Sales'] = df['BSR'].apply(bsr_to_sales)
            cost = 2.15 if pgs <= 108 else 0.60 + (pgs * 0.012)
            # Formula Royalty: $ R = (Prezzo \times 0.6) - Costo $
            df['Est_Profit'] = df.apply(lambda r: r['Est_Sales'] * ((r['Prezzo'] * 0.6) - cost), axis=1)
            
            st.session_state.score = 40 + (30 if avg_p > 13.50 else 0) + (30 if self_r > 45 else 0)
            st.session_state.cash = df['Est_Profit'].sum() / 10
            
            if st.session_state.score >= 60:
                st.session_state.master_plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, final_q)

# VISUALIZZAZIONE DATI (Se esistono nella sessione)
if st.session_state.df_results is not None:
    st.header(f"📊 Report Centurion: {final_q.upper()}")
    
    st.markdown(f'<div class="gap-box"><b>🤖 AI MARKET AUDIT:</b><br>{st.session_state.audit_report}</div>', unsafe_allow_html=True)
    
    st.dataframe(st.session_state.df_results, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Punteggio Nicchia", f"{st.session_state.score}/100")
    c2.metric("Profitto Stimato/Mese", f"€ {int(st.session_state.cash)}")
    c3.metric("Indie Ratio (Self)", f"{int((len(st.session_state.df_results[st.session_state.df_results['Self'] == 'Sì']) / len(st.session_state.df_results)) * 100)}%")

    if st.session_state.master_plan:
        st.markdown("---")
        st.header("✍️ Master Plan Editoriale")
        plan = st.session_state.master_plan
        formatted_plan = (plan
            .replace("TITOLO:", " <span class='title-option'>")
            .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
            .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
            .replace("AI COVER PROMPT:", "</div> <div class='ai-cover-prompt'>🎨 <b>AI COVER PROMPT:</b> ")
        )
        st.markdown(f'<div class="editorial-container">{formatted_plan}</div> </div>', unsafe_allow_html=True)
