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
# 1. DESIGN SYSTEM: PREMIUM SAAS DASHBOARD
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 12.2", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp { background-color: #f9fafb !important; }

        section[data-testid="stSidebar"] { 
            background-color: #1f2937 !important; 
            min-width: 380px !important;
            border-right: 1px solid #374151;
            padding-top: 2rem;
        }
        section[data-testid="stSidebar"] * { 
            color: #f3f4f6 !important; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #374151 !important;
            border: 1px solid #4b5563 !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 0.5rem !important;
        }

        .program-title { 
            color: #111827 !important; 
            font-size: 2.2rem !important; 
            font-weight: 800; 
            text-align: left; 
            margin-top: 1rem;
            margin-bottom: 2rem; 
            padding-bottom: 1rem;
            border-bottom: 1px solid #e5e7eb;
            letter-spacing: -0.025em;
        }
        .white-title { 
            color: #374151 !important; 
            font-size: 1.4rem !important; 
            font-weight: 700; 
            margin-top: 2rem;
            margin-bottom: 1rem; 
        }

        [data-testid="stMetricValue"] { 
            color: #2563eb !important; 
            font-weight: 800 !important; 
            font-size: 2rem !important;
        }
        [data-testid="stMetricLabel"] p {
            color: #6b7280 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.05em;
        }
        .stMetric { 
            background-color: white !important; 
            border: 1px solid #e5e7eb; 
            padding: 1.5rem; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            text-align: center;
        }

        [data-testid="stDataFrame"] {
            background-color: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1);
            border: 1px solid #e5e7eb;
        }

        .ebook-card {
            background-color: white; 
            border: 1px solid #e5e7eb; 
            border-left: 4px solid #3b82f6; 
            padding: 1.5rem; 
            border-radius: 12px; 
            margin-bottom: 1.5rem; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            transition: transform 0.2s ease;
        }
        .ebook-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
        .ebook-title { color: #111827 !important; font-weight: 800; font-size: 1.25rem; margin-bottom: 0.5rem; }
        .ebook-subtitle { color: #4b5563 !important; font-weight: 600; font-size: 1rem; margin-bottom: 1rem; font-style: italic; }
        .ebook-plot { color: #374151 !important; line-height: 1.6; font-size: 0.95rem; }

        .stButton button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.2rem !important;
            border: 1px solid #4b5563 !important;
            background-color: transparent !important;
            color: white !important;
            transition: all 0.2s ease;
        }
        .stButton button:hover { background-color: #374151 !important; }
        button[kind="primary"] {
            background-color: #2563eb !important; 
            color: white !important;
            border: none !important;
            box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1) !important;
        }
        button[kind="primary"]:hover { background-color: #1d4ed8 !important; }
        
        .badge {
            display: inline-block; padding: 0.25em 0.6em; font-size: 75%; font-weight: 700; 
            line-height: 1; text-align: center; white-space: nowrap; vertical-align: baseline; 
            border-radius: 0.25rem; color: white; margin-bottom: 10px;
        }
        .badge-green { background-color: #10b981; }
        .badge-yellow { background-color: #f59e0b; }
        .badge-red { background-color: #ef4444; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE MEMORIA E STATO
# ==============================================================================
for key in ['data', 'suggestions', 'kw', 'score', 'suggested_kws', 'demand', 'difficulty', 'reviews']:
    if key not in st.session_state: st.session_state[key] = None if key != 'score' else 0

# ==============================================================================
# 3. MOTORE DI SCRAPING POTENZIATO CON RECENSIONI
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
            
            # Estrazione BSR
            bsr_match = re.search(r'(?:n\.|#|rank)\s*([0-9.,]+)', text)
            bsr = float(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else np.nan
            
            # Estrazione Recensioni (Nuova Feature Funzionale)
            rev_el = item.select_one('.a-icon-alt')
            reviews = 0
            if rev_el:
                rev_text_container = item.select_one('.a-size-base.s-underline-text')
                if rev_text_container:
                    try: reviews = int(re.sub(r'[^\d]', '', rev_text_container.text))
                    except: pass
            
            is_self = "Sì (Self-Pub)" if any(x in text for x in ['independently', 'kdp', 'indipendente', 'createspace']) else "Tradizionale"
            
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
# 4. SIDEBAR: RICERCA SEMANTICA E ANALISI MERCATO
# ==============================================================================
with st.sidebar:
    st.markdown("### 🔍 Targeting Mercato")
    
    amazon_categories = ["Libri (Tutti)", "Arte, cinema e fotografia", "Biografie, diari e memorie", "Casa, hobby e cucina", "Diritto", "Economia, affari e finanza", "Educazione e insegnamento", "Famiglia, salute e benessere", "Fantascienza e Fantasy", "Gialli e Thriller", "Informatica", "Letteratura e narrativa", "Libri per bambini", "Politica", "Religione e spiritualità", "Romanzi rosa", "Scienze, tecnologia e medicina", "Scienze sociali", "Sport e tempo libero", "Storia", "Viaggi", "Test di preparazione"]
    categoria_selezionata = st.selectbox("Categoria Amazon", amazon_categories)
    genere = st.selectbox("Formato Editoriale", ["Saggio", "Manuale Operativo", "Test Prep", "Workbook", "Romanzo", "Ricettario", "Biografia"])
    nicchia = st.text_input("Nicchia specifica (es. Dieta Keto)")
    target = st.text_input("Target Lettore (es. Donne Over 50)")
    
    st.markdown("---")
    
    if st.button("🪄 Genera Long-Tail Keywords", use_container_width=True):
        if not nicchia or not target: st.error("Inserisci nicchia e target!")
        else:
            with st.spinner("Analisi query di ricerca in corso..."):
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt_kw = (
                    f"Agisci come tool SEO Amazon. Categoria '{categoria_selezionata}', Nicchia: {nicchia}, Formato: {genere}, Target: {target}. "
                    "Genera 5 keyword long-tail (3-5 parole) con alta intenzione d'acquisto, separate solo da virgola. "
                    "NON inserire commenti."
                )
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_kw}])
                st.session_state.suggested_kws = res.choices[0].message.content

    if st.session_state.suggested_kws:
        st.success("Analisi Semantica Completata.")
        st.info(st.session_state.suggested_kws)
        kw_selezionata = st.text_input("Seleziona Keyword Target:", value=st.session_state.suggested_kws.split(',')[0].strip())
        
        if st.button("🚀 Esegui Scansione Competitor", type="primary", use_container_width=True):
            with st.spinner("Raccolta dati da Amazon in corso..."):
                df = get_amazon_data("Italia", kw_selezionata)
                if not df.empty:
                    st.session_state.data, st.session_state.kw = df, kw_selezionata
                    
                    # LOGICA DI PROFITTABILITÀ AVANZATA (Stile SaaS)
                    avg_p = df['Prezzo'].mean()
                    indie_r = (len(df[df['Editore'] == "Sì (Self-Pub)"]) / len(df)) * 100
                    avg_rev = df['Recensioni'].mean()
                    
                    # Calcolo Score base
                    base_score = 40 + (30 if avg_p > 12.5 else 0) + (30 if indie_r > 40 else 0)
                    
                    # Penali Competizione (Se la media recensioni è troppo alta, la nicchia è satura)
                    if avg_rev > 1500: st.session_state.difficulty = "Estrema"
                    elif avg_rev > 500: st.session_state.difficulty = "Alta"; base_score -= 15
                    elif avg_rev > 100: st.session_state.difficulty = "Media"
                    else: st.session_state.difficulty = "Bassa"; base_score += 10
                    
                    # Calcolo Domanda stimata tramite BSR validi
                    valid_bsr = pd.to_numeric(df['BSR'], errors='coerce').dropna()
                    if not valid_bsr.empty:
                        med_bsr = valid_bsr.median()
                        if med_bsr < 10000: st.session_state.demand = "Altissima"
                        elif med_bsr < 50000: st.session_state.demand = "Alta"
                        elif med_bsr < 150000: st.session_state.demand = "Media"
                        else: st.session_state.demand = "Bassa"
                    else: st.session_state.demand = "Sconosciuta"

                    st.session_state.score = min(max(base_score, 0), 100) # Clamp tra 0 e 100
                    st.session_state.reviews = avg_rev
                    
                    # GENERAZIONE PACCHETTO EDITORIALE COMPLETO
                    if st.session_state.score >= 50: # Abbassato il threshold per dare più idee
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        prompt_book = f"""
                        L'analisi di mercato per '{kw_selezionata}' è positiva. Genera 3 idee di libri per il target '{target}'.
                        Formato TASSATIVO e IDENTICO per ogni libro (Non cambiare le parole chiave del formato):
                        TITOLO: [Titolo magnetico principale]
                        SOTTOTITOLO: [Sottotitolo SEO ottimizzato]
                        TRAMA: [Sinossi persuasiva di 3-4 righe]
                        ---
                        """
                        st.session_state.suggestions = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
                    else: st.session_state.suggestions = "NEGATIVE"
                else: st.error("⚠️ Impossibile analizzare. Amazon ha respinto le richieste o pagina vuota.")
                
    st.markdown("---")
    if st.button("🔄 Reset Dashboard", use_container_width=True):
        for key in ['data', 'suggestions', 'kw', 'score', 'suggested_kws', 'demand', 'difficulty', 'reviews']:
            st.session_state[key] = None if key != 'score' else 0
        st.rerun()

# ==============================================================================
# 5. DASHBOARD: RENDERING RISULTATI E COMPETITION METRICS
# ==============================================================================
if st.session_state.data is not None:
    st.markdown(f"<div class='white-title'>Analisi Competitiva: <span style='color: #2563eb;'>{st.session_state.kw.upper()}</span></div>", unsafe_allow_html=True)
    
    # ROW 1: Metriche Economiche
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.data['Prezzo'].mean():.2f} €")
    c2.metric("Market Share Indie", f"{int((len(st.session_state.data[st.session_state.data['Editore'] == 'Sì (Self-Pub)']) / len(st.session_state.data)) * 100)}%")
    c3.metric("Recensioni Medie (Top 100)", f"{int(st.session_state.reviews)}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 2: Metriche Strategiche
    sc1, sc2, sc3 = st.columns(3)
    
    diff_color = "green" if st.session_state.difficulty in ["Bassa", "Media"] else "red" if st.session_state.difficulty == "Estrema" else "yellow"
    dem_color = "green" if st.session_state.demand in ["Altissima", "Alta"] else "yellow" if st.session_state.demand == "Media" else "red"
    score_color = "green" if st.session_state.score >= 70 else "yellow" if st.session_state.score >= 50 else "red"

    sc1.markdown(f"<div class='stMetric'><p style='color: #6b7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;'>Difficoltà Keyword</p><div class='badge badge-{diff_color}'>{st.session_state.difficulty}</div></div>", unsafe_allow_html=True)
    sc2.markdown(f"<div class='stMetric'><p style='color: #6b7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;'>Domanda Stimata</p><div class='badge badge-{dem_color}'>{st.session_state.demand}</div></div>", unsafe_allow_html=True)
    sc3.markdown(f"<div class='stMetric'><p style='color: #6b7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;'>Opportunity Score</p><div class='badge badge-{score_color}'>{int(st.session_state.score)}/100</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("📊 Tabella Dati Competitor (Esporta)", expanded=False):
        st.dataframe(st.session_state.data, use_container_width=True, hide_index=True)

    st.markdown("---")

    if st.session_state.suggestions == "NEGATIVE":
        st.error(f"❌ ANALISI NEGATIVA: L'Opportunity Score per '{st.session_state.kw}' è troppo basso ({int(st.session_state.score)}/100). Competizione troppo alta o mercato povero.")
    elif st.session_state.suggestions:
        st.markdown(f"<div class='white-title'>Pacchetto Editoriale Suggerito</div>", unsafe_allow_html=True)
        
        clean_suggestions = st.session_state.suggestions.replace("**", "")
        # Regex estesa per catturare Titolo, Sottotitolo e Trama
        matches = re.findall(r'TITOLO:\s*(.*?)\s*SOTTOTITOLO:\s*(.*?)\s*TRAMA:\s*(.*?)(?=\nTITOLO:|\n---|---|$)', clean_suggestions, re.IGNORECASE | re.DOTALL)
        
        if matches:
            for t_clean, s_clean, p_clean in matches:
                st.markdown(f"""
                <div class="ebook-card">
                    <div class="ebook-title">{t_clean.strip()}</div>
                    <div class="ebook-subtitle">{s_clean.strip()}</div>
                    <div class="ebook-plot">{p_clean.strip()}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Formato AI non riconosciuto. Ecco il testo grezzo:")
            st.write(st.session_state.suggestions)
