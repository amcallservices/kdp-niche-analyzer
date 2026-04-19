import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 1. DESIGN SYSTEM: CONTRASTO BIANCO/NERO & RIMOZIONE MENU
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 11.9.1", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; min-width: 450px !important;
            border-right: 1px solid #30363d;
        }
        section[data-testid="stSidebar"] * { color: white !important; }
        
        .white-title { color: white !important; font-size: 2.2rem !important; font-weight: 800; margin-bottom: 20px; text-align: center; }
        .program-title { color: #ffd700 !important; font-size: 2.8rem !important; font-weight: 900; text-align: center; margin-bottom: 30px; text-transform: uppercase; border-bottom: 2px solid #ffd700; padding-bottom: 10px; }

        .stMarkdown p, .stMarkdown li, .stMarkdown span, [data-testid="stMetricLabel"] p { 
            color: #000000 !important; font-weight: 500;
        }
        
        .explanation-box {
            background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; border-radius: 10px; color: black !important;
        }
        .ebook-card {
            background-color: white; border: 2px solid #ffd700; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 2px 2px 12px rgba(0,0,0,0.1);
        }
        .ebook-title { color: #856404 !important; font-weight: 900; font-size: 1.5rem; margin-bottom: 10px; }
        .ebook-plot { color: #000000 !important; line-height: 1.6; font-size: 1.1rem; }
        
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }
        .stMetric { background-color: white !important; border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>Analisi delle Nicchie Profittevoli</div>", unsafe_allow_html=True)

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
        # FIX: Aumentato il range a 11 (scansiona le prime 10 pagine invece di 7)
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
            
            # FIX: Aumentato il limite di libri catturati da 60 a 100
            if len(results) >= 100: break
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR CON GENERAZIONE SILENZIOSA E PROMPT BLINDATO
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 11.9.1")
    if st.button("🔄 RESET"):
        st.session_state.data, st.session_state.suggestions, st.session_state.suggested_kws = None, None, ""
        st.rerun()
    
    st.markdown("---")
    genere = st.selectbox("Genere / Formato", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Test Prep", "Religioso", "Spirituale", "Meditazione", "Business", "Romanzo Rosa", "Thriller", "Fantasy", "Fantascienza", "Psicologia", "Biografia", "Ricettario"])
    nicchia = st.text_input("Nicchia specifica")
    target = st.text_input("Target Lettore")
    
    if st.button("🔍 GENERA KEYWORD CHIRURGICHE"):
        if not nicchia or not target: st.error("Inserisci nicchia e target!")
        else:
            with st.spinner("Estrazione keyword..."):
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt_kw = (
                    f"Agisci come esperto SEO Amazon. Nicchia: {nicchia}, Genere: {genere}, Target: {target}. "
                    "Genera 5 keyword long-tail specifiche separate da virgola. "
                    "NON scrivere introduzioni, NON scrivere conclusioni, NON aggiungere commenti. "
                    "Rispondi SOLO ed ESCLUSIVAMENTE con la lista di keyword."
                )
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_kw}])
                st.session_state.suggested_kws = res.choices[0].message.content

    if st.session_state.suggested_kws:
        st.info(f"Suggerite: {st.session_state.suggested_kws}")
        kw_selezionata = st.text_input("Keyword finale:", value=st.session_state.suggested_kws.split(',')[0].strip())
        
        if st.button("🚀 LANCIA ANALISI TRIPLE-ENGINE", type="primary"):
            with st.spinner("Analisi e drafting..."):
                df = get_amazon_data("Italia", kw_selezionata)
                if not df.empty:
                    st.session_state.data, st.session_state.kw = df, kw_selezionata
                    avg_p, indie_r = df['Prezzo'].mean(), (len(df[df['Editore'] == "Sì (Self-Pub)"]) / len(df)) * 100
                    st.session_state.score = 40 + (30 if avg_p > 12.5 else 0) + (30 if indie_r > 40 else 0)
                    
                    if st.session_state.score >= 60:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        # PROMPT SEMPLIFICATO E A PROVA DI ERRORE
                        prompt_book = f"Analisi POSITIVA per '{kw_selezionata}' ({genere}) per il target '{target}'. Genera 3 idee per libri attinenti. Formato TASSATIVO:\nTITOLO: [testo]\nTRAMA: [testo]\n---"
                        st.session_state.suggestions = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
                    else: st.session_state.suggestions = "NEGATIVE"
                else: st.error("⚠️ Nessun dato trovato. Riprova.")

# ==============================================================================
# 5. DASHBOARD: RENDERING E STAMPA RISULTATI (PARSER REGEX INFALLIBILE)
# ==============================================================================
if st.session_state.data is not None:
    st.markdown(f"<div class='white-title'>Report Chirurgico: {st.session_state.kw.upper()}</div>", unsafe_allow_html=True)
    st.dataframe(st.session_state.data, use_container_width=True, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.data['Prezzo'].mean():.2f} €")
    indie_p = (len(st.session_state.data[st.session_state.data['Editore'] == "Sì (Self-Pub)"]) / len(st.session_state.data)) * 100
    c2.metric("Indie Ratio", f"{int(indie_p)}%")
    c3.metric("Score Nicchia", f"{st.session_state.score}/100")

    if st.session_state.suggestions == "NEGATIVE":
        st.error(f"❌ ANALISI NEGATIVA: La keyword '{st.session_state.kw}' non è profittevole secondo i criteri strategici.")
    elif st.session_state.suggestions:
        st.success(f"✅ ANALISI POSITIVA! Ecco i titoli e le trame per '{st.session_state.kw}':")
        
        # FIX: Puliamo il testo da eventuali grassetti markdown (**) generati dall'AI
        clean_suggestions = st.session_state.suggestions.replace("**", "")
        
        # FIX: Regex infallibile che cattura tutto quello che c'è tra "TITOLO:" e "TRAMA:"
        matches = re.findall(r'TITOLO:\s*(.*?)\s*TRAMA:\s*(.*?)(?=\nTITOLO:|\n---|---|$)', clean_suggestions, re.IGNORECASE | re.DOTALL)
        
        if matches:
            for t_clean, p_clean in matches:
                st.markdown(f"""
                <div class="ebook-card">
                    <div class="ebook-title">📘 {t_clean.strip()}</div>
                    <div class="ebook-plot"><b>Strategia Editoriale:</b> {p_clean.strip()}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Fallback visivo se l'IA risponde in un formato completamente alieno
            st.warning("⚠️ L'Intelligenza Artificiale ha generato i suggerimenti ma in un formato anomalo. Ecco il testo grezzo:")
            st.write(st.session_state.suggestions)
