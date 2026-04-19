import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (SIDEBAR FISSA & UI GHOST)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 8.0", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        /* UI GHOST: RIMOZIONE HEADER, FOOTER E MENU STREAMLIT */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR FISSA E DARK */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; 
            border-right: 1px solid #30363d;
            min-width: 450px !important;
        }

        /* METRICHE */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }

        /* BANNER VERDETTO NEGATIVO */
        .negative-verdict {
            background-color: #3d0a0a !important; color: #ff6b6b !important; padding: 30px; border-radius: 15px;
            text-align: center; font-weight: 900; font-size: 1.8rem; margin: 30px 0;
            border: 2px solid #ff6b6b; box-shadow: 0 0 20px rgba(255, 107, 107, 0.2);
        }

        /* EBOOK CARDS POSITIVE */
        .ebook-suggestion-card {
            background-color: #0b0e14 !important; border: 2px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
        }
        .ebook-title { color: #ffd700 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 8px; }
        .ebook-plot { color: #e6edf3 !important; line-height: 1.7 !important; font-size: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE API & PERSISTENZA
# ==============================================================================
# Chiavi API integrate come richiesto
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"
SCRAPER_API_KEY = st.secrets.get("SCRAPER_API_KEY", "INSERISCI_QUI_SE_NON_NEI_SECRETS") # Fallback se non è nei secrets

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ OpenAI API Key non trovata nei Secret di Streamlit.")
    API_READY = False

# Inizializzazione Session State per persistenza totale
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'kw_active' not in st.session_state: st.session_state.kw_active = ""
if 'kw_logic' not in st.session_state: st.session_state.kw_logic = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING CON FAILOVER (ANT + SCRAPERAPI)
# ==============================================================================
def fetch_amazon_page(url, provider="ant"):
    """Prova a scaricare la pagina usando il provider specificato."""
    if provider == "ant":
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={ANT_API_KEY}&browser=true&proxy_type=residential"
    else: # ScraperAPI
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={urllib.parse.quote(url)}&render=true"
    
    try:
        response = requests.get(api_url, timeout=45)
        if response.status_code == 200:
            return response.text
    except:
        return None
    return None

def run_omni_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    unique_results = []
    seen_titles = set()
    p_bar = st.progress(0)
    
    for page in range(1, 15): 
        if len(unique_results) >= 100: break
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        
        # LOGICA FAILOVER: Prova Ant, se fallisce prova ScraperAPI
        html = fetch_amazon_page(target_url, provider="ant")
        if not html or "captcha" in html.lower():
            html = fetch_amazon_page(target_url, provider="scraperapi")
        
        if not html: continue
        
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for item in items:
            title_elem = item.h2.text.strip() if item.h2 else "N/A"
            if title_elem in seen_titles or title_elem == "N/A": continue
            
            full_text = item.get_text(separator=' ').lower()
            if not any(x in full_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
            
            # --- DATI VERITIERI ---
            # BSR
            bsr = 0
            bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', full_text)
            if bsr_match: bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
            
            # Prezzo
            price = 0.0
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            if p_whole and p_frac:
                price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}")
            
            if price > 0:
                seen_titles.add(title_elem)
                unique_results.append({
                    "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                    "Titolo": title_elem, 
                    "Prezzo": price, 
                    "BSR": bsr if bsr > 0 else "N/D", 
                    "Self": "Sì" if any(x in full_text for x in ['independently published', 'kdp', 'createspace']) else "No"
                })
            if len(unique_results) >= 100: break
        p_bar.progress(len(unique_results) / 100)
    
    p_bar.empty()
    return pd.DataFrame(unique_results)

# ==============================================================================
# 4. SIDEBAR FISSA (FULL GENRES & AI CMD)
# ==============================================================================
with st.sidebar:
    st.title("🛡️ OMNI-SHIELD v8.0")
    if st.button("🔄 RESET TOTALE"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

    st.markdown("---")
    p_type = st.selectbox("Genere / Formato", [
        "Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", 
        "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", 
        "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", 
        "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"
    ])
    p_target = st.text_input("Target", placeholder="es. Ingegneri")
    p_pain = st.text_input("Problema", placeholder="es. gestione tempo")
    p_dream = st.text_input("Sogno", placeholder="es. produttività")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        p = f"Genera UNA keyword Long-Tail per '{p_type}' rivolto a '{p_target}'. Dolore: {p_pain}. Rispondi: KEYWORD: [testo] | LOGICA: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()
        st.session_state.kw_logic = res.split("LOGICA:")[1].strip()

    if st.session_state.kw_active:
        st.info(f"**AI Strategy:** {st.session_state.kw_logic}")
        final_q = st.text_input("Keyword finale:", value=st.session_state.kw_active)
        mkt = st.selectbox("Mercato", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        run_btn = st.button("🚀 LANCIA ANALISI OMNI-SHIELD", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: VERDETTO & REDAZIONE
# ==============================================================================
if 'run_btn' in locals() and run_btn and API_READY:
    with st.spinner("Analisi massiva con doppio motore di scraping..."):
        df = run_omni_scan(mkt, final_q)
        if not df.empty:
            st.session_state.results_df = df
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13.5 else 0) + (30 if self_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_ebook = f"Genera 3 titoli e 3 trame (100 parole) per eBook su '{final_q}' ({p_type}). Formato: TITOLO: [testo] | TRAMA: [testo]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_ebook}]).choices[0].message.content
            else:
                st.session_state.ebook_ideas = "NEGATIVE"

# VISUALIZZAZIONE RISULTATI PERSISTENTE
if st.session_state.results_df is not None:
    st.header(f"📊 Report: {final_q.upper()} ({p_type})")
    st.dataframe(st.session_state.results_df, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns(2)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    c2.metric("Indie Ratio", f"{int((len(st.session_state.results_df[st.session_state.results_df['Self'] == 'Sì']) / len(st.session_state.results_df)) * 100)}%")

    if st.session_state.score >= 60:
        st.success(f"✅ ANALISI POSITIVA ({st.session_state.score}/100)")
        st.header("🎯 Strategia Editoriale eBook")
        ebooks = st.session_state.ebook_ideas.split("TITOLO:")
        for eb in ebooks[1:]:
            parts = eb.split("| TRAMA:")
            if len(parts) > 1:
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {parts[0].strip()}</span><p class="ebook-plot">{parts[1].strip()}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="negative-verdict">❌ ANALISI NEGATIVA ({st.session_state.score}/100)</div>', unsafe_allow_html=True)
        st.warning("⚠️ Questa nicchia non ha i parametri minimi di profitto.")
        st.info("💡 **Consiglio:** Rigenera la Keyword AI nella sidebar cambiando leggermente il Target o il Problema.")
