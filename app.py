import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM: CONTRASTO DEFINITIVO (BIANCO/NERO)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 9.0", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        /* RIMOZIONE ELEMENTI STREAMLIT */
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR FISSA E TITOLI BIANCHI */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; border-right: 1px solid #30363d; min-width: 480px !important;
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { 
            color: #ffffff !important; 
        }

        /* HEADER RISULTATI BIANCO */
        .header-white {
            color: #ffffff !important; font-size: 2rem !important; font-weight: 800 !important;
            margin: 20px 0px !important; display: block;
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
        
        /* FORZA NERO SU TUTTO IL CORPO CENTRALE */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown div { color: #000000 !important; }
        
        /* ECCEZIONI PER IL BIANCO */
        .header-white, section[data-testid="stSidebar"] * { color: white !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE API & STATO PERSISTENTE
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ Chiave OpenAI mancante nei Secret.")
    API_READY = False

# Inizializzazione della memoria di sessione (Fondamentale perché non sparisca nulla)
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'final_keyword' not in st.session_state: st.session_state.final_keyword = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING PROFONDO (JS-OFF PER VELOCITÀ)
# ==============================================================================
def run_deep_scan(mkt, keyword):
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
                
                raw_text = item.get_text(separator=' ').lower()
                if not any(x in raw_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue

                # BSR DETECTION
                bsr = 0
                patterns = [r'n\.\s*([0-9.,]+)\s*in', r'rank\s*#?\s*([0-9.,]+)', r'#([0-9.,]+)\s*in']
                for p in patterns:
                    m = re.search(p, raw_text)
                    if m: 
                        bsr = int(m.group(1).replace('.', '').replace(',', ''))
                        break

                # SELF-PUB DETECTION
                editore_tipo = "Editore Tradizionale"
                if any(x in raw_text for x in ['independently', 'kdp', 'createspace', 'indipendente']):
                    editore_tipo = "Sì (Self-Pub)"

                # PREZZO
                price = 0.0
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                if p_w and p_f: price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}")
                
                if price > 0:
                    seen_titles.add(title)
                    results.append({
                        "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                        "Titolo": title, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", "Autore/Tipo": editore_tipo
                    })
                if len(results) >= 40: break
            p_bar.progress(len(results) / 40 if len(results) <= 40 else 1.0)
        except: continue
    
    p_bar.empty()
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR FISSA (TITOLI BIANCHI)
# ==============================================================================
with st.sidebar:
    st.markdown("# 🛡️ STRATEGY LAB 9.0")
    if st.button("🔄 RESET"):
        for k in ['results_df', 'ebook_ideas', 'score', 'final_keyword']: st.session_state[k] = None
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere / Formato", [
        "Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", 
        "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", 
        "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", 
        "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"
    ])
    p_desc = st.text_area("Descrizione Progetto")
    p_target = st.text_input("Target Lettori")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        prompt = f"Genera UNA keyword per {p_type}. Descrizione: {p_desc}. Target: {p_target}. Rispondi: KEYWORD: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_suggested = res.split("KEYWORD:")[1].strip()

    if 'kw_suggested' in st.session_state:
        kw_input = st.text_input("Keyword finale:", value=st.session_state.kw_suggested)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        
        if st.button("🚀 LANCIA ANALISI Sniper", use_container_width=True):
            with st.spinner("Analisi in corso..."):
                df = run_deep_scan(mkt, kw_input)
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
                else:
                    st.error("Amazon ha bloccato la richiesta o non ci sono risultati per questa keyword.")

# ==============================================================================
# 5. DASHBOARD: VISUALIZZAZIONE PERSISTENTE (FUORI DAL PULSANTE)
# ==============================================================================
if st.session_state.results_df is not None:
    # Header Bianco
    st.markdown(f"<span class='header-white'>📊 Risultati per: {st.session_state.final_keyword.upper()}</span>", unsafe_allow_html=True)
    
    # Glossario Nero
    st.markdown("""
    <div class="explanation-box">
        <b>📘 Glossario Tecnico (Testo Nero):</b><br>
        • <b>BSR (Best Sellers Rank):</b> La classifica vendite. Più è basso, meglio è.<br>
        • <b>Indie Ratio:</b> Quota di Self-Publisher nei primi 40 libri. Se è alta, la nicchia è libera.<br>
        • <b>Opportunity Score:</b> Valutazione finale. Sopra 60 è un'opportunità reale.
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    # Metriche Nere su Bianco
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    self_count = len(st.session_state.results_df[st.session_state.results_df['Autore/Tipo'].str.contains('Sì')])
    c2.metric("Indie Ratio", f"{int((self_count / len(st.session_state.results_df)) * 100)}%")
    c3.metric("Score", f"{st.session_state.score}/100")

    if st.session_state.score >= 60:
        st.success("✅ ANALISI POSITIVA")
        proposte = st.session_state.ebook_ideas.split("[PROPOSTA_START]")
        for prop in proposte[1:]:
            if "[PROPOSTA_END]" in prop:
                clean_prop = prop.split("[PROPOSTA_END]")[0]
                t = clean_prop.split("| TRAMA:")[0].replace("TITOLO:", "").strip()
                p = clean_prop.split("| TRAMA:")[1].strip()
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {t}</span><p class="ebook-plot">{p}</p></div>', unsafe_allow_html=True)
    else:
        st.error("❌ ANALISI NEGATIVA (Score insufficiente)")
