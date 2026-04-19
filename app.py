import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 1. DESIGN SYSTEM: CONTRASTO DEFINITIVO (TITOLI BIANCHI / TESTO NERO)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 10.0", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        /* UI GHOST: RIMOZIONE TOTALE ELEMENTI STREAMLIT */
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR FISSA E TESTO BIANCO */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; 
            border-right: 1px solid #30363d; 
            min-width: 480px !important;
        }
        section[data-testid="stSidebar"] * { 
            color: #ffffff !important; 
        }
        section[data-testid="stSidebar"] h1 { font-size: 1.8rem !important; }

        /* HEADER RISULTATI BIANCO (LOGICA BLINDATA) */
        .white-header {
            color: #ffffff !important;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            margin: 25px 0px !important;
            display: block;
        }

        /* METRICHE: SFONDO BIANCO E TESTO NERO */
        [data-testid="stMetricLabel"] p { color: #000000 !important; font-weight: bold !important; font-size: 1.1rem !important; }
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 900 !important; }
        .stMetric { background-color: #ffffff !important; border: 2px solid #dee2e6 !important; padding: 15px !important; border-radius: 10px !important; }

        /* CONTENUTI IN NERO ASSOLUTO SU FONDO CHIARO */
        .explanation-box {
            background-color: #f8f9fa; border: 2px solid #ced4da; padding: 20px; 
            border-radius: 10px; color: #000000 !important; margin: 20px 0; font-size: 1rem;
        }
        .ebook-suggestion-card {
            background-color: #ffffff !important; border: 3px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .ebook-title { color: #856404 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 8px; }
        .ebook-plot { color: #000000 !important; line-height: 1.6 !important; font-size: 1.1rem !important; font-weight: 500; }
        
        /* FORZATURA TESTO NERO SUI RISULTATI */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown div { color: #000000 !important; }
        
        /* ECCEZIONE PER CLASSI BIANCHE */
        .white-header, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] label { color: white !important; }
        
        /* TABELLE */
        .stDataFrame { border: 1px solid #dee2e6; border-radius: 10px; background-color: white; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. API & STATO PERSISTENTE (IRON MEMORY)
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ Chiave OpenAI non trovata nei Secret di Streamlit.")
    API_READY = False

# Inizializzazione Session State
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'final_keyword' not in st.session_state: st.session_state.final_keyword = ""
if 'kw_suggested' not in st.session_state: st.session_state.kw_suggested = None

# ==============================================================================
# 3. MOTORE PARALLELO TURBO (60+ LIBRI UNICI - JS OFF)
# ==============================================================================
def fetch_amazon_page(url):
    api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
    try:
        resp = requests.get(api_url, timeout=25)
        return resp.text if resp.status_code == 200 else None
    except: return None

def run_surgical_omniscanner(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    # Scansione estesa per trovare almeno 60 libri unici
    urls = [f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={i}" for i in range(1, 16)]
    
    results = []
    seen_titles = set()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        pages_content = list(executor.map(fetch_amazon_page, urls))
    
    for html in pages_content:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for item in items:
            if len(results) >= 60: break
            title = item.h2.text.strip() if item.h2 else "N/A"
            if title in seen_titles or title == "N/A": continue
            
            raw_text = item.get_text(separator=' ').lower()
            if not any(x in raw_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue

            # --- BSR DETECTION (Regex Profonda) ---
            bsr = 0
            bsr_patterns = [r'n\.\s*([0-9.,]+)\s*in', r'rank\s*#?\s*([0-9.,]+)', r'#([0-9.,]+)\s*in', r'posiziona\s*([0-9.,]+)']
            for p in bsr_patterns:
                m = re.search(p, raw_text)
                if m: 
                    bsr = int(m.group(1).replace('.', '').replace(',', ''))
                    break

            # --- SELF-PUB DETECTION ---
            is_self = "Tradizionale"
            if any(x in raw_text for x in ['independently', 'kdp', 'createspace', 'indipendente']):
                is_self = "Sì (Self-Pub)"

            # --- PREZZO ---
            price = 0.0
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            if p_w and p_f: price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}")
            
            if price > 0:
                seen_titles.add(title)
                results.append({
                    "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                    "Titolo": title, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", "Autore/Tipo": is_self
                })
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR FISSA: PRECISION COMMAND CENTER
# ==============================================================================
with st.sidebar:
    st.markdown("# 🛡️ STRATEGY LAB 10.0")
    if st.button("🔄 RESET ANALISI"):
        for k in ['results_df', 'ebook_ideas', 'score', 'final_keyword', 'kw_suggested']: st.session_state[k] = None
        st.rerun()

    st.markdown("---")
    
    # LISTA 14 GENERI
    p_type = st.selectbox("Genere / Formato", [
        "Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", 
        "Religioso / Teologico", "Spirituale / Esoterico", "Meditazione / Mindfulness", 
        "Business e Marketing", "Romanzo Rosa", "Thriller / Noir", 
        "Fantasy", "Fantascienza", "Manuale Psicologico", "Biografia", "Ricettario"
    ])
    
    p_niche = st.text_input("Sotto-Nicchia Specifica", placeholder="es. Yoga per principianti over 60")
    p_target = st.text_input("Identikit del Lettore", placeholder="es. Pensionati dinamici")
    p_angle = st.text_area("Angolo di Attacco / Unicità", placeholder="es. Spiegazioni pratiche senza termini tecnici", height=80)
    
    if st.button("🧠 GENERA KEYWORD CHIRURGICA", type="primary") and API_READY:
        prompt = f"""
        Agisci come esperto SEO Amazon. Genera UNA keyword LONG-TAIL chirurgica per:
        GENERE: {p_type} | NICCHIA: {p_niche} | TARGET: {p_target} | ANGOLO: {p_angle}.
        Rispondi solo ed esclusivamente: KEYWORD: [testo]
        """
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_suggested = res.split("KEYWORD:")[1].strip()

    if st.session_state.kw_suggested:
        kw_input = st.text_input("Keyword finale da analizzare:", value=st.session_state.kw_suggested)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        
        if st.button("🚀 LANCIA DEEP SCAN (60 LIBRI)", use_container_width=True):
            with st.spinner("⚡ Analisi parallela massiva in corso..."):
                df = run_surgical_omniscanner(mkt, kw_input)
                if not df.empty:
                    st.session_state.results_df = df
                    st.session_state.final_keyword = kw_input
                    avg_p = df['Prezzo'].mean()
                    indie_n = len(df[df['Autore/Tipo'].str.contains("Sì")])
                    st.session_state.score = 40 + (30 if avg_p > 13.5 else 0) + (30 if (indie_n/len(df)) > 0.4 else 0)
                    
                    if st.session_state.score >= 60:
                        p_eb = f"Analisi OK per '{kw_input}'. Genera 3 titoli e 3 trame. FORMATO: [PROPOSTA_START] TITOLO: [testo] | TRAMA: [testo] [PROPOSTA_END]"
                        st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_eb}]).choices[0].message.content
                    else: st.session_state.ebook_ideas = "NEGATIVE"

# ==============================================================================
# 5. DASHBOARD: VISUALIZZAZIONE PERSISTENTE (TITOLI BIANCHI / TESTO NERO)
# ==============================================================================
if st.session_state.results_df is not None:
    # HEADER BIANCO BLINDATO
    st.markdown(f"<div class='white-header'>📊 Report Mercato: {st.session_state.final_keyword.upper()}</div>", unsafe_allow_html=True)
    
    # GLOSSARIO IN NERO
    st.markdown("""
    <div class="explanation-box">
        <b>📘 Guida alla Strategia (Testo Nero):</b><br>
        • <b>BSR (Best Sellers Rank):</b> Classifica vendite. Più è basso, più il libro vende ogni giorno.<br>
        • <b>Indie Ratio:</b> Quota di autori indipendenti. Sopra il 40% indica spazio per te.<br>
        • <b>Opportunity Score:</b> Semaforo verde sopra 60 punti.
    </div>
    """, unsafe_allow_html=True)
    
    # TABELLA DATI
    st.dataframe(st.session_state.results_df, use_container_width=True, hide_index=True)
    
    # METRICHE
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    indie_count = len(st.session_state.results_df[st.session_state.results_df['Autore/Tipo'].str.contains('Sì')])
    c2.metric("Indie Ratio", f"{int((indie_count / len(st.session_state.results_df)) * 100)}%")
    c3.metric("Score Nicchia", f"{st.session_state.score}/100")

    # VERDETTO E PROPOSTE EBOOK
    if st.session_state.score >= 60:
        st.success("✅ ANALISI POSITIVA: Ecco le opportunità editoriali")
        proposte = st.session_state.ebook_ideas.split("[PROPOSTA_START]")
        for prop in proposte[1:]:
            if "[PROPOSTA_END]" in prop and "| TRAMA:" in prop:
                clean_prop = prop.split("[PROPOSTA_END]")[0]
                parts = clean_prop.split("| TRAMA:")
                t = parts[0].replace("TITOLO:", "").strip()
                p = parts[1].strip()
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {t}</span><p class="ebook-plot">{p}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown("<div class='negative-verdict' style='background-color:#fff5f5; color:#c92a2a; padding:20px; border-radius:10px; border:2px solid #ffc9c9; text-align:center; font-weight:bold;'>❌ ANALISI NEGATIVA: Nicchia poco profittevole o troppo competitiva.</div>", unsafe_allow_html=True)
        st.info("💡 Consiglio: Torna alla sidebar e rigenera la keyword cambiando Nicchia Specifica o Angolo d'Attacco.")
