import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (SIDEBAR FISSA & TESTO NERO)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 8.4", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        /* UI GHOST: RIMOZIONE TOTALE HEADER E MENU */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; 
            border-right: 1px solid #30363d;
            min-width: 450px !important;
        }

        /* METRICHE */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }

        /* BOX SPIEGAZIONE - TESTO NERO */
        .explanation-box {
            background-color: #f8f9fa; border: 2px solid #dee2e6; padding: 20px; 
            border-radius: 10px; color: #000000 !important; margin: 20px 0; font-size: 1rem;
        }
        .explanation-box b { color: #000000 !important; }

        /* EBOOK CARDS - SFONDO BIANCO E TESTO NERO */
        .ebook-suggestion-card {
            background-color: #ffffff !important; border: 3px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .ebook-title { color: #b8860b !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 8px; }
        .ebook-plot { color: #000000 !important; line-height: 1.7 !important; font-size: 1.1rem !important; font-weight: 500; }
        
        /* BANNER NEGATIVO */
        .negative-verdict {
            background-color: #fff5f5 !important; color: #c92a2a !important; padding: 30px; border-radius: 15px;
            text-align: center; font-weight: 900; font-size: 1.8rem; margin: 30px 0; border: 3px solid #ffc9c9;
        }

        /* FORZATURA TESTO GENERALE NERO NELLE SEZIONI RISULTATI */
        .stMarkdown p, .stMarkdown li { color: #000000 !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE API & PERSISTENZA
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"
SCRAPER_API_KEY = st.secrets.get("SCRAPER_API_KEY", "")

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ OpenAI API Key non trovata.")
    API_READY = False

if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'kw_active' not in st.session_state: st.session_state.kw_active = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING TURBO (ANT + SCRAPERAPI FAILOVER)
# ==============================================================================
def fetch_page(url, provider="ant"):
    if provider == "ant":
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
    else:
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={urllib.parse.quote(url)}"
    try:
        response = requests.get(api_url, timeout=25)
        return response.text if response.status_code == 200 else None
    except: return None

def run_expert_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    unique_results = []
    seen_titles = set()
    p_bar = st.progress(0)
    
    for page in range(1, 8): 
        if len(unique_results) >= 40: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        html = fetch_page(target_url, "ant")
        if not html or "captcha" in html.lower(): html = fetch_page(target_url, "scraperapi")
        if not html: continue
        
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        for item in items:
            title = item.h2.text.strip() if item.h2 else "N/A"
            if title in seen_titles or title == "N/A": continue
            full_text = item.get_text(separator=' ').lower()
            if not any(x in full_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
            
            price = 0.0
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            if p_w and p_f: price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}")
            
            if price > 0:
                seen_titles.add(title)
                bsr = 0
                bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', full_text)
                if bsr_match: bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
                unique_results.append({
                    "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                    "Titolo": title, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", 
                    "Self": "Sì" if any(x in full_text for x in ['independently', 'kdp', 'createspace']) else "No"
                })
            if len(unique_results) >= 40: break
        p_bar.progress(len(unique_results) / 40 if len(unique_results) <= 40 else 1.0)
    p_bar.empty()
    return pd.DataFrame(unique_results)

# ==============================================================================
# 4. SIDEBAR FISSA
# ==============================================================================
with st.sidebar:
    st.title("🛡️ EXPERT LAB 8.4")
    if st.button("🔄 RESET"):
        for key in ['results_df', 'ebook_ideas', 'kw_active', 'score']: st.session_state[key] = None if key != 'score' else 0
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere", ["Saggio", "Manuale", "Business", "Romanzo", "Ricettario", "Psicologico"])
    p_desc = st.text_area("Cosa vuoi scrivere?", height=100)
    p_target = st.text_input("Target", placeholder="Chi leggerà?")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary") and API_READY:
        prompt = f"Keyword per: {p_type}. Descrizione: {p_desc}. Target: {p_target}. Rispondi: KEYWORD: [testo] | LOGICA: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()

    if st.session_state.kw_active:
        final_q = st.text_input("Keyword finale:", value=st.session_state.kw_active)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        run_btn = st.button("🚀 ANALIZZA 40 LIBRI", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD (TESTO IN NERO)
# ==============================================================================
if 'run_btn' in locals() and run_btn and API_READY:
    with st.spinner("Analisi in corso..."):
        df = run_expert_scan(mkt, final_q)
        if not df.empty:
            st.session_state.results_df = df
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13 else 0) + (30 if self_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_ebook = f"Analisi OK per '{final_q}'. Suggerisci 3 titoli e 3 trame. Target: {p_target}. Formato: TITOLO: [testo] | TRAMA: [testo]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_ebook}]).choices[0].message.content
            else:
                st.session_state.ebook_ideas = "NEGATIVE"

if st.session_state.results_df is not None:
    st.header(f"📊 Risultati Analisi: {final_q.upper()}")
    
    # SPIEGAZIONE (TESTO NERO)
    st.markdown("""
    <div class="explanation-box">
        <b>💡 Guida all'Analisi Strategica:</b><br>
        • <b>BSR (Best Sellers Rank):</b> Indica quanto velocemente vende un libro. Più è basso, meglio è.<br>
        • <b>Indie Ratio:</b> Percentuale di autori Self-Publisher. Sopra il 40% indica spazio per te.<br>
        • <b>Opportunity Score:</b> Voto da 0 a 100. Sopra 60 è una miniera d'oro.
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns(2)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    c2.metric("Indie Ratio", f"{int((len(st.session_state.results_df[st.session_state.results_df['Self'] == 'Sì']) / len(st.session_state.results_df)) * 100)}%")

    if st.session_state.score >= 60:
        st.success(f"✅ VERDETTO POSITIVO ({st.session_state.score}/100)")
        st.header("🎯 Proposte eBook (Black Edition)")
        ebooks = st.session_state.ebook_ideas.split("TITOLO:")
        for eb in ebooks[1:]:
            parts = eb.split("| TRAMA:")
            if len(parts) > 1:
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {parts[0].strip()}</span><p class="ebook-plot">{parts[1].strip()}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="negative-verdict">❌ ANALISI NEGATIVA ({st.session_state.score}/100)</div>', unsafe_allow_html=True)
        st.warning("⚠️ Nicchia sconsigliata: prova a rigenerare la keyword.")
