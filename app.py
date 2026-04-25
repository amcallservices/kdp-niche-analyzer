import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM E CONFIGURAZIONE
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 12.6", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp { background-color: #f9fafb !important; }

        /* SIDEBAR (LEFT) */
        section[data-testid="stSidebar"] { 
            background-color: #1f2937 !important; 
            min-width: 320px !important;
            border-right: 1px solid #374151;
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] * { 
            color: #f3f4f6 !important; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #374151 !important;
            border: 1px solid #4b5563 !important;
            color: white !important;
            border-radius: 6px !important;
        }

        .program-title { 
            color: #111827 !important; 
            font-size: 2rem !important; 
            font-weight: 800; 
            margin-bottom: 1rem; 
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0.5rem;
        }
        .section-title {
            color: #374151 !important; 
            font-size: 1.2rem !important; 
            font-weight: 700; 
            margin-bottom: 1rem;
            margin-top: 1rem;
        }

        /* METRICS */
        [data-testid="stMetricValue"] { color: #2563eb !important; font-weight: 800 !important; font-size: 1.8rem !important; }
        [data-testid="stMetricLabel"] p { color: #6b7280 !important; font-weight: 600 !important; text-transform: uppercase; font-size: 0.8rem; }
        .stMetric { background-color: white !important; border: 1px solid #e5e7eb; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

        /* DATAFRAME */
        [data-testid="stDataFrame"] {
            background-color: white; padding: 1rem; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
        }

        /* AI RIGHT PANEL */
        .ai-panel {
            background-color: white; padding: 1.5rem; border-radius: 8px;
            border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%;
        }

        .stButton button { border-radius: 6px !important; font-weight: 600 !important; width: 100%;}
        button[kind="primary"] { background-color: #2563eb !important; color: white !important; border: none !important; }
        button[kind="primary"]:hover { background-color: #1d4ed8 !important; }
        
        .empty-state {
            text-align: center; padding: 3rem; color: #6b7280; font-size: 1.1rem;
            border: 2px dashed #d1d5db; border-radius: 12px; margin-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE STATO
# ==============================================================================
for key in ['raw_data', 'suggestions', 'search_category', 'selected_market']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# 3. DIZIONARI
# ==============================================================================
marketplaces = {
    "🇺🇸 Amazon.com (US)": "amazon.com",
    "🇬🇧 Amazon.co.uk (UK)": "amazon.co.uk",
    "🇮🇹 Amazon.it (Italia)": "amazon.it",
    "🇩🇪 Amazon.de (Germany)": "amazon.de",
    "🇫🇷 Amazon.fr (France)": "amazon.fr",
    "🇪🇸 Amazon.es (Spain)": "amazon.es"
}

categories_map = {
    "amazon.it": ["Tutte le categorie", "Libri", "Kindle Store", "Arte, cinema e fotografia", "Biografie, diari e memorie", "Casa, hobby e cucina", "Diritto", "Economia, affari e finanza", "Fantascienza e Fantasy", "Fumetti e manga", "Gialli e Thriller", "Informatica", "Romanzi rosa", "Salute e famiglia", "Sport", "Storia"],
    "amazon.com": ["All Departments", "Books", "Kindle Store", "Arts & Photography", "Biographies & Memoirs", "Business & Money", "Cookbooks", "Crafts & Hobbies", "Health & Fitness", "History", "Mystery & Thriller", "Romance", "Science Fiction", "Self-Help", "Sports"],
    "amazon.co.uk": ["All Departments", "Books", "Kindle Store", "Arts & Photography", "Biographies & Memoirs", "Business", "Comics", "Computing", "Crime & Thrillers", "Health & Lifestyle", "History", "Romance", "Science Fiction", "Sports"],
    "amazon.de": ["Alle Kategorien", "Bücher", "Kindle-Shop", "Biografien", "Business", "Comics", "Computer", "Fachbücher", "Fantasy", "Kochen", "Krimi", "Ratgeber", "Reise", "Sport"],
    "amazon.fr": ["Toutes nos boutiques", "Livres", "Boutique Kindle", "Art", "Bande dessinée", "Biographies", "Cuisine", "Entreprise", "Histoire", "Informatique", "Policiers", "Romance", "Santé", "Science-Fiction"],
    "amazon.es": ["Todos los departamentos", "Libros", "Tienda Kindle", "Arte", "Biografías", "Cómics", "Deportes", "Economía", "Historia", "Hogar", "Informática", "Policíaca", "Romántica", "Salud"]
}

fallback_keywords = {
    "amazon.it": "libri", "amazon.com": "books", "amazon.co.uk": "books", 
    "amazon.de": "bücher", "amazon.fr": "livres", "amazon.es": "libros"
}

# ==============================================================================
# 4. MOTORE DI SCRAPING
# ==============================================================================
def get_amazon_data(domain, keyword):
    ANT_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"
    SCRAPERAPI_KEY = st.secrets.get("SCRAPERAPI_KEY", "")
    WEBSCRAPINGAI_KEY = st.secrets.get("WEBSCRAPINGAI_KEY", "")
    
    def fetch_with_triple_fallback(p):
        amazon_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={p}"
        try:
            r = requests.get(f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(amazon_url)}&x-api-key={ANT_KEY}&browser=true&proxy_type=residential", timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        try:
            r = requests.get(f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={urllib.parse.quote(amazon_url)}&render=true", timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        try:
            r = requests.get(f"https://api.webscraping.ai/html?api_key={WEBSCRAPINGAI_KEY}&url={urllib.parse.quote(amazon_url)}&proxy=residential&js=true", timeout=30)
            if r.status_code == 200: return r.text
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        pages = list(executor.map(fetch_with_triple_fallback, range(1, 8)))
    
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
            
            bsr_match = re.search(r'(?:n\.|nr\.|n\.º|#|rank)\s*([0-9.,]+)', text)
            bsr = float(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else np.nan
            
            rev_el = item.select_one('.a-icon-alt')
            reviews = 0
            if rev_el:
                rev_text_container = item.select_one('.a-size-base.s-underline-text')
                if rev_text_container:
                    try: reviews = int(re.sub(r'[^\d]', '', rev_text_container.text))
                    except: pass
            
            is_self = "Independent" if any(x in text for x in ['independently', 'kdp', 'indipendente', 'createspace', 'unabhängig']) else "Publishing House"
            
            price = 0.0
            price_el = item.select_one('.a-price .a-offscreen')
            if price_el:
                try: price = float(re.sub(r'[^\d.,]', '', price_el.text).replace(',', '.'))
                except: price = 0.0
                
            seen.add(title)
            results.append({"Titolo": title, "Prezzo": price, "BSR": bsr if not np.isnan(bsr) else "N/D", "Recensioni": reviews, "Editore": is_self})
            if len(results) >= 100: break
    return pd.DataFrame(results)

# ==============================================================================
# 5. SIDEBAR (FASE 1) E AZIONI
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>STEP 1: MARKET DATA</p>", unsafe_allow_html=True)
    
    mkt_choice = st.selectbox("Marketplace *", list(marketplaces.keys()))
    domain = marketplaces[mkt_choice]
    st.session_state.selected_market = domain
    
    cat_list = categories_map.get(domain, ["All Departments"])
    cat_choice = st.selectbox("Categoria", cat_list)
    
    pub_choice = st.selectbox("Publisher Type *", ["All Publishers", "Publishing House", "Independent"])
    
    st.markdown("---")
    
    if st.button("🔍 Estrai Dati Categoria", type="primary"):
        with st.spinner(f"Scraping in corso su {domain}..."):
            search_query = fallback_keywords.get(domain, "books") if cat_choice in ["Tutte le categorie", "All Departments", "Alle Kategorien", "Toutes nos boutiques", "Todos los departamentos"] else cat_choice
            
            df = get_amazon_data(domain, search_query)
            if not df.empty:
                st.session_state.raw_data = df
                st.session_state.search_category = cat_choice
                st.session_state.suggestions = None 
            else:
                st.error("Nessun dato trovato. Riprova.")
                    
    if st.button("🔄 Reset Dati"):
        for key in ['raw_data', 'suggestions', 'search_category']: st.session_state[key] = None
        st.rerun()

# ==============================================================================
# 6. DASHBOARD E TABELLA DATI
# ==============================================================================
if st.session_state.raw_data is None:
    st.markdown("<div class='empty-state'>🚀 Usa il pannello laterale per selezionare il Marketplace, la categoria e avviare l'estrazione dati.</div>", unsafe_allow_html=True)
else:
    # 1. Filtro dei dati in base alla scelta della sidebar (in tempo reale)
    df_to_show = st.session_state.raw_data
    if pub_choice != "All Publishers":
        df_to_show = df_to_show[df_to_show['Editore'] == pub_choice]

    col_data, col_ai = st.columns([6, 4], gap="large")

    # --- COLONNA SINISTRA: TABELLA ---
    with col_data:
        st.markdown(f"<div class='section-title'>Dati Estratti: <span style='color: #2563eb;'>{st.session_state.search_category}</span></div>", unsafe_allow_html=True)
        
        if not df_to_show.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Libri Rilevati", len(df_to_show))
            c2.metric("Prezzo Medio", f"{df_to_show['Prezzo'].mean():.2f} €")
            c3.metric("Recensioni Medie", f"{int(df_to_show['Recensioni'].mean())}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Mostra la tabella
            st.dataframe(df_to_show[['Titolo', 'BSR', 'Prezzo', 'Recensioni', 'Editore']], use_container_width=True, height=600, hide_index=True)
        else:
            st.warning("Nessun libro trovato per questo tipo di autore in questa estrazione.")

    # --- COLONNA DESTRA: AI LAB ---
    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>STEP 2: IDEAZIONE</p>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.9rem; color:#4b5563;'>Dopo aver analizzato visivamente i dati a sinistra, inserisci la nicchia e genera la strategia.</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        nicchia_ai = st.text_input("Nicchia Individuata (dai dati) *", placeholder="es. Dieta Keto, Trading")
        target_ai = st.text_input("Definisci Target Lettore *", placeholder="es. Donne Over 50")
        format_ai = st.selectbox("Formato Libro *", ["Manuale Pratico", "Saggio", "Guida Passo-Passo", "Workbook", "Romanzo", "Ricettario", "Biografia"])
        
        if st.button("🪄 Genera Pacchetto Editoriale", type="primary"):
            if not nicchia_ai or not target_ai:
                st.error("Inserisci sia la Nicchia che il Target Lettore.")
            else:
                with st.spinner("L'AI sta generando le idee..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt_book = f"""
                    Agisci come un Publisher di successo su Amazon {domain}. 
                    Categoria: '{cat_choice}'. Nicchia individuata: '{nicchia_ai}'. Target: {target_ai}. Formato: {format_ai}.
                    Genera 3 idee di libri ottimizzati.
                    Formato TASSATIVO:
                    TITOLO: [Titolo magnetico principale]
                    SOTTOTITOLO: [Sottotitolo SEO ottimizzato]
                    TRAMA: [Sinossi persuasiva di 3-4 righe]
                    ---
                    """
                    st.session_state.suggestions = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
        
        # Rendering Output AI
        if st.session_state.suggestions:
            st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
            clean_suggestions = st.session_state.suggestions.replace("**", "")
            matches = re.findall(r'TITOLO:\s*(.*?)\s*SOTTOTITOLO:\s*(.*?)\s*TRAMA:\s*(.*?)(?=\nTITOLO:|\n---|---|$)', clean_suggestions, re.IGNORECASE | re.DOTALL)
            
            if matches:
                for t_clean, s_clean, p_clean in matches:
                    st.markdown(f"""
                    <div style='background-color:#f3f4f6; padding:1.2rem; border-radius:8px; margin-bottom:1rem; border-left:4px solid #10b981;'>
                        <div style='font-weight:800; color:#111827; font-size:1.1rem; margin-bottom:0.2rem;'>{t_clean.strip()}</div>
                        <div style='font-weight:600; color:#4b5563; font-size:0.9rem; margin-bottom:0.8rem; font-style:italic;'>{s_clean.strip()}</div>
                        <div style='color:#374151; font-size:0.9rem; line-height:1.5;'>{p_clean.strip()}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write(st.session_state.suggestions)
                
        st.markdown("</div>", unsafe_allow_html=True)
