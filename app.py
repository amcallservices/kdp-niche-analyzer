import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 1. DESIGN SYSTEM: CONTRASTO BIANCO/NERO & SIDEBAR FISSA
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 10.4", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; border-right: 1px solid #30363d; min-width: 480px !important;
        }
        
        section[data-testid="stSidebar"] * { color: #ffffff !important; }
        section[data-testid="stSidebar"] h1 { font-size: 1.8rem !important; color: white !important; }

        .white-header {
            color: #ffffff !important; font-size: 2.2rem !important; font-weight: 800 !important;
            margin: 25px 0px !important; display: block;
        }

        [data-testid="stMetricLabel"] p { color: #000000 !important; font-weight: bold !important; font-size: 1.1rem !important; }
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 900 !important; }
        .stMetric { background-color: #ffffff !important; border: 2px solid #dee2e6 !important; padding: 15px !important; border-radius: 10px !important; }

        .explanation-box {
            background-color: #f8f9fa; border: 2px solid #ced4da; padding: 20px; 
            border-radius: 10px; color: #000000 !important; margin: 20px 0; font-size: 1rem;
        }
        .ebook-suggestion-card {
            background-color: #ffffff !important; border: 3px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
        }
        .ebook-title { color: #856404 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; }
        .ebook-plot { color: #000000 !important; line-height: 1.6 !important; font-size: 1.1rem !important; font-weight: 500; }
        
        /* FORZA NERO SUI CONTENUTI */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown div { color: #000000 !important; }
        .white-header, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] label { color: white !important; }
        
        .kw-active-box {
            background-color: #238636; color: white !important; padding: 10px; border-radius: 5px; margin-top: 10px; font-weight: bold; text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. API & PERSISTENZA (BUG FIX: INITIALIZATION)
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ Configurazione OpenAI mancante.")
    API_READY = False

# Inizializziamo tutti i campi nel session_state per evitare che il bottone non risponda
states = {
    'results_df': None, 'ebook_ideas': "", 'score': 0, 
    'final_keyword': "", 'kw_suggested': None, 'trigger_analysis': False
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

# ==============================================================================
# 3. MOTORE PARALLELO TURBO (60+ LIBRI)
# ==============================================================================
def fetch_page(url):
    api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
    try:
        resp = requests.get(api_url, timeout=20)
        return resp.text if resp.status_code == 200 else None
    except: return None

def run_deep_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    urls = [f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={i}" for i in range(1, 15)]
    results, seen_titles = [], set()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        pages_content = list(executor.map(fetch_page, urls))
    
    for html in pages_content:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        for item in items:
            if len(results) >= 60: break
            title = item.h2.text.strip() if item.h2 else "N/A"
            if title in seen_titles or title == "N/A": continue
            raw_text = item.get_text(separator=' ').lower()
            if not any(x in raw_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
            
            # BSR detection
            bsr = 0
            for p in [r'n\.\s*([0-9.,]+)\s*in', r'rank\s*#?\s*([0-9.,]+)', r'#([0-9.,]+)\s*in']:
                m = re.search(p, raw_text)
                if m: bsr = int(m.group(1).replace('.', '').replace(',', '')); break
            
            p_w, p_f = item.find('span', 'a-price-whole'), item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            
            if price > 0:
                seen_titles.add(title)
                results.append({
                    "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                    "Titolo": title, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", 
                    "Autore/Tipo": "Sì (Self-Pub)" if any(x in raw_text for x in ['independently', 'kdp', 'createspace']) else "Tradizionale"
                })
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR FISSA (LOGICA DEI PULSANTI RIPARATA)
# ==============================================================================
with st.sidebar:
    st.markdown("# 🛡️ STRATEGY LAB 10.4")
    if st.button("🔄 RESET TOTALE"):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    
    if st.session_state.final_keyword:
        st.markdown(f'<div class="kw-active-box">🎯 TARGET: {st.session_state.final_keyword.upper()}</div>', unsafe_allow_html=True)
    
    p_type = st.selectbox("Genere / Formato", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"])
    p_niche = st.text_input("Nicchia Specifica")
    p_target = st.text_input("Identikit Lettore")
    p_angle = st.text_area("Angolo di Attacco", height=80)
    
    # PULSANTE 1: GENERAZIONE
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        if API_READY:
            prompt = f"Sei un SEO KDP. Genera UNA keyword LONG-TAIL per un {p_type}. Nicchia: {p_niche}. Target: {p_target}. Rispondi: KEYWORD: [testo]"
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
            st.session_state.kw_suggested = res.split("KEYWORD:")[1].strip()
            st.rerun()

    if st.session_state.kw_suggested:
        kw_input = st.text_input("Keyword finale:", value=st.session_state.kw_suggested)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        
        # PULSANTE 2: ANALISI (Usa trigger per stabilità)
        if st.button("🚀 LANCIA DEEP SCAN (60 LIBRI)", use_container_width=True):
            st.session_state.trigger_analysis = True
            st.session_state.active_kw = kw_input
            st.session_state.active_mkt = mkt
            st.rerun()

# ==============================================================================
# 5. ESECUZIONE ANALISI (Garantisce che il codice parta e resti)
# ==============================================================================
if st.session_state.trigger_analysis:
    with st.spinner("⚡ Analisi parallela in corso..."):
        df = run_deep_scan(st.session_state.active_mkt, st.session_state.active_kw)
        if not df.empty:
            st.session_state.results_df = df
            st.session_state.final_keyword = st.session_state.active_kw
            avg_p = df['Prezzo'].mean()
            indie_r = (len(df[df['Autore/Tipo'].str.contains("Sì")]) / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13.5 else 0) + (30 if indie_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_eb = f"Editor KDP. Keyword: '{st.session_state.active_kw}', Genere: '{p_type}'. Genera 3 titoli e 3 trame. Formato: [PROPOSTA_START] TITOLO: [testo] | TRAMA: [testo] [PROPOSTA_END]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_eb}]).choices[0].message.content
            else: st.session_state.ebook_ideas = "NEGATIVE"
        
        st.session_state.trigger_analysis = False # Ferma il loop ma i dati restano nel session_state

# ==============================================================================
# 6. DASHBOARD: VISUALIZZAZIONE PERSISTENTE
# ==============================================================================
if st.session_state.results_df is not None:
    st.markdown(f"<div class='white-header'>📊 Report Mercato: {st.session_state.final_keyword.upper()}</div>", unsafe_allow_html=True)
    
    st.markdown("""<div class="explanation-box"><b>📘 Manuale d'Analisi (Testo Nero):</b><br>• <b>BSR:</b> Classifica vendite. • <b>Indie Ratio:</b> Quota Self-Publisher. • <b>Score:</b> Semaforo verde > 60.</div>""", unsafe_allow_html=True)
    
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    indie_n = len(st.session_state.results_df[st.session_state.results_df['Autore/Tipo'].str.contains('Sì')])
    c2.metric("Indie Ratio", f"{int((indie_n / len(st.session_state.results_df)) * 100)}%")
    c3.metric("Score", f"{st.session_state.score}/100")

    if st.session_state.score >= 60:
        st.success(f"✅ ANALISI POSITIVA: Strategia per '{p_type}'")
        proposte = st.session_state.ebook_ideas.split("[PROPOSTA_START]")
        for prop in proposte[1:]:
            if "[PROPOSTA_END]" in prop and "| TRAMA:" in prop:
                clean_prop = prop.split("[PROPOSTA_END]")[0]
                parts = clean_prop.split("| TRAMA:")
                t, p = parts[0].replace("TITOLO:", "").strip(), parts[1].strip()
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {t}</span><p class="ebook-plot">{p}</p></div>', unsafe_allow_html=True)
    else:
        st.error("❌ ANALISI NEGATIVA (Scarsa opportunità)")
