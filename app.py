import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (SIDEBAR FISSA & DARK MODE)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 7.5", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded" # Forza l'espansione all'avvio
)

st.markdown("""
    <style>
        /* DISATTIVA IL PULSANTE PER CHIUDERE LA SIDEBAR */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        
        /* STILE SIDEBAR FISSA */
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; 
            border-right: 1px solid #30363d;
            min-width: 450px !important;
        }

        /* METRICHE */
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }
        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }

        /* GUIDA RISULTATI */
        .guide-box { background-color: #f0f6fc; border: 1px solid #d0d7de; padding: 20px; border-radius: 10px; color: #1f2328; margin-bottom: 25px; }

        /* EBOOK SUGGESTIONS CARD */
        .ebook-suggestion-card {
            background-color: #0b0e14 !important; border: 2px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
        }
        .ebook-title { color: #ffd700 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 8px; }
        .ebook-plot { color: #e6edf3 !important; line-height: 1.7 !important; font-size: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE API & SESSIONE
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ Configurazione OpenAI mancante nei Secret.")
    API_READY = False

if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""

# ==============================================================================
# 3. MOTORE DI SCAN (100 LIBRI UNICI)
# ==============================================================================
def run_unique_centurion_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    
    unique_results = []
    seen_titles = set()
    
    p_bar = st.progress(0)
    status_text = st.empty()
    
    for page in range(1, 15): 
        if len(unique_results) >= 100: break
        
        status_text.text(f"Scansione Pagina {page}... Libri unici: {len(unique_results)}/100")
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(target_url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
        
        try:
            response = requests.get(api_url, timeout=35)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                item_text = item.get_text().lower()
                if not any(x in item_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
                
                title_elem = item.h2.text.strip() if item.h2 else "N/A"
                if title_elem in seen_titles or title_elem == "N/A": continue
                
                seen_titles.add(title_elem)
                img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
                
                p_w = item.find('span', 'a-price-whole')
                p_f = item.find('span', 'a-price-fraction')
                price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
                
                bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', item_text)
                bsr = int(bsr_match.group(1).replace('.', '').replace(',', '')) if bsr_match else 0
                
                unique_results.append({
                    "Preview": img, "Titolo": title_elem, "Prezzo": price, 
                    "BSR": bsr, "Self": "Sì" if "independently" in item_text else "No"
                })
                if len(unique_results) >= 100: break
            
            p_bar.progress(len(unique_results) / 100)
        except: continue
        
    status_text.empty()
    p_bar.empty()
    return pd.DataFrame(unique_results)

# ==============================================================================
# 4. SIDEBAR FISSA (COMMAND CENTER)
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 7.5")
    st.caption("Sidebar Blindata - Solo Libri Unici")
    
    if st.button("🔄 RESET"):
        for key in ['results_df', 'ebook_ideas', 'kw_active']: 
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    st.markdown("---")
    genere = st.selectbox("Genere", ["Saggio", "Manuale", "Business", "Romanzo", "Psicologico", "Ricettario"])
    target = st.text_input("Target", placeholder="es. Ingegneri")
    dolore = st.text_input("Problema", placeholder="es. gestione tempo")
    sogno = st.text_input("Risultato", placeholder="es. produttività")
    
    if st.button("🧠 GENERA KEYWORD AI", type="primary"):
        p = f"Genera UNA keyword Long-Tail per '{genere}' rivolto a '{target}'. Dolore: {dolore}. Risposta: KEYWORD: [testo] | LOGICA: [testo]"
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()

    if 'kw_active' in st.session_state:
        final_q = st.text_input("Keyword finale:", value=st.session_state.kw_active)
    
    mkt = st.selectbox("Mercato", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    run_btn = st.button("🚀 ANALIZZA 100 LIBRI UNICI", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD & ANALISI
# ==============================================================================
if run_btn and API_READY:
    with st.spinner("Analisi massiva deduplicata in corso..."):
        df = run_unique_centurion_scan(mkt, final_q)
        if not df.empty:
            st.session_state.results_df = df
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13 else 0) + (30 if self_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_ebook = f"Genera 3 titoli e 3 trame (100 parole) per eBook basandoti su '{final_q}'. Formato: TITOLO: [testo] | TRAMA: [testo]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_ebook}]).choices[0].message.content

if st.session_state.results_df is not None:
    st.header(f"📊 Report: {final_q.upper()}")
    
    with st.expander("📖 Guida all'Analisi", expanded=True):
        st.markdown(f"""
        <div class="guide-box">
            <b>Analisi 100 Libri Unici:</b> Dati puliti senza ripetizioni pubblicitarie.<br><br>
            <b>Opportunity Score ({st.session_state.score}/100):</b> Valutazione della profittabilità.<br><br>
            <b>Indie Ratio:</b> Percentuale di spazio per autori indipendenti.
        </div>
        """, unsafe_allow_html=True)

    st.dataframe(st.session_state.results_df, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns(2)
    c1.metric("Punteggio Nicchia", f"{st.session_state.score}/100")
    c2.metric("Libri Unici Analizzati", f"{len(st.session_state.results_df)}")

    if st.session_state.score >= 60 and st.session_state.ebook_ideas:
        st.markdown("---")
        st.header("🎯 Suggerimenti eBook")
        ebooks = st.session_state.ebook_ideas.split("TITOLO:")
        for eb in ebooks[1:]:
            parts = eb.split("| TRAMA:")
            if len(parts) > 1:
                st.markdown(f"""
                <div class="ebook-suggestion-card">
                    <span class="ebook-title">📘 {parts[0].strip()}</span>
                    <p class="ebook-plot">{parts[1].strip()}</p>
                </div>
                """, unsafe_allow_html=True)
