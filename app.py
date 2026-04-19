import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 1. DESIGN SYSTEM: CONTRASTO ALTO (BIANCO/NERO)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 11.0", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
        /* Sfondo scuro per sidebar e titoli principali */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; min-width: 450px !important;
        }
        
        /* TESTO BIANCO: Sidebar e Intestazione Risultati */
        section[data-testid="stSidebar"] * { color: white !important; }
        .white-title { color: white !important; font-size: 2.5rem !important; font-weight: 800; margin-bottom: 20px; }

        /* TESTO NERO: Tutto il contenuto dell'analisi */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, [data-testid="stMetricLabel"] p { 
            color: #000000 !important; font-weight: 500;
        }
        
        /* CARDS E BOX */
        .explanation-box {
            background-color: #f0f2f6; border: 1px solid #d1d5db; padding: 20px; border-radius: 10px; color: black !important;
        }
        .ebook-card {
            background-color: white; border: 2px solid #ffd700; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        }
        .ebook-title { color: #856404 !important; font-weight: 900; font-size: 1.3rem; }
        .ebook-plot { color: black !important; margin-top: 10px; }
        
        /* METRICHE */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }
        .stMetric { background-color: white !important; border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI MEMORIA (PER EVITARE CHE L'ANALISI SPARISCA)
# ==============================================================================
if 'data' not in st.session_state: st.session_state.data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None
if 'kw' not in st.session_state: st.session_state.kw = ""

# ==============================================================================
# 3. MOTORE DI RICERCA (VELOCE E DIRETTO)
# ==============================================================================
def get_amazon_data(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    api_key = "5a93911a587c4aff8d8dc7f2af9ea0db" # ScrapingAnt
    
    def fetch(p):
        url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={p}"
        ant_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={api_key}&browser=false"
        try:
            r = requests.get(ant_url, timeout=20)
            return r.text if r.status_code == 200 else None
        except: return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        pages = list(executor.map(fetch, range(1, 9)))
    
    results = []
    seen = set()
    for html in pages:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        for item in soup.find_all('div', {'data-component-type': 's-search-result'}):
            title = item.h2.text.strip() if item.h2 else ""
            if not title or title in seen: continue
            
            # Estrazione BSR e Self-Pub
            text = item.get_text(separator=' ').lower()
            bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', text) or re.search(r'#([0-9.,]+)\s*in', text)
            bsr = bsr_match.group(1).replace('.', '').replace(',', '') if bsr_match else "N/D"
            
            is_self = "Sì (Self-Pub)" if any(x in text for x in ['independently', 'kdp', 'indipendente']) else "Tradizionale"
            
            # Prezzo
            pw = item.find('span', 'a-price-whole')
            pf = item.find('span', 'a-price-fraction')
            price = float(f"{pw.text.replace(',','').replace('.','')}.{pf.text}") if pw and pf else 0.0
            
            if price > 0:
                seen.add(title)
                results.append({"Titolo": title, "Prezzo": price, "BSR": bsr, "Editore": is_self})
            if len(results) >= 50: break
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR (14 GENERI E INPUT)
# ==============================================================================
with st.sidebar:
    st.title("🛡️ KDP ANALYZER 11.0")
    if st.button("🔄 RESET"):
        st.session_state.data = None
        st.rerun()
    
    st.markdown("---")
    genere = st.selectbox("Seleziona Genere", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Religioso", "Spirituale", "Meditazione", "Business", "Romanzo Rosa", "Thriller", "Fantasy", "Fantascienza", "Psicologia", "Biografia", "Ricettario"])
    nicchia = st.text_input("Sotto-nicchia (es. Yoga per anziani)")
    target = st.text_input("Target (es. Pensionati)")
    
    if st.button("🚀 ANALIZZA MERCATO", type="primary"):
        with st.spinner("Scansione di 50+ libri in corso..."):
            # Generazione keyword semplice e diretta
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            kw_res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"Genera una keyword KDP per {genere} nicchia {nicchia} target {target}. Rispondi solo con la keyword."}]
            ).choices[0].message.content
            
            df = get_amazon_data("Italia", kw_res)
            st.session_state.data = df
            st.session_state.kw = kw_res
            
            # Calcolo Score e Suggerimenti
            avg_p = df['Prezzo'].mean()
            indie_r = (len(df[df['Editore'] == "Sì (Self-Pub)"]) / len(df)) * 100
            score = 40 + (30 if avg_p > 12 else 0) + (30 if indie_r > 40 else 0)
            st.session_state.score = score
            
            if score >= 60:
                sugg = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": f"Per la keyword '{kw_res}' e genere '{genere}', suggerisci 3 titoli e 3 brevi trame. Formato: TITOLO: [testo] | TRAMA: [testo]"}]
                ).choices[0].message.content
                st.session_state.suggestions = sugg
            else:
                st.session_state.suggestions = "NEGATIVE"

# ==============================================================================
# 5. RISULTATI (PULITI E PERSISTENTI)
# ==============================================================================
if st.session_state.data is not None:
    st.markdown(f"<div class='white-title'>Risultati per: {st.session_state.kw.upper()}</div>", unsafe_allow_html=True)
    
    # SPIEGAZIONI (TESTO NERO)
    st.markdown("""
    <div class="explanation-box">
        <b>📘 Cosa stiamo analizzando:</b><br>
        • <b>BSR (Best Sellers Rank):</b> Indica quanto vende il libro. Più è basso, più copie vende al giorno.<br>
        • <b>Indie Ratio:</b> La percentuale di autori Self-Publishing. Se è alta, c'è molta opportunità per te.<br>
        • <b>Opportunity Score:</b> Valutazione della nicchia da 0 a 100.
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(st.session_state.data, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.data['Prezzo'].mean():.2f} €")
    indie_p = (len(st.session_state.data[st.session_state.data['Editore'] == "Sì (Self-Pub)"]) / len(st.session_state.data)) * 100
    c2.metric("Indie Ratio", f"{int(indie_p)}%")
    c3.metric("Opportunity Score", f"{st.session_state.score}/100")

    if st.session_state.suggestions == "NEGATIVE":
        st.error("Nicchia troppo competitiva o poco profittevole. Prova a cambiare parametri.")
    elif st.session_state.suggestions:
        st.success("✅ OTTIMA OPPORTUNITÀ! Ecco cosa potresti scrivere:")
        for item in st.session_state.suggestions.split("\n"):
            if "|" in item:
                t, p = item.split("|")
                st.markdown(f"""
                <div class="ebook-card">
                    <div class="ebook-title">{t.replace('TITOLO:', '').strip()}</div>
                    <div class="ebook-plot">{p.replace('TRAMA:', '').strip()}</div>
                </div>
                """, unsafe_allow_html=True)
