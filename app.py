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
    page_title="KDP OMNI-REASONER 6.1",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { min-width: 480px !important; background-color: #0d1117 !important; border-right: 1px solid #30363d; }

        /* METRICHE - CASH FOCUS */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; font-size: 1.6rem !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #238636 !important; padding: 15px !important; border-radius: 10px !important; }

        /* WINNER BANNER GOLD */
        .winner-box {
            background-color: #0d1117; color: #ffd700; padding: 30px; border-radius: 15px;
            text-align: center; font-weight: 900; font-size: 2rem; margin: 30px 0;
            border: 4px solid #ffd700; box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
        }

        /* MASTER PLAN CONTAINER (FORZA COLORI) */
        .editorial-container {
            background-color: #0d1117; border: 2px solid #30363d; padding: 40px; 
            border-radius: 15px; margin-bottom: 25px; border-top: 12px solid #ffd700;
        }
        .title-option { color: #ffd700 !important; font-size: 1.8rem; font-weight: 900; display: block; margin-bottom: 10px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .marketing-angle { color: #58a6ff !important; font-weight: 700; font-size: 1.1rem; margin-bottom: 15px; display: block; font-family: monospace; }
        .plot-detailed { color: #e6edf3 !important; line-height: 1.8; font-size: 1.1rem; white-space: pre-wrap; margin-bottom: 20px; }
        .ai-cover-prompt { background-color: #161b22; border: 1px dashed #58a6ff; padding: 15px; color: #8b949e; font-size: 0.9rem; border-radius: 8px; margin-top: 15px; }

        .gap-box { background-color: #fff9db; border-left: 8px solid #fab005; padding: 20px; border-radius: 10px; color: #856404; margin-bottom: 20px; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI BUSINESS (BSR TO SALES)
# ==============================================================================
def bsr_to_sales(bsr):
    if not bsr or bsr == 0 or bsr == "N/D": return 0
    if bsr < 500: return 2500
    if bsr < 5000: return 800
    if bsr < 20000: return 150
    if bsr < 100000: return 30
    return 2

# ==============================================================================
# 3. SURGICAL AI ENGINE v6.1 (DUAL CORE)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_2_keywords(p_type, p_target, p_pain, p_dream):
        """Genera esattamente 2 keyword strategiche."""
        prompt = f"""
        Direttore Marketing KDP. Genera esattamente 2 Keyword Long-Tail per '{p_type}' rivolto a '{p_target}'.
        Problema: {p_pain} | Sogno: {p_dream}.
        Keyword 1: Dominante/Mainstream.
        Keyword 2: Chirurgica/Nicchia profonda.
        RESTITUISCI SOLO LE 2 KEYWORD SEPARATE DA '||'. Esempio: Key1 || Key2
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def get_review_gap(titles, p_target):
        prompt = f"Analizza titoli competitor: {titles}. Identifica 2 lacune (Review Gap) per il target '{p_target}' e come differenziarsi."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Genera 5 proposte editoriali per: '{kw}'. Genere: {p_type} | Target: {p_target}.
        Per ogni opzione: 
        1. TITOLO
        2. ANGOLO DI MARKETING
        3. TRAMA DETTAGLIATA (200 parole)
        4. AI COVER PROMPT (Midjourney)
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. DEEP SCAN ENGINE (ONLY BOOKS)
# ==============================================================================
def run_ultra_scan(mkt, keyword, pages_count=120):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    for page_num in range(1, 4):
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page_num}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': st.secrets["WS_API_KEY"], 'url': target_url, 'proxy': 'residential'}, timeout=30)
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
                if len(results) >= 30: break
        except: break
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR: LABORATORIO 2 KEYWORD
# ==============================================================================
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("Chiavi API mancanti nei Secrets.")
    API_READY = False

if 'dual_kws' not in st.session_state: st.session_state['dual_kws'] = []

with st.sidebar:
    st.title("🛡️ STRATEGY LAB 2.0")
    st.subheader("Cosa vuoi scrivere?")
    p_type = st.selectbox("Genere", ["Manuale Tecnico", "Saggio Scientifico", "Business", "Romanzo", "Spirituale", "Ricettario"])
    p_target = st.text_input("Target", placeholder="es. Manager")
    p_pain = st.text_input("Dolore", placeholder="es. poco tempo")
    p_dream = st.text_input("Sogno", placeholder="es. efficienza")
    
    if st.button("🧠 GENERA 2 KEYWORD STRATEGICHE", use_container_width=True, type="primary") and API_READY:
        res = SurgicalAI.brainstorm_2_keywords(p_type, p_target, p_pain, p_dream)
        st.session_state['dual_kws'] = [k.strip() for k in res.split("||")][:2]

    if st.session_state['dual_kws']:
        st.success("2 Keyword Pronte per l'analisi:")
        for i, k in enumerate(st.session_state['dual_kws']):
            st.code(f"{i+1}. {k}")

    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    pgs = st.number_input("Pagine", value=120)
    run_all = st.button("🚀 LANCIA ANALISI COMPARATIVA", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: BATTLE OF TWO
# ==============================================================================
if run_all and st.session_state['dual_kws'] and API_READY:
    st.header("⚖️ Comparazione Dual-Core")
    
    battle_data = {}
    current_kws = st.session_state['dual_kws']
    cols = st.columns(len(current_kws))
    
    for i, kw in enumerate(current_kws):
        # PROTEZIONE INDEXERROR: La colonna i esiste sempre perché cols è creato su len(current_kws)
        with cols[i]:
            st.subheader(f"Opzione {i+1}")
            st.info(f"Analisi: {kw}")
            with st.spinner("Scansione..."):
                df = run_ultra_scan(mkt, kw, pgs)
                if not df.empty:
                    avg_p = df['Prezzo'].mean()
                    self_ratio = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
                    
                    df['Est_Sales'] = df['BSR'].apply(bsr_to_sales)
                    cost = 2.15 if pgs <= 108 else 0.60 + (pgs * 0.012)
                    df['Est_Profit'] = df.apply(lambda r: r['Est_Sales'] * ((r['Prezzo'] * 0.6) - cost), axis=1)
                    total_monthly_cash = df['Est_Profit'].sum() / (len(df)/10)
                    
                    o_score = 40
                    if avg_p > 13.50: o_score += 30
                    if self_ratio > 45: o_score += 30
                    
                    st.metric("Opportunity Score", f"{o_score}/100")
                    st.metric("Profitto/Mese Est.", f"€ {int(total_monthly_cash)}")
                    st.metric("Indie Ratio", f"{int(self_ratio)}%")
                    
                    battle_data[kw] = {"score": o_score, "df": df, "cash": total_monthly_cash}
                    with st.expander("Vedi Dettaglio Libri"):
                        st.dataframe(df, column_config={"Preview": st.column_config.ImageColumn("Preview")}, hide_index=True)
                else: 
                    st.warning("Nessun dato trovato.")
                    battle_data[kw] = {"score": 0, "df": None}

    if battle_data:
        winner_kw = max(battle_data, key=lambda k: battle_data[k]['score'])
        st.markdown(f'<div class="winner-box">🏆 VINCITORE: {winner_kw.upper()}</div>', unsafe_allow_html=True)
        
        # --- REVIEW GAP ---
        if battle_data[winner_kw]['df'] is not None:
            titles = " | ".join(battle_data[winner_kw]['df']['Titolo'].tolist()[:10])
            st.markdown(f'<div class="gap-box"><b>🔍 REVIEW GAP ANALYSIS:</b><br>{SurgicalAI.get_review_gap(titles, p_target)}</div>', unsafe_allow_html=True)
        
        # --- MASTER PLAN ---
        if battle_data[winner_kw]['score'] >= 60:
            with st.spinner("Generazione Master Plan..."):
                plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, winner_kw)
                formatted_plan = (plan
                    .replace("TITOLO:", " <span class='title-option'>")
                    .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
                    .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                    .replace("AI COVER PROMPT:", "</div> <div class='ai-cover-prompt'>🎨 <b>AI COVER PROMPT:</b> ")
                )
                st.markdown(f'<div class="editorial-container">{formatted_plan}</div> </div>', unsafe_allow_html=True)
