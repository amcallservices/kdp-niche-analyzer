import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM: TESTO NERO & CONTRASTO MASSIMO
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 8.6", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        /* RIMOZIONE ELEMENTI STREAMLIT */
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR FISSA */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; border-right: 1px solid #30363d; min-width: 480px !important;
        }

        /* FORZATURA TESTO NERO SU METRICHE (LABEL E VALORI) */
        [data-testid="stMetricLabel"] p { color: #000000 !important; font-weight: bold !important; font-size: 1.1rem !important; }
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 900 !important; }
        .stMetric { background-color: #ffffff !important; border: 2px solid #dee2e6 !important; padding: 15px !important; border-radius: 10px !important; }

        /* BOX SPIEGAZIONE E CARDS */
        .explanation-box {
            background-color: #f1f3f5; border: 2px solid #ced4da; padding: 20px; 
            border-radius: 10px; color: #000000 !important; margin: 20px 0;
        }
        .ebook-suggestion-card {
            background-color: #ffffff !important; border: 3px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }
        .ebook-title { color: #856404 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 10px; }
        .ebook-plot { color: #000000 !important; line-height: 1.6 !important; font-size: 1.1rem !important; }
        
        /* TESTO GENERALE */
        .stMarkdown p, .stMarkdown li, h1, h2, h3 { color: #000000 !important; }
        
        /* TABELLA RISULTATI */
        .stDataFrame { border: 1px solid #dee2e6; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. API & STATE
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ OpenAI Key mancante.")
    API_READY = False

if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'kw_active' not in st.session_state: st.session_state.kw_active = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING PROFONDO (BSR & SELF-PUB FOCUS)
# ==============================================================================
def run_deep_detection_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    results = []
    seen_titles = set()
    p_bar = st.progress(0)
    
    for page in range(1, 10): 
        if len(results) >= 40: break
        url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
        
        try:
            resp = requests.get(api_url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                title = item.h2.text.strip() if item.h2 else "N/A"
                if title in seen_titles or title == "N/A": continue
                
                # Estrazione TESTUALE profonda
                raw_text = item.get_text(separator=' ').lower()
                
                # 1. BSR DETECTION (Regex avanzata per HTML statico)
                bsr = 0
                patterns = [r'n\.\s*([0-9.,]+)\s*in', r'rank\s*#?\s*([0-9.,]+)', r'posiziona\s*([0-9.,]+)']
                for p in patterns:
                    m = re.search(p, raw_text)
                    if m: 
                        bsr = int(m.group(1).replace('.', '').replace(',', ''))
                        break

                # 2. SELF-PUB DETECTION
                is_self = "No"
                if any(x in raw_text for x in ['independently', 'kdp', 'createspace', 'indipendente', 'self-pub']):
                    is_self = "Sì (Self-Pub)"

                # 3. PREZZO
                price = 0.0
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                if p_w and p_f: price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}")
                
                if price > 0:
                    seen_titles.add(title)
                    results.append({
                        "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                        "Titolo": title, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", "Autore/Tipo": is_self
                    })
                if len(results) >= 40: break
            p_bar.progress(len(results) / 40 if len(results) <= 40 else 1.0)
        except: continue
    
    p_bar.empty()
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR FISSA
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 8.6")
    if st.button("🔄 RESET"):
        for k in ['results_df', 'ebook_ideas', 'kw_active', 'score']: st.session_state[k] = None
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere", ["Saggio Scientifico", "Manuale Tecnico", "Business", "Romanzo Rosa", "Thriller", "Ricettario", "Spirituale"])
    p_desc = st.text_area("Descrizione Progetto", height=100)
    p_target = st.text_input("Target Lettori")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary") and API_READY:
        prompt = f"Genera UNA keyword per {p_type}. Info: {p_desc}. Target: {p_target}. Rispondi: KEYWORD: [testo] | LOGICA: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()

    if st.session_state.kw_active:
        final_q = st.text_input("Keyword finale:", value=st.session_state.kw_active)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        run_btn = st.button("🚀 ANALIZZA 40 LIBRI", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: RISULTATI E SPIEGAZIONI
# ==============================================================================
if 'run_btn' in locals() and run_btn and API_READY:
    with st.spinner("Analisi profonda in corso..."):
        df = run_deep_detection_scan(mkt, final_q)
        if not df.empty:
            st.session_state.results_df = df
            avg_p = df['Prezzo'].mean()
            self_count = len(df[df['Autore/Tipo'].str.contains("Sì")])
            self_r = (self_count / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13.5 else 0) + (30 if self_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_eb = f"Analisi POSITIVA per '{final_q}'. Genera 3 titoli e 3 trame. FORMATO OBBLIGATORIO: [PROPOSTA_START] TITOLO: [testo] | TRAMA: [testo] [PROPOSTA_END]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_eb}]).choices[0].message.content
            else: st.session_state.ebook_ideas = "NEGATIVE"

if st.session_state.results_df is not None:
    st.header(f"📊 Risultati per: {final_q.upper()}")
    
    # SPIEGAZIONE TERMINI (TESTO NERO)
    st.markdown("""
    <div class="explanation-box">
        <b>📘 Manuale di Lettura Dati:</b><br>
        • <b>BSR (Best Sellers Rank):</b> Indica la popolarità. Più il numero è basso (es. 500), più il libro vende. Se vedi "N/D" Amazon sta limitando i dati della pagina.<br>
        • <b>Indie Ratio:</b> Percentuale di Self-Publisher. Se è alta, la nicchia è scalabile per te.<br>
        • <b>Opportunity Score:</b> Valutazione finale. Sopra 60 è un semaforo verde per pubblicare.
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    # METRICHE (FORZATE NERE)
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    c2.metric("Indie Ratio", f"{int((len(st.session_state.results_df[st.session_state.results_df['Autore/Tipo'].str.contains('Sì')]) / len(st.session_state.results_df)) * 100)}%")
    c3.metric("Score Nicchia", f"{st.session_state.score}/100")

    # VERDETTO E TITOLI
    if st.session_state.score >= 60:
        st.success("✅ ANALISI POSITIVA: Ecco le tue opportunità editoriali")
        proposte = st.session_state.ebook_ideas.split("[PROPOSTA_START]")
        for prop in proposte[1:]:
            clean_prop = prop.split("[PROPOSTA_END]")[0]
            t = clean_prop.split("| TRAMA:")[0].replace("TITOLO:", "").strip()
            p = clean_prop.split("| TRAMA:")[1].strip()
            st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {t}</span><p class="ebook-plot">{p}</p></div>', unsafe_allow_html=True)
    else:
        st.error("❌ ANALISI NEGATIVA: Nicchia troppo competitiva o poco profittevole.")
        st.info("💡 Prova a rigenerare la Keyword cambiando la descrizione o il target nella sidebar.")
