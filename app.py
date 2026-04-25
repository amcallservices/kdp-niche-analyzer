import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 1. DESIGN SYSTEM: MODERN SAAS DASHBOARD
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 12.0", page_icon="📊", layout="wide")

st.markdown("""
    <style>
        /* Base Streamlit Overrides */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        /* App Background */
        .stApp {
            background-color: #f3f4f6;
        }

        /* Sidebar: Deep Professional Indigo */
        section[data-testid="stSidebar"] { 
            background-color: #1e1e2f !important; 
            min-width: 400px !important;
            border-right: 1px solid #2d2d44;
            padding-top: 2rem;
        }
        section[data-testid="stSidebar"] * { 
            color: #f8f9fa !important; 
        }
        
        /* Sidebar inputs styling */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #2d2d44 !important;
            border: 1px solid #4b4b63 !important;
            color: white !important;
            border-radius: 6px;
        }
        
        /* Main Area Typography */
        .program-title { 
            color: #111827 !important; 
            font-size: 2.2rem !important; 
            font-weight: 800; 
            text-align: left; 
            margin-bottom: 2rem; 
            padding-bottom: 1rem;
            border-bottom: 2px solid #e5e7eb;
            letter-spacing: -0.025em;
        }
        .white-title { 
            color: #374151 !important; 
            font-size: 1.5rem !important; 
            font-weight: 700; 
            margin-bottom: 1rem; 
        }

        /* Metrics Styling */
        [data-testid="stMetricValue"] { 
            color: #2563eb !important; 
            font-weight: 700 !important; 
            font-size: 2rem !important;
        }
        [data-testid="stMetricLabel"] p {
            color: #6b7280 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 0.85rem;
        }
        .stMetric { 
            background-color: white !important; 
            border: 1px solid #e5e7eb; 
            padding: 20px; 
            border-radius: 12px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        /* Dataframe Styling */
        [data-testid="stDataFrame"] {
            background-color: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #e5e7eb;
        }

        /* Strategy Cards */
        .ebook-card {
            background-color: white; 
            border: 1px solid #e5e7eb; 
            border-left: 4px solid #2563eb; 
            padding: 24px; 
            border-radius: 12px; 
            margin-bottom: 1.5rem; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s ease-in-out;
        }
        .ebook-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .ebook-title { 
            color: #111827 !important; 
            font-weight: 800; 
            font-size: 1.25rem; 
            margin-bottom: 12px; 
        }
        .ebook-plot { 
            color: #4b5563 !important; 
            line-height: 1.7; 
            font-size: 1rem; 
        }

        /* Buttons */
        .stButton button {
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
        }
        button[kind="primary"] {
            background-color: #2563eb !important;
            color: white !important;
            border: none !important;
        }
        button[kind="primary"]:hover {
            background-color: #1d4ed8 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE MEMORIA (PERSISTENZA)
# ==============================================================================
if 'data' not in st.session_state: st.session_state.data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None
if 'kw' not in st.session_state: st.session_state.kw = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'suggested_kws' not in st.session_state: st.session_state.suggested_kws = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING TRIPLE-FALLBACK (ANTI-BLOCCO)
# ==============================================================================
def get_amazon_data(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    ANT_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"
    SCRAPERAPI_KEY = st.secrets.get("SCRAPERAPI_KEY", "")
    WEBSCRAPINGAI_KEY = st.secrets.get("WEBSCRAPINGAI_KEY", "")
    
    def fetch_with_triple_fallback(p):
        amazon_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={p}"
        try:
            ant_api = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(amazon_url)}&x-api-key={ANT_KEY}&browser=true&proxy_type=residential"
            r = requests.get(ant_api, timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        try:
            scraperapi_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={urllib.parse.quote(amazon_url)}&render=true"
            r = requests.get(scraperapi_url, timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        try:
            ws_ai_url = f"https://api.webscraping.ai/html?api_key={WEBSCRAPINGAI_KEY}&url={urllib.parse.quote(amazon_url)}&proxy=residential&js=true"
            r = requests.get(ws_ai_url, timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        pages = list(executor.map(fetch_with_triple_fallback, range(1, 11)))
    
    results, seen = [], set()
    for html in pages:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'}) or soup.select('.s-result-item[data-asin]')
        for item in items:
            title_el = item.h2 or item.select_one('.a-size-medium') or item.select_one('.a-size-base-plus')
            title = title_el.text.strip() if title_el else ""
            if not title or title in seen: continue
            text = item.get_text(separator=' ').lower()
            bsr_match = re.search(r'(?:n\.|#|rank)\s*([0-9.,]+)', text)
            bsr = bsr_match.group(1).replace('.', '').replace(',', '') if bsr_match else "N/D"
            is_self = "Sì (Self-Pub)" if any(x in text for x in ['independently', 'kdp', 'indipendente', 'createspace']) else "Tradizionale"
            price = 0.0
            price_el = item.select_one('.a-price .a-offscreen')
            if price_el:
                try: price = float(re.sub(r'[^\d.,]', '', price_el.text).replace(',', '.'))
                except: price = 0.0
            seen.add(title)
            results.append({"Titolo Analizzato": title, "Prezzo": price, "BSR": bsr, "Editore": is_self})
            if len(results) >= 100: break
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR: PARAMETRI E GENERAZIONE AI
# ==============================================================================
with st.sidebar:
    st.markdown("### 🔍 Parametri di Ricerca")
    
    amazon_categories = [
        "Libri (Tutti)", "Arte, cinema e fotografia", "Biografie, diari e memorie", 
        "Calendari e agende", "Casa, hobby e cucina", "Diritto", "Dizionari e opere di consultazione", 
        "Economia, affari e finanza", "Educazione e insegnamento", "Famiglia, salute e benessere", 
        "Fantascienza e Fantasy", "Fumetti e manga", "Gialli e Thriller", "Informatica, Web e Digital Media", 
        "Letteratura e narrativa", "Libri per bambini", "Libri per ragazzi", "Lingua, linguistica e scrittura", 
        "Politica", "Religione e spiritualità", "Romanzi rosa", "Scienze, tecnologia e medicina", 
        "Scienze sociali", "Sport e tempo libero", "Storia", "Viaggi", "Test di preparazione"
    ]
    categoria_selezionata = st.selectbox("Categoria Amazon", amazon_categories)
    genere = st.selectbox("Formato / Sotto-Genere", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Test Prep", "Religioso", "Spirituale", "Meditazione", "Business", "Romanzo Rosa", "Thriller", "Fantasy", "Fantascienza", "Psicologia", "Biografia", "Ricettario"])
    nicchia = st.text_input("Nicchia specifica (es. Dieta Keto)")
    target = st.text_input("Target Lettore (es. Donne Over 50)")
    
    st.markdown("---")
    
    if st.button("Genera Keyword Semantiche", use_container_width=True):
        if not nicchia or not target: st.error("Inserisci nicchia e target!")
        else:
            with st.spinner("Estrazione..."):
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt_kw = (
                    f"Agisci come esperto SEO Amazon specializzato nella categoria '{categoria_selezionata}'. "
                    f"Nicchia: {nicchia}, Genere: {genere}, Target: {target}. "
                    "Genera 5 keyword long-tail specifiche separate da virgola. "
                    "NON scrivere introduzioni, NON scrivere conclusioni, NON aggiungere commenti. "
                    "Rispondi SOLO ed ESCLUSIVAMENTE con la lista di keyword."
                )
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_kw}])
                st.session_state.suggested_kws = res.choices[0].message.content

    if st.session_state.suggested_kws:
        st.success("Keyword generate con successo.")
        st.info(st.session_state.suggested_kws)
        kw_selezionata = st.text_input("Keyword da analizzare:", value=st.session_state.suggested_kws.split(',')[0].strip())
        
        if st.button("Esegui Analisi Mercato", type="primary", use_container_width=True):
            with st.spinner("Scraping dati in corso..."):
                df = get_amazon_data("Italia", kw_selezionata)
                if not df.empty:
                    st.session_state.data, st.session_state.kw = df, kw_selezionata
                    avg_p, indie_r = df['Prezzo'].mean(), (len(df[df['Editore'] == "Sì (Self-Pub)"]) / len(df)) * 100
                    st.session_state.score = 40 + (30 if avg_p > 12.5 else 0) + (30 if indie_r > 40 else 0)
                    
                    if st.session_state.score >= 60:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        prompt_book = f"Analisi POSITIVA per '{kw_selezionata}' nella categoria '{categoria_selezionata}' per il target '{target}'. Genera 3 idee per libri attinenti. Formato TASSATIVO:\nTITOLO: [testo]\nTRAMA: [testo]\n---"
                        st.session_state.suggestions = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
                    else: st.session_state.suggestions = "NEGATIVE"
                else: st.error("⚠️ Nessun dato trovato. Riprova.")
                
    st.markdown("---")
    if st.button("Reset Sessione", use_container_width=True):
        st.session_state.data, st.session_state.suggestions, st.session_state.suggested_kws = None, None, ""
        st.rerun()

# ==============================================================================
# 5. DASHBOARD: RENDERING RISULTATI (PARSER REGEX)
# ==============================================================================
if st.session_state.data is not None:
    st.markdown(f"<div class='white-title'>Analisi Dati: {st.session_state.kw}</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.data['Prezzo'].mean():.2f} €")
    indie_p = (len(st.session_state.data[st.session_state.data['Editore'] == "Sì (Self-Pub)"]) / len(st.session_state.data)) * 100
    c2.metric("Market Share Indie", f"{int(indie_p)}%")
    c3.metric("Score di Profittabilità", f"{st.session_state.score}/100")
    
    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("Visualizza Dati Grezzi", expanded=False):
        st.dataframe(st.session_state.data, use_container_width=True, hide_index=True)

    st.markdown("---")

    if st.session_state.suggestions == "NEGATIVE":
        st.error(f"❌ ANALISI NEGATIVA: La keyword '{st.session_state.kw}' non è profittevole secondo i criteri strategici.")
    elif st.session_state.suggestions:
        st.markdown(f"<div class='white-title'>Output Strategico</div>", unsafe_allow_html=True)
        
        clean_suggestions = st.session_state.suggestions.replace("**", "")
        matches = re.findall(r'TITOLO:\s*(.*?)\s*TRAMA:\s*(.*?)(?=\nTITOLO:|\n---|---|$)', clean_suggestions, re.IGNORECASE | re.DOTALL)
        
        if matches:
            for t_clean, p_clean in matches:
                st.markdown(f"""
                <div class="ebook-card">
                    <div class="ebook-title">{t_clean.strip()}</div>
                    <div class="ebook-plot">{p_clean.strip()}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Formato AI anomalo. Testo grezzo:")
            st.write(st.session_state.suggestions)
