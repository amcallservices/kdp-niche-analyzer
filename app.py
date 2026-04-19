import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 1. DESIGN SYSTEM: CONTRASTO DEFINITIVO (BIANCO/NERO)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 9.3", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
        /* UI GHOST & SIDEBAR */
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; border-right: 1px solid #30363d; min-width: 480px !important;
        }
        
        /* TESTO BIANCO PER TITOLI PRINCIPALI */
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] label, 
        section[data-testid="stSidebar"] p,
        .white-title { 
            color: #ffffff !important; 
        }

        .white-title {
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            margin: 25px 0px !important;
            display: block;
        }

        /* METRICHE: SFONDO BIANCO E TESTO NERO */
        [data-testid="stMetricLabel"] p { color: #000000 !important; font-weight: bold !important; }
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 900 !important; }
        .stMetric { background-color: #ffffff !important; border: 2px solid #dee2e6 !important; padding: 15px !important; border-radius: 10px !important; }

        /* CONTENUTI IN NERO ASSOLUTO */
        .explanation-box {
            background-color: #f8f9fa; border: 2px solid #ced4da; padding: 20px; 
            border-radius: 10px; color: #000000 !important; margin: 20px 0;
        }
        .ebook-suggestion-card {
            background-color: #ffffff !important; border: 3px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
        }
        .ebook-title { color: #856404 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; }
        .ebook-plot { color: #000000 !important; line-height: 1.6 !important; font-size: 1.1rem !important; font-weight: 500; }
        
        /* FORZA NERO SU TUTTO IL CORPO (CON ECCEZIONE PER CLASSE WHITE) */
        .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #000000 !important; }
        .white-title, section[data-testid="stSidebar"] * { color: white !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. API & STATO PERSISTENTE
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ Chiave OpenAI non trovata.")
    API_READY = False

if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'final_keyword' not in st.session_state: st.session_state.final_keyword = ""

# ==============================================================================
# 3. MOTORE PARALLELO TURBO (JS-OFF)
# ==============================================================================
def fetch_page(url):
    api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
    try:
        resp = requests.get(api_url, timeout=20)
        return resp.text if resp.status_code == 200 else None
    except: return None

def run_fast_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    urls = [f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={i}" for i in range(1, 10)]
    
    results = []
    seen_titles = set()
    
    with st.spinner("⚡ Scansione Parallela (10-15s)..."):
        with ThreadPoolExecutor(max_workers=8) as executor:
            pages_content = list(executor.map(fetch_page, urls))
    
    for html in pages_content:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        for item in items:
            if len(results) >= 40: break
            title = item.h2.text.strip() if item.h2 else "N/A"
            if title in seen_titles or title == "N/A": continue
            
            raw_text = item.get_text(separator=' ').lower()
            if not any(x in raw_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue

            # BSR & Prezzo & Self-Pub
            bsr = 0
            for p in [r'n\.\s*([0-9.,]+)\s*in', r'rank\s*#?\s*([0-9.,]+)', r'#([0-9.,]+)\s*in']:
                m = re.search(p, raw_text)
                if m: 
                    bsr = int(m.group(1).replace('.', '').replace(',', ''))
                    break
            
            price = 0.0
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            if p_w and p_f: price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}")
            
            if price > 0:
                seen_titles.add(title)
                results.append({
                    "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                    "Titolo": title, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", 
                    "Autore/Tipo": "Sì (Self-Pub)" if any(x in raw_text for x in ['independently', 'kdp', 'createspace']) else "Tradizionale"
                })
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR FISSA (BIANCA)
# ==============================================================================
with st.sidebar:
    st.markdown("# 🛡️ STRATEGY LAB 9.3")
    if st.button("🔄 RESET"):
        for k in ['results_df', 'ebook_ideas', 'score', 'final_keyword', 'kw_suggested']: 
            if k in st.session_state: st.session_state[k] = None
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere / Formato", [
        "Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", 
        "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", 
        "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", 
        "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"
    ])
    p_desc = st.text_area("Descrizione Progetto", height=100)
    p_target = st.text_input("Target Lettori")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        prompt = f"Genera UNA keyword per {p_type}. Info: {p_desc}. Target: {p_target}. Rispondi: KEYWORD: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_suggested = res.split("KEYWORD:")[1].strip()

    if 'kw_suggested' in st.session_state:
        kw_input = st.text_input("Keyword finale:", value=st.session_state.kw_suggested)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        
        if st.button("🚀 LANCIA ANALISI PARALLELA", use_container_width=True):
            df = run_fast_scan(mkt, kw_input)
            if not df.empty:
                st.session_state.results_df = df
                st.session_state.final_keyword = kw_input
                avg_p = df['Prezzo'].mean()
                self_r = (len(df[df['Autore/Tipo'].str.contains("Sì")]) / len(df)) * 100
                st.session_state.score = 40 + (30 if avg_p > 13.5 else 0) + (30 if self_r > 40 else 0)
                
                if st.session_state.score >= 60:
                    p_eb = f"Analisi OK per '{kw_input}'. Suggerisci 3 titoli e 3 trame. FORMATO: [PROPOSTA_START] TITOLO: [testo] | TRAMA: [testo] [PROPOSTA_END]"
                    st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_eb}]).choices[0].message.content
                else: st.session_state.ebook_ideas = "NEGATIVE"

# ==============================================================================
# 5. DASHBOARD: RISULTATI (HEADER BIANCO FISSO)
# ==============================================================================
if st.session_state.results_df is not None:
    # HEADER BIANCO FORZATO
    st.markdown(f"<div class='white-title'>📊 Risultati per: {st.session_state.final_keyword.upper()}</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="explanation-box">
        <b>📘 Glossario Tecnico (Testo Nero):</b><br>
        • <b>BSR (Best Sellers Rank):</b> La classifica vendite. Più è basso, meglio è.<br>
        • <b>Indie Ratio:</b> Quota di Self-Publisher nei primi 40 libri unici.<br>
        • <b>Opportunity Score:</b> Valutazione complessiva (Successo se > 60).
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    # Metriche
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    indie_count = len(st.session_state.results_df[st.session_state.results_df['Autore/Tipo'].str.contains('Sì')])
    c2.metric("Indie Ratio", f"{int((indie_count / len(st.session_state.results_df)) * 100)}%")
    c3.metric("Score", f"{st.session_state.score}/100")

    # Verdetto e proposte (Safe split per evitare IndexError)
    if st.session_state.score >= 60:
        st.success("✅ ANALISI POSITIVA")
        proposte = st.session_state.ebook_ideas.split("[PROPOSTA_START]")
        for prop in proposte[1:]:
            if "[PROPOSTA_END]" in prop and "| TRAMA:" in prop:
                clean_prop = prop.split("[PROPOSTA_END]")[0]
                parts = clean_prop.split("| TRAMA:")
                t = parts[0].replace("TITOLO:", "").strip()
                p = parts[1].strip()
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {t}</span><p class="ebook-plot">{p}</p></div>', unsafe_allow_html=True)
    else:
        st.error("❌ ANALISI NEGATIVA (Nicchia sconsigliata)")
