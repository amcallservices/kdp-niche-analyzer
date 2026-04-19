import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (MASTER DARK & DATA-DRIVEN)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 5.1",
    page_icon="📊",
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
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-weight: 800 !important; font-size: 1.5rem !important; }
        .stMetric { background-color: #ffffff !important; border-left: 8px solid #0969da !important; padding: 10px !important; border-radius: 10px !important; }

        /* WINNER BANNER */
        .winner-box {
            background-color: #238636; color: white; padding: 25px; border-radius: 12px;
            text-align: center; font-weight: 900; font-size: 1.8rem; margin: 30px 0;
            border: 3px solid #2ea043; box-shadow: 0 0 25px rgba(35, 134, 54, 0.5);
        }

        /* PIANO EDITORIALE - HIGH CONTRAST */
        .editorial-container {
            background-color: #0d1117; 
            border: 2px solid #30363d; 
            padding: 35px; 
            border-radius: 15px; 
            margin-bottom: 25px; 
            border-top: 10px solid #ffd700;
        }
        .title-option { color: #ffd700 !important; font-size: 1.7rem; font-weight: 900; display: block; margin-bottom: 12px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .marketing-angle { color: #58a6ff !important; font-weight: 700; font-size: 1.1rem; margin-bottom: 15px; display: block; font-family: monospace; }
        .plot-detailed { color: #e6edf3 !important; line-height: 1.9; font-size: 1.1rem; white-space: pre-wrap; margin-bottom: 30px; }

        .keyword-card {
            background-color: #161b22; border: 1px solid #30363d; padding: 15px;
            border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #3182ce;
        }
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
    st.error("⚠️ Configurazione Secret non trovata.")
    API_READY = False

# ==============================================================================
# 3. SURGICAL AI ENGINE (COMPARATIVE LOGIC)
# ==============================================================================
class SurgicalAI:
    @staticmethod
    def brainstorm_3_keywords(p_type, p_target, p_pain, p_dream):
        prompt = f"""
        Direttore Marketing KDP. Genera 3 diverse Keyword Long-Tail per '{p_type}' rivolto a '{p_target}'.
        Problema: {p_pain} | Sogno: {p_dream}.
        Restituisci SOLO le 3 keyword separate da '||'. Esempio: Key1 || Key2 || Key3
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def genera_master_plan(p_type, p_target, p_pain, p_dream, kw):
        prompt = f"""
        Genera 5 proposte editoriali su: '{kw}'.
        Genere: {p_type} | Target: {p_target} | Problema: {p_pain} | Sogno: {p_dream}.
        Per ogni opzione: TITOLO | ANGOLO DI MARKETING | TRAMA DETTAGLIATA (Almeno 200 parole).
        """
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

# ==============================================================================
# 4. DEEP SCAN ENGINE (ULTRA-DATA)
# ==============================================================================
def run_ultra_scan(mkt, keyword, pages_count=120):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    
    # Scansioniamo fino a 3 pagine per ottenere dati solidi
    for page_num in range(1, 4):
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page_num}"
        try:
            response = requests.get('https://api.webscraping.ai/html', params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'}, timeout=30)
            if response.status_code != 200: continue
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                item_text = item.get_text().lower()
                # Filtro Libri
                if not any(x in item_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue

                title = item.h2.text.strip() if item.h2 else "N/A"
                img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
                
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                
                # Estrazione BSR (Metodo Rapido da anteprima se presente o Mock)
                bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', item_text)
                bsr = int(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else 0
                
                cost = 2.15 if pages_count <= 108 else 0.60 + (pages_count * 0.012)
                roy = round((price * 0.6) - cost, 2)
                
                results.append({
                    "Preview": img,
                    "Titolo": title[:80] + "...",
                    "Prezzo": price,
                    "Royalty": roy,
                    "BSR": bsr if bsr > 0 else "N/D",
                    "Self": "Sì" if "independently" in item_text or "pubblicato" in item_text else "No"
                })
                if len(results) >= 40: break
        except: break
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR: LABORATORIO DI IDEAZIONE
# ==============================================================================
if 'kws_battle' not in st.session_state: st.session_state['kws_battle'] = []

with st.sidebar:
    st.title("⚔️ KDP NICHE BATTLE")
    st.info("Configura il tuo progetto per iniziare la competizione tra nicchie.")
    
    p_type = st.selectbox("Genere", ["Manuale Tecnico", "Saggio Scientifico", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario", "Spirituale / Esoterico"])
    p_target = st.text_input("Target", placeholder="es. Architetti junior")
    p_pain = st.text_input("Dolore", placeholder="es. burnout da disegno")
    p_dream = st.text_input("Sogno", placeholder="es. progettazione Zen")
    
    if st.button("🧠 GENERA 3 STRATEGIE", use_container_width=True, type="primary") and API_READY:
        res = SurgicalAI.brainstorm_3_keywords(p_type, p_target, p_pain, p_dream)
        st.session_state['kws_battle'] = [k.strip() for k in res.split("||")]

    if st.session_state['kws_battle']:
        st.markdown("### Keyword in Gara:")
        for i, k in enumerate(st.session_state['kws_battle']):
            st.markdown(f'<div class="keyword-card"><b>{i+1}:</b> {k}</div>', unsafe_allow_html=True)

    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    run_battle = st.button("🚀 LANCIA BATTAGLIA DATI", use_container_width=True)

# ==============================================================================
# 6. DASHBOARD: ANALISI COMPARATIVA & LISTA LIBRI
# ==============================================================================
if run_battle and st.session_state['kws_battle'] and API_READY:
    st.header("🏁 Analisi Comparativa delle Nicchie")
    
    
    battle_data = {}
    cols = st.columns(len(st.session_state['kws_battle']))
    
    for i, kw in enumerate(st.session_state['kws_battle']):
        with cols[i]:
            st.subheader(f"Opzione {i+1}")
            st.caption(f"🔍 {kw}")
            with st.spinner(f"Scansione..."):
                df = run_ultra_scan(mkt, kw)
                if not df.empty:
                    # Metriche
                    avg_p = df['Prezzo'].mean()
                    self_ratio = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
                    bsr_list = [b for b in df['BSR'] if isinstance(b, int)]
                    avg_bsr = sum(bsr_list) / len(bsr_list) if bsr_list else "N/D"
                    
                    o_score = 40
                    if avg_p > 13.50: o_score += 30
                    if self_ratio > 45: o_score += 30
                    
                    st.metric("Score", f"{o_score}/100")
                    st.metric("Prezzo Med.", f"{avg_p:.2f} €")
                    st.metric("Indie Ratio", f"{int(self_ratio)}%")
                    st.metric("BSR Medio", f"{int(avg_bsr) if isinstance(avg_bsr, float) else avg_bsr}")
                    
                    battle_data[kw] = {"score": o_score, "df": df}
                    
                    with st.expander("Vedi Libri Analizzati"):
                        st.dataframe(
                            df, 
                            column_config={"Preview": st.column_config.ImageColumn("Cover")},
                            hide_index=True,
                            use_container_width=True
                        )
                else:
                    st.error("Nessun dato.")
                    battle_data[kw] = {"score": 0, "df": None}

    # PROCLAMAZIONE VINCITORE & PIANO EDITORIALE
    if battle_data:
        winner_kw = max(battle_data, key=lambda k: battle_data[k]['score'])
        winner_score = battle_data[winner_kw]['score']
        
        st.markdown(f'<div class="winner-box">🏆 VINCITORE: {winner_kw.upper()}</div>', unsafe_allow_html=True)
        
        if winner_score >= 60:
            with st.spinner("Generazione Master Plan..."):
                plan = SurgicalAI.genera_master_plan(p_type, p_target, p_pain, p_dream, winner_kw)
                formatted_plan = (plan
                    .replace("TITOLO:", " <span class='title-option'>")
                    .replace("ANGOLO DI MARKETING:", "</span> <span class='marketing-angle'>")
                    .replace("TRAMA DETTAGLIATA:", "</span> <div class='plot-detailed'>")
                    .replace("1.", "<br><b>1.</b>").replace("2.", "<br><b>2.</b>")
                    .replace("3.", "<br><b>3.</b>").replace("4.", "<br><b>4.</b>")
                    .replace("5.", "<br><b>5.</b>")
                )
                st.markdown(f'<div class="editorial-container">{formatted_plan}</div> </div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ Score insufficiente per sbloccare il Piano Editoriale automatico.")
