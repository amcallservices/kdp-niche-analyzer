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
        .white-title { color: white !important; font-size: 2.5rem !important; font-weight: 800; margin-bottom: 20px; }

        /* CORPO ANALISI: TESTO NERO */
        .stMarkdown p, .stMarkdown li, .stMarkdown span, [data-testid="stMetricLabel"] p { 
            color: #000000 !important; font-weight: 500;
        }
        
        /* BOX E CARDS */
        .explanation-box {
            background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; border-radius: 10px; color: black !important;
        }
        .ebook-card {
            background-color: white; border: 2px solid #ffd700; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        }
        .ebook-title { color: #856404 !important; font-weight: 900; font-size: 1.3rem; }
        .ebook-plot { color: black !important; margin-top: 10px; }
        
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
# 3. MOTORE DI SCRAPING (PARALLELO)
# ==============================================================================
def get_amazon_data(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    api_key = "5a93911a587c4aff8d8dc7f2af9ea0db"
    
    def fetch(p):
        url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={p}"
        ant_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(url)}&x-api-key={api_key}&browser=false"
        try:
            r = requests.get(ant_url, timeout=20)
            return r.text if r.status_code == 200 else None
        except: return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        # Analizziamo più pagine per garantire almeno 20 risultati validi
        pages = list(executor.map(fetch, range(1, 6)))
    
    results = []
    seen = set()
    for html in pages:
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        for item in soup.find_all('div', {'data-component-type': 's-search-result'}):
            title = item.h2.text.strip() if item.h2 else ""
            if not title or title in seen: continue
            
            text = item.get_text(separator=' ').lower()
            # Regex BSR migliorata per catturare diverse varianti (n. 123 o #123)
            bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', text) or re.search(r'#([0-9.,]+)\s*in', text)
            bsr = bsr_match.group(1).replace('.', '').replace(',', '') if bsr_match else "N/D"
            
            is_self = "Sì (Self-Pub)" if any(x in text for x in ['independently', 'kdp', 'indipendente']) else "Tradizionale"
            
            pw, pf = item.find('span', 'a-price-whole'), item.find('span', 'a-price-fraction')
            price = float(f"{pw.text.replace(',','').replace('.','')}.{pf.text}") if pw and pf else 0.0
            
            if price > 0:
                seen.add(title)
                results.append({"Titolo Analizzato": title, "Prezzo": price, "BSR": bsr, "Editore": is_self})
            
            if len(results) >= 50: break # Limite massimo per performance
            
    return pd.DataFrame(results)

# ==============================================================================
# 4. SIDEBAR (LOGICA GENERAZIONE KEYWORD & ANALISI)
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 11.1")
    if st.button("🔄 RESET"):
        st.session_state.data = None
        st.session_state.suggestions = None
        st.session_state.suggested_kws = ""
        st.rerun()
    
    st.markdown("---")
    # Generi con "Test Prep" incluso
    genere = st.selectbox("Seleziona Genere", ["Saggio Scientifico", "Quiz Scientifico", "Manuale Tecnico", "Test Prep", "Religioso", "Spirituale", "Meditazione", "Business", "Romanzo Rosa", "Thriller", "Fantasy", "Fantascienza", "Psicologia", "Biografia", "Ricettario"])
    nicchia = st.text_input("Sotto-nicchia specifica")
    target = st.text_input("Target Lettore")
    
    # 2) Generazione Keyword prima dell'analisi
    if st.button("🔍 GENERA KEYWORD SPECIFICHE"):
        if not nicchia or not target:
            st.error("Inserisci nicchia e target per generare keyword!")
        else:
            with st.spinner("Generazione in corso..."):
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt_kw = f"Agisci come esperto SEO Amazon. Genera una lista di 5 keyword long-tail specifiche per la nicchia '{nicchia}' (Genere: {genere}) rivolta a '{target}'. Separale con virgole."
                kw_ai = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt_kw}]
                ).choices[0].message.content
                st.session_state.suggested_kws = kw_ai

    if st.session_state.suggested_kws:
        st.info(f"Keyword Suggerite: {st.session_state.suggested_kws}")
        kw_selezionata = st.text_input("Keyword da analizzare (copia una delle precedenti o scrivine una):", value=st.session_state.suggested_kws.split(',')[0])
        
        if st.button("🚀 ANALIZZA MERCATO", type="primary"):
            with st.spinner("Analisi profonda in corso..."):
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                
                df = get_amazon_data("Italia", kw_selezionata)
                
                if not df.empty and len(df) >= 20:
                    st.session_state.data = df
                    st.session_state.kw = kw_selezionata
                    
                    # Calcolo metriche
                    avg_p = df['Prezzo'].mean()
                    indie_r = (len(df[df['Editore'] == "Sì (Self-Pub)"]) / len(df)) * 100
                    score = 40 + (30 if avg_p > 12.5 else 0) + (30 if indie_r > 40 else 0)
                    st.session_state.score = score
                    
                    # 1) Generazione Titoli e Trame per stesura libro (Analisi Positiva)
                    if score >= 60:
                        prompt_book = f"Analisi positiva per la keyword '{kw_selezionata}'. Suggerisci 3 titoli accattivanti e 3 trame strutturate per scrivere un libro di successo in questa nicchia ({genere}). Formato: TITOLO: [testo] | TRAMA: [testo]"
                        sugg = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt_book}]
                        ).choices[0].message.content
                        st.session_state.suggestions = sugg
                    else:
                        st.session_state.suggestions = "NEGATIVE"
                elif not df.empty and len(df) < 20:
                    st.warning("Trovati meno di 20 libri. L'analisi potrebbe non essere accurata.")
                    st.session_state.data = df
                    st.session_state.score = 30
                else:
                    st.error("⚠️ Nessun dato trovato. Riprova con una keyword meno specifica.")

# ==============================================================================
# 5. RISULTATI (MOSTRA TITOLI ANALIZZATI & BSR)
# ==============================================================================
if st.session_state.data is not None:
    st.markdown(f"<div class='white-title'>Analisi per: {st.session_state.kw.upper()}</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="explanation-box">
        <b>💡 Guida ai Dati (Testo Nero):</b><br>
        • <b>BSR (Best Seller Rank):</b> Mostra la velocità di vendita attuale su Amazon. Più è basso, più il titolo vende.<br>
        • <b>Titoli Analizzati:</b> Elenco dei libri trovati per questa specifica keyword (Minimo 20 per validità statistica).<br>
        • <b>Opportunity Score:</b> Valutazione della profittabilità della nicchia.
    </div>
    """, unsafe_allow_html=True)
    
    # 4) Mostra titoli analizzati (Sempre almeno 20 se disponibili)
    st.dataframe(st.session_state.data, use_container_width=True, hide_index=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{st.session_state.data['Prezzo'].mean():.2f} €")
    indie_p = (len(st.session_state.data[st.session_state.data['Editore'] == "Sì (Self-Pub)"]) / len(st.session_state.data)) * 100
    c2.metric("Indie Ratio", f"{int(indie_p)}%")
    c3.metric("Score Nicchia", f"{st.session_state.score}/100")

    if st.session_state.suggestions == "NEGATIVE":
        st.warning("⚠️ Score insufficiente (<60). La nicchia non è consigliata per la stesura di un nuovo libro.")
    elif st.session_state.suggestions:
        st.success("✅ OTTIMA OPPORTUNITÀ! Ecco la struttura per la stesura del tuo nuovo libro:")
        for item in st.session_state.suggestions.split("\n"):
            if "|" in item:
                parts = item.split("|")
                t = parts[0].replace('TITOLO:', '').strip()
                p = parts[1].replace('TRAMA:', '').strip()
                st.markdown(f"""
                <div class="ebook-card">
                    <div class="ebook-title">📘 {t}</div>
                    <div class="ebook-plot"><b>Sinossi per la stesura:</b> {p}</div>
                </div>
                """, unsafe_allow_html=True)
