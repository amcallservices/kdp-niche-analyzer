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
st.set_page_config(page_title="KDP OMNI-REASONER 11.1", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        /* RIMOZIONE MENU E BARRE STREAMLIT */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        /* SIDEBAR: SFONDO SCURO E TESTO BIANCO */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; min-width: 450px !important;
            border-right: 1px solid #30363d;
        }
        section[data-testid="stSidebar"] * { color: white !important; }
        
        /* TITOLI RISULTATI: BIANCO */
        .white-title { color: white !important; font-size: 2.5rem !important; font-weight: 800; margin-bottom: 20px; text-align: center; }
        .program-title { color: #ffd700 !important; font-size: 3rem !important; font-weight: 900; text-align: center; margin-bottom: 40px; text-transform: uppercase; border-bottom: 2px solid #ffd700; padding-bottom: 10px; }

        /* CORPO ANALISI: TESTO NERO */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, [data-testid="stMetricLabel"] p { 
            color: #000000 !important; font-weight: 500;
        }
        
        /* BOX E CARDS */
        .explanation-box {
            background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; border-radius: 10px; color: black !important;
        }
        .ebook-card {
            background-color: white; border: 2px solid #ffd700; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 2px 2px 12px rgba(0,0,0,0.1);
        }
        .ebook-title { color: #856404 !important; font-weight: 900; font-size: 1.5rem; margin-bottom: 10px; }
        .ebook-plot { color: #000000 !important; line-height: 1.6; font-size: 1.1rem; }
        
        /* METRICHE */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }
        .stMetric { background-color: white !important; border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE MEMORIA (PERSISTENZA)
# ==============================================================================
if 'data' not in st.session_state: st.session_state.data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None
if 'kw' not in st.session_state: st.session_state.kw = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'suggested_kws' not in st.session_state: st.session_state.suggested_kws = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING (PARALLELO CON BSR ANALYST)
# ==============================================================================
def get_amazon_data(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    api_key = "5a93911a587c4aff8d8dc7f2af9ea0db"
    
    def fetch(p):
        url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={p}"
        ant_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={api_key}&browser=true&proxy_type=residential"
        try:
            r = requests.get(ant_url, timeout=30)
            return r.text if r.status_code == 200 else None
        except: return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        pages = list(executor.map(fetch, range(1, 6)))
    
    results = []
    seen = set()
    for html in pages:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for item in items:
            title_el = item.h2
            title = title_el.text.strip() if title_el else ""
            if not title or title in seen: continue
            
            text = item.get_text(separator=' ').lower()
            bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', text) or re.search(r'#([0-9.,]+)\s*in', text)
            bsr = bsr_match.group(1).replace('.', '').replace(',', '') if bsr_match else "N/D"
            
            is_self = "Sì (Self-Pub)" if any(x in text for x in ['independently', 'kdp', 'indipendente', 'createspace']) else "Tradizionale"
            
            pw, pf = item.find('span', 'a-price-whole'), item.find('span', 'a-price-fraction')
            try:
                price = float(f"{pw.text.replace(',','').replace('.','')}.{pf.text}") if pw and pf else 0.0
            except: price = 0.0
            
            if price > 0 or bsr != "N/D":
                seen.add(title)
                results.append({"Titolo Analizzato": title, "Prezzo": price, "BSR": bsr, "Editore": is_self})
            
            if len(results) >= 50: break
            
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR (GENERAZIONE KEYWORD & ANALISI)
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 11.1")
    if st.button("🔄 RESET"):
        st.session_state.data = None
        st.session_state.suggestions = None
        st.session_state.suggested_kws = ""
        st.rerun()
    
    st.markdown("---")
    # Generi inclusi con Test Prep
    genere = st.selectbox("Seleziona Genere", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Test Prep", "Religioso", "Spirituale", "Meditazione", "Business", "Romanzo Rosa", "Thriller", "Fantasy", "Fantascienza", "Psicologia", "Biografia", "Ricettario"])
    nicchia = st.text_input("Sotto-nicchia specifica")
    target = st.text_input("Target Lettore")
    
    if st.button("🔍 GENERA KEYWORD SPECIFICHE"):
        if not nicchia or not target:
            st.error("Inserisci nicchia e target!")
        else:
            with st.spinner("Generazione..."):
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                # Prompt migliorato per keyword specifiche
                prompt_kw = f"Agisci come esperto SEO Amazon. Genera 5 keyword long-tail CHIRURGICHE e SPECIFICHE per KDP. Nicchia: {nicchia}, Genere: {genere}, Target: {target}. Focalizzati su termini ad alto intento d'acquisto. Separale con virgola."
                kw_ai = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_kw}]).choices[0].message.content
                st.session_state.suggested_kws = kw_ai

    if st.session_state.suggested_kws:
        st.info(f"Keyword Suggerite: {st.session_state.suggested_kws}")
        kw_selezionata = st.text_input("Keyword finale da analizzare:", value=st.session_state.suggested_kws.split(',')[0].strip())
        
        if st.button("🚀 ANALIZZA MERCATO", type="primary"):
            with st.spinner("Analisi profonda in corso..."):
                df = get_amazon_data("Italia", kw_selezionata)
                
                if not df.empty:
                    st.session_state.data = df
                    st.session_state.kw = kw_selezionata
                    
                    avg_p = df['Prezzo'].mean()
                    indie_r = (len(df[df['Editore'] == "Sì (Self-Pub)"]) / len(df)) * 100
                    score = 40 + (30 if avg_p > 12.5 else 0) + (30 if indie_r > 40 else 0)
                    st.session_state.score = score
                    
                    if score >= 60:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        # PROMPT POTENZIATO PER TITOLI E TRAME ATTINENTI
                        prompt_book = f"""Agisci come un esperto KDP Publishing Strategist. L'analisi per la keyword '{kw_selezionata}' (Genere: {genere}) è POSITIVA. 
                        Genera 3 proposte di libri UNICI e SPECIFICI che trattino approfonditamente l'argomento della keyword cercata. 
                        I titoli devono essere magnetici (Titolo Principale + Sottotitolo descrittivo) e le trame devono spiegare esattamente il valore aggiunto del libro per il lettore target.
                        Formato obbligatorio: TITOLO: [testo] | TRAMA: [testo]. Non aggiungere altro."""
                        sugg = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_book}]).choices[0].message.content
                        st.session_state.suggestions = sugg
                    else:
                        st.session_state.suggestions = "NEGATIVE"
                else:
                    st.error("⚠️ Nessun dato trovato. Prova una keyword meno specifica.")

# ==============================================================================
# 5. RISULTATI: ANALISI DELLE NICCHIE PROFITTEVOLI
# ==============================================================================
if st.session_state.data is not None:
    # TITOLO DEL PROGRAMMA
    st.markdown("<div class='program-title'>Analisi delle Nicchie Profittevoli</div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='white-title'>Analisi per: {st.session_state.kw.upper()}</div>", unsafe_allow_html=True)
    
    # Visualizzazione Tabella Dati (Minimo 20 titoli)
    st.dataframe(st.session_state.data, use_container_width=True, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.data['Prezzo'].mean():.2f} €")
    indie_p = (len(st.session_state.data[st.session_state.data['Editore'] == "Sì (Self-Pub)"]) / len(st.session_state.data)) * 100
    c2.metric("Indie Ratio", f"{int(indie_p)}%")
    c3.metric("Score Nicchia", f"{st.session_state.score}/100")

    if st.session_state.suggestions == "NEGATIVE":
        st.warning("⚠️ Score basso (<60). Nicchia troppo competitiva. Suggerimenti non generati.")
    elif st.session_state.suggestions:
        st.success(f"✅ ANALISI POSITIVA! Ecco i migliori angoli di attacco per '{st.session_state.kw}':")
        
        # LOGICA DI STAMPA ROBUSTA
        blocks = st.session_state.suggestions.split("TITOLO:")
        for block in blocks[1:]:
            if "|" in block:
                parts = block.split("|")
                title_final = parts[0].strip()
                plot_final = parts[1].replace('TRAMA:', '').replace('Trama:', '').strip()
                
                st.markdown(f"""
                <div class="ebook-card">
                    <div class="ebook-title">📘 {title_final}</div>
                    <div class="ebook-plot"><b>Trame e Strategia di Contenuto:</b> {plot_final}</div>
                </div>
                """, unsafe_allow_html=True)
