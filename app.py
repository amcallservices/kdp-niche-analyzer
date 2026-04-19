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
    page_title="KDP OMNI-REASONER 7.0",
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
        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }

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

        /* AUDIT & GAP */
        .gap-box { background-color: #fff9db; border-left: 10px solid #fab005; padding: 25px; border-radius: 10px; color: #856404; margin-bottom: 30px; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BUSINESS LOGIC & API
# ==============================================================================
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
    WS_API_KEY = st.secrets["WS_API_KEY"]
    client = openai.OpenAI(api_key=OPENAI_KEY)
    API_READY = True
except:
    st.error("⚠️ Chiavi API non trovate nei Secret.")
    API_READY = False

def bsr_to_sales(bsr):
    if not bsr or bsr == 0: return 0
    if bsr < 500: return 3000
    if bsr < 5000: return 900
    if bsr < 20000: return 200
    if bsr < 100000: return 40
    return 3

# ==============================================================================
# 3. SURGICAL AI CLASS (INTEGRATED REASONING)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_keyword(p_type, p_target, p_pain, p_dream):
        prompt = f"""
        Direttore Marketing KDP. Genera UNA SOLA keyword Long-Tail chirurgica per un libro '{p_type}' rivolto a '{p_target}'.
        Dolore: {p_pain} | Sogno: {p_dream}.
        RESTITUISCI SOLO LA KEYWORD E LA LOGICA.
        Formato: KEYWORD: [testo] | LOGICA: [testo]
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def get_market_audit(titles, p_target):
        prompt = f"Analizza 100 competitor KDP: {titles}. Identifica 3 Review Gap per '{p_target}' e scrivi un audit di 5 righe sulla fattibilità competitiva."
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Editor-in-Chief. Genera 5 proposte editoriali complete sulla keyword '{kw}'.
        Target: {p_target} | Genere: {p_type}.
        Per ogni opzione: 
        1. TITOLO (Killer SEO)
        2. ANGOLO DI MARKETING
        3. TRAMA DETTAGLIATA (250 parole)
        4. AI COVER PROMPT (Midjourney tecnico)
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. CENTURION SCANNER (RICERCA CATEGORICA SU 100 LIBRI)
# ==============================================================================
def run_centurion_scan(mkt, keyword, pgs_count):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    # Progresso visibile
    progress_text = st.empty()
    p_bar = st.progress(0)
    
    for page in range(1, 10): # Scansione profonda fino a 10 pagine
        if len(results) >= 100: break
        progress_text.text(f"Scansione Pagina {page}... Libri trovati: {len(results)}")
        p_bar.progress(len(results) / 100 if len(results) < 100 else 1.0)
        
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=35)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                item_text = item.get_text().lower()
                # Filtro Blindato solo Libri
                if not any(x in item_text for x in ['pagine', 'kindle', 'copertina', 'formato', 'paperback', 'hardcover']): continue
                
                title = item.h2.text.strip() if item.h2 else "N/A"
                img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
                
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                
                bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', item_text)
                bsr = int(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else 0
                
                results.append({
                    "Preview": img, "Titolo": title, "Prezzo": price, 
                    "BSR": bsr, "Self": "Sì" if "independently" in item_text or "pubblicato" in item_text else "No"
                })
                if len(results) >= 100: break
        except: break
    
    progress_text.empty()
    p_bar.empty()
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR: LABORATORIO CHIRURGICO
# ==============================================================================
if 'kw_surgical' not in st.session_state: st.session_state['kw_surgical'] = ""
if 'kw_logic' not in st.session_state: st.session_state['kw_logic'] = ""

with st.sidebar:
    st.title("🛡️ KDP STRATEGY LAB 7.0")
    st.markdown("### Configurazione Analisi Profonda")
    p_type = st.selectbox("Formato", ["Saggio Scientifico", "Manuale Tecnico", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Manuale Psicologico", "Ricettario", "Spirituale / Esoterico"])
    p_target = st.text_input("Identikit Target", placeholder="es. Imprenditori Digitali")
    p_pain = st.text_input("Patologia (Dolore)", placeholder="es. tasse elevate")
    p_dream = st.text_input("Prognosi (Sogno)", placeholder="es. libertà finanziaria")
    
    if st.button("🧠 GENERA KEYWORD CHIRURGICA AI", use_container_width=True, type="primary") and API_READY:
        with st.spinner("L'AI sta dissezionando il bisogno..."):
            res = SurgicalAI.brainstorm_keyword(p_type, p_target, p_pain, p_dream)
            if "KEYWORD:" in res:
                st.session_state['kw_surgical'] = res.split("KEYWORD:")[1].split("|")[0].strip()
                st.session_state['kw_logic'] = res.split("LOGICA:")[1].strip()

    if st.session_state['kw_logic']:
        st.markdown(f'<div style="background:#161b22; padding:15px; border-radius:8px; border-left:4px solid #3182ce; color:#90cdf4; font-size:0.85rem; margin-top:15px;"><b>AI INSIGHT:</b><br>{st.session_state["kw_logic"]}</div>', unsafe_allow_html=True)
        st.session_state['final_q'] = st.text_input("Conferma o modifica la Keyword:", value=st.session_state['kw_surgical'])

    st.markdown("---")
    mkt = st.selectbox("Mercato Amazon", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    pgs = st.number_input("Pagine Libro", value=120)
    run_btn = st.button("🚀 LANCIA CENTURION SCAN (100 LIBRI)", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: FINANCIAL FORECAST & REDAZIONE
# ==============================================================================
if run_btn and st.session_state.get('final_q') and API_READY:
    query = st.session_state['final_q']
    st.header(f"📊 Report Centurion: {query.upper()}")
    
    with st.spinner("Scansione massiva di 100 competitor editoriali..."):
        df = run_centurion_scan(mkt, query, pgs)
        
        if df is not None and not df.empty:
            # Audit Qualitativo
            titles_audit = " | ".join(df['Titolo'].tolist()[:20])
            audit_report = SurgicalAI.get_market_audit(titles_audit, p_target)
            st.markdown(f'<div class="gap-box"><b>🤖 AI EXECUTIVE AUDIT (Sentiment & Gap):</b><br>{audit_report}</div>', unsafe_allow_html=True)

            # Tabella Dati
            st.dataframe(df, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
            
            # Calcolo Metriche su 100 libri
            avg_p = df['Prezzo'].mean()
            self_ratio = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            
            # Forecast Profitto (Normalizzato su 100 campioni)
            df['Est_Sales'] = df['BSR'].apply(bsr_to_sales)
            cost = 2.15 if pgs <= 108 else 0.60 + (pgs * 0.012)
            df['Est_Profit'] = df.apply(lambda r: r['Est_Sales'] * ((r['Prezzo'] * 0.6) - cost), axis=1)
            total_cash = df['Est_Profit'].sum() / 10 # Media ponderata per competitività nicchia
            
            o_score = 40
            if avg_p > 13.50: o_score += 30
            if self_ratio > 45: o_score += 30
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo Medio (100 Libri)", f"{avg_p:.2f} €")
            c2.metric("Profitto Stimato/Mese", f"€ {int(total_cash)}")
            c3.metric("Opportunity Score", f"{o_score}/100")

            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Piano Editoriale di Pubblicazione (Centurion Plan)")
                with st.spinner("Generazione Master Plan..."):
                    master_plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, query)
                    formatted_plan = (master_plan
                        .replace("TITOLO:", " <span class='title-option'>")
                        .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
                        .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                        .replace("AI COVER PROMPT:", "</div> <div class='ai-cover-prompt'>🎨 <b>AI COVER PROMPT:</b> ")
                    )
                    st.markdown(f'<div class="editorial-container">{formatted_plan}</div> </div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Score insufficiente. L'AI sconsiglia questa nicchia specifica.")
        else:
            st.error("Amazon ha limitato la richiesta. Attendi 60 secondi e riprova.")
