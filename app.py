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
# 1. DESIGN SYSTEM: PREMIUM SAAS DASHBOARD (DUAL-PANEL SEQUENZIALE)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 12.5", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp { background-color: #f9fafb !important; }

        /* MAIN SIDEBAR (LEFT) */
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

        /* DATAFRAME E TABELLE */
        [data-testid="stDataFrame"] {
            background-color: white; padding: 1rem; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
        }

        /* AI RIGHT PANEL */
        .ai-panel {
            background-color: white;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            height: 100%;
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
for key in ['raw_data', 'filtered_data', 'suggestions', 'search_category', 'selected_market']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# 3. DIZIONARI CATEGORIE MULTILINGUA
# ==============================================================================
marketplaces = {
    "🇺🇸 Amazon.com (US)": "amazon.com",
    "🇬🇧 Amazon.co.uk (UK)": "amazon.co.uk",
    "🇮🇹 Amazon.it (Italia)": "amazon.it",
    "🇩🇪 Amazon.de (Germany)": "amazon.de",
    "🇫🇷 Amazon.fr (France)": "amazon.fr",
    "🇪🇸 Amazon.es (Spain)": "amazon.es"
}

# Mappe Categorie dinamiche in base al mercato
categories_map = {
    "amazon.it": ["Tutte le categorie", "Libri", "Kindle Store", "Arte, cinema e fotografia", "Biografie, diari e memorie", "Casa, hobby e cucina", "Diritto", "Economia, affari e finanza", "Fantascienza e Fantasy", "Fumetti e manga", "Gialli e Thriller", "Informatica, Web e Digital Media", "Romanzi rosa", "Salute, famiglia e stile di vita", "Sport e tempo libero", "Storia"],
    "amazon.com": ["All Departments", "Books", "Kindle Store", "Arts & Photography", "Biographies & Memoirs", "Business & Money", "Cookbooks, Food & Wine", "Crafts, Hobbies & Home", "Health, Fitness & Dieting", "History", "Mystery, Thriller & Suspense", "Romance", "Science Fiction & Fantasy", "Self-Help", "Sports & Outdoors"],
    "amazon.co.uk": ["All Departments", "Books", "Kindle Store", "Arts & Photography", "Biographies & Memoirs", "Business, Finance & Law", "Comics & Graphic Novels", "Computing & Internet", "Crime, Thrillers & Mystery", "Health, Family & Lifestyle", "History", "Romance", "Science Fiction & Fantasy", "Sports, Hobbies & Games"],
    "amazon.de": ["Alle Kategorien", "Bücher", "Kindle-Shop", "Biografien & Erinnerungen", "Business & Karriere", "Comics & Mangas", "Computer & Internet", "Fachbücher", "Fantasy & Science Fiction", "Kochen & Genießen", "Krimi & Thriller", "Ratgeber", "Reise & Abenteuer", "Sport & Fitness"],
    "amazon.fr": ["Toutes nos boutiques", "Livres", "Boutique Kindle", "Art, Musique et Cinéma", "Bande dessinée", "Biographies et témoignages", "Cuisine et Vins", "Entreprise et Bourse", "Histoire", "Informatique et Internet", "Policiers et Suspense", "Romance et littérature sentimentale", "Santé, Forme et Diététique", "Science-Fiction et Fantasy"],
    "amazon.es": ["Todos los departamentos", "Libros", "Tienda Kindle", "Arte, cine y fotografía", "Biografías, diarios y hechos reales", "Cómics y manga", "Deportes y aire libre", "Economía y empresa", "Historia", "Hogar, manualidades y estilos de vida", "Informática, internet y medios digitales", "Policíaca, negra y suspense", "Romántica", "Salud, familia y desarrollo personal"]
}

# Traduzioni di fallback per la query vuota ("Tutte le categorie")
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
        pages = list(executor.map(fetch_with_triple_fallback, range(1, 8))) # Scansione
    
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
            
            # Controllo Editore multilingua
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
# 5. MAIN SIDEBAR (FASE 1: RICERCA DATI PER CATEGORIA)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>STEP 1: MARKET DATA</p>", unsafe_allow_html=True)
    
    mkt_choice = st.selectbox("Marketplace *", list(marketplaces.keys()))
    domain = marketplaces[mkt_choice]
    st.session_state.selected_market = domain
    
    # Categorie Dinamiche
    cat_list = categories_map.get(domain, ["All Departments"])
    cat_choice = st.selectbox("Categoria", cat_list)
    
    pub_choice = st.selectbox("Publisher Type *", ["All Publishers", "Publishing House", "Independent"])
    
    st.markdown("---")
    
    if st.button("🔍 Estrai Dati Categoria", type="primary"):
        with st.spinner(f"Scraping in corso su {domain} per la categoria '{cat_choice}'..."):
            
            # Definiamo la query di ricerca. Se è "Tutte le categorie", usiamo una parola generica come "Libri"
            search_query = cat_choice
            if search_query in ["Tutte le categorie", "All Departments", "Alle Kategorien", "Toutes nos boutiques", "Todos los departamentos"]:
                search_query = fallback_keywords.get(domain, "books")

            df = get_amazon_data(domain, search_query)
            if not df.empty:
                st.session_state.raw_data = df
                st.session_state.search_category = cat_choice
                st.session_state.suggestions = None # Reset AI lab
            else:
                st.error("Nessun dato trovato o blocco di rete temporaneo.")
                    
    if st.button("🔄 Reset Dati"):
        for key in ['raw_data', 'filtered_data', 'suggestions', 'search_category']: st.session_state[key] = None
        st.rerun()

# ==============================================================================
# 6. CORE LAYOUT: RISULTATI E PANNELLO AI (FASE 2)
# ==============================================================================
if st.session_state.raw_data is None:
    st.markdown("<div class='empty-state'>🚀 Usa il pannello laterale per selezionare il Marketplace, la categoria e avviare l'estrazione dati.</div>", unsafe_allow_html=True)

else:
    df = st.session_state.raw_data
    if pub_choice != "All Publishers": df = df[df['Editore'] == pub_choice]

    col_data, col_ai = st.columns([6, 4], gap="large")

    # --- COLONNA SINISTRA: RISULTATI E TABELLA ---
    with col_data:
        st.markdown(f"<div class='section-title'>Dati Estratti: <span style='color: #2563eb;'>{st.session_state.search_category}</span></div>", unsafe_allow_html=True)
        
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Libri Rilevati", len(df))
            c2.metric("Prezzo Medio", f"{df['Prezzo'].mean():.2f}")
            c3.metric("Recensioni Medie", f"{int(df['Recensioni'].mean())}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Mostra chiaramente la tabella dati per l'analisi visiva
            st.dataframe(df[['Titolo', 'BSR', 'Prezzo', 'Recensioni', 'Editore']], use_container_width=True, height=600, hide_index=True)
        else:
            st.warning(f"Nessun libro trovato per il filtro autore selezionato.")

    # --- COLONNA DESTRA: AI STRATEGY LAB (ATTIVO SOLO DOPO I DATI) ---
    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>STEP 2: IDEAZIONE</p>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.9rem; color:#4b5563;'>Dopo aver analizzato visivamente i dati a sinistra, inserisci la nicchia individuata e genera la strategia.</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # NUOVO INPUT: Nicchia individuata manualmente dall'utente
        nicchia_ai = st.text_input("Nicchia Individuata (dai dati) *", placeholder="es. Dieta Keto, Trading per principianti")
        target_ai = st.text_input("Definisci Target Lettore *", placeholder="es. Donne Over 50, Programmatori Junior")
        format_ai = st.selectbox("Formato Libro *", ["Manuale Pratico", "Saggio", "Guida Passo-Passo", "Workbook", "Romanzo", "Ricettario", "Biografia"])
        
        if st.button("🪄 Genera Pacchetto Editoriale", type="primary"):
            if df.empty:
                st.error("Estrai prima dei dati validi a sinistra.")
            elif not nicchia_ai or not target_ai:
                st.error("Inserisci sia la Nicchia che il Target Lettore.")
            else:
                with st.spinner("L'AI sta generando le idee..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt_book = f"""
                    Agisci come un Publisher di successo su Amazon {domain}. 
                    L'utente ha esplorato la Categoria: '{cat_choice}' e ha individuato la seguente Nicchia: '{nicchia_ai}'. 
                    Target Lettore: {target_ai}. 
                    Formato Libro: {format_ai}.
                    
                    Basandoti su queste informazioni, genera 3 idee di libri altamente ottimizzati per vendere su Amazon. 
                    Devono risolvere i problemi del target e differenziarsi dalla concorrenza.
                    Formato TASSATIVO (non inserire commenti extra):
                    TITOLO: [Titolo magnetico principale]
                    SOTTOTITOLO: [Sottotitolo SEO ottimizzato]
                    TRAMA: [Sinossi persuasiva di 3-4 righe]
                    ---
                    """
                    st.session_state.suggestions = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
        
        # Stampa Risultati AI
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
                st.warning("⚠️ Formato AI non riconosciuto:")
                st.write(st.session_state.suggestions)
                
        st.markdown("</div>", unsafe_allow_html=True)
