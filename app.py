import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import openai

# ==============================================================================
# 1. DESIGN SYSTEM ELITE (ETERNAL SIDEBAR & GHOST UI)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 8.2", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] { 
            background-color: #0d1117 !important; 
            border-right: 1px solid #30363d;
            min-width: 480px !important;
        }

        .stMetric { background-color: #ffffff !important; border-left: 10px solid #238636 !important; padding: 20px !important; border-radius: 12px !important; }
        [data-testid="stMetricValue"] { color: #238636 !important; font-weight: 800 !important; }

        .ebook-suggestion-card {
            background-color: #0b0e14 !important; border: 2px solid #ffd700 !important; 
            padding: 25px !important; border-radius: 15px !important; margin-bottom: 20px !important;
        }
        .ebook-title { color: #ffd700 !important; font-size: 1.4rem !important; font-weight: 900 !important; display: block; margin-bottom: 8px; }
        .ebook-plot { color: #e6edf3 !important; line-height: 1.7 !important; font-size: 1rem !important; }
        
        .negative-verdict {
            background-color: #3d0a0a !important; color: #ff6b6b !important; padding: 30px; border-radius: 15px;
            text-align: center; font-weight: 900; font-size: 1.8rem; margin: 30px 0; border: 2px solid #ff6b6b;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONFIGURAZIONE & PERSISTENZA (CRUCIALE)
# ==============================================================================
ANT_API_KEY = "5a93911a587c4aff8d8dc7f2af9ea0db"

try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    API_READY = True
except:
    st.error("⚠️ OpenAI API Key non trovata nei Secret.")
    API_READY = False

# Inizializziamo il "cassetto della memoria" per non perdere i dati
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'ebook_ideas' not in st.session_state: st.session_state.ebook_ideas = ""
if 'score' not in st.session_state: st.session_state.score = 0
if 'kw_active' not in st.session_state: st.session_state.kw_active = ""
if 'kw_logic' not in st.session_state: st.session_state.kw_logic = ""

# ==============================================================================
# 3. MOTORE DI SCRAPING TURBO (JS OFF + SNIPER 40)
# ==============================================================================
def run_sniper_scan(mkt, keyword):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    unique_results = []
    seen_titles = set()
    
    p_bar = st.progress(0)
    for page in range(1, 7): 
        if len(unique_results) >= 40: break
        
        target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks&page={page}"
        # browser=false (HTML puro) per velocità e risparmio crediti
        api_url = f"https://api.scrapingant.com/v2/general?url={urllib.parse.quote(target_url)}&x-api-key={ANT_API_KEY}&browser=false&proxy_type=residential"
        
        try:
            response = requests.get(api_url, timeout=25)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                title_elem = item.h2.text.strip() if item.h2 else "N/A"
                if title_elem in seen_titles or title_elem == "N/A": continue
                
                full_text = item.get_text(separator=' ').lower()
                if not any(x in full_text for x in ['pagine', 'kindle', 'copertina', 'formato']): continue
                
                # Prezzo
                price = 0.0
                p_whole = item.find('span', 'a-price-whole')
                p_frac = item.find('span', 'a-price-fraction')
                if p_whole and p_frac:
                    price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}")
                
                if price > 0:
                    seen_titles.add(title_elem)
                    bsr = 0
                    bsr_match = re.search(r'n\.\s*([0-9.,]+)\s*in', full_text)
                    if bsr_match: bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
                    
                    unique_results.append({
                        "Preview": item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else "",
                        "Titolo": title_elem, "Prezzo": price, "BSR": bsr if bsr > 0 else "N/D", 
                        "Self": "Sì" if any(x in full_text for x in ['independently', 'kdp', 'createspace']) else "No"
                    })
                if len(unique_results) >= 40: break
            p_bar.progress(len(unique_results) / 40)
        except: continue
    p_bar.empty()
    return pd.DataFrame(unique_results)

# ==============================================================================
# 4. SIDEBAR FISSA: DEEP CONCEPT
# ==============================================================================
with st.sidebar:
    st.title("🛡️ STRATEGY LAB 8.2")
    if st.button("🔄 RESET ANALISI"):
        for key in ['results_df', 'ebook_ideas', 'kw_active', 'kw_logic', 'score']:
            st.session_state[key] = None if key != 'score' else 0
        st.rerun()

    st.markdown("---")
    st.subheader("📝 Descrivi il tuo Progetto")
    
    # NUOVI CAMPI DETTAGLIATI
    p_type = st.selectbox("Genere / Formato", ["Saggio Scientifico", "Manuale Tecnico", "Business", "Romanzo", "Ricettario", "Spirituale"])
    p_desc = st.text_area("Cosa vuoi scrivere esattamente?", placeholder="es. Un manuale per architetti che spiega come usare l'AI nel design...", height=100)
    p_target = st.text_input("Target (Chi lo leggerà?)", placeholder="es. Architetti junior 25-35 anni")
    p_angle = st.text_input("Angolo Unico (Perché è diverso?)", placeholder="es. Spiegazioni semplici senza gergo tecnico")
    p_tone = st.selectbox("Tono di Voce", ["Professionale", "Amichevole", "Accademico", "Motivazionale"])
    
    if st.button("🧠 GENERA KEYWORD CHIRURGICA", type="primary") and API_READY:
        prompt = f"""
        Direttore Marketing KDP. Genera UNA keyword Long-Tail per questo progetto:
        - GENERE: {p_type}
        - DESCRIZIONE: {p_desc}
        - TARGET: {p_target}
        - ANGOLO UNICO: {p_angle}
        - TONO: {p_tone}
        Rispondi ESCLUSIVAMENTE nel formato: KEYWORD: [testo] | LOGICA: [testo]
        """
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        st.session_state.kw_active = res.split("KEYWORD:")[1].split("|")[0].strip()
        st.session_state.kw_logic = res.split("LOGICA:")[1].strip()

    if st.session_state.kw_active:
        st.success(f"**Strategia AI:** {st.session_state.kw_logic}")
        final_q = st.text_input("Keyword da analizzare:", value=st.session_state.kw_active)
        mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
        run_btn = st.button("🚀 LANCIA ANALISI SNIPER", use_container_width=True)

# ==============================================================================
# 5. LOGICA DI ESECUZIONE (SALVATAGGIO DATI)
# ==============================================================================
if 'run_btn' in locals() and run_btn and API_READY:
    with st.spinner("Analisi Sniper in corso..."):
        df = run_sniper_scan(mkt, final_q)
        if not df.empty:
            st.session_state.results_df = df
            avg_p = df['Prezzo'].mean()
            self_r = (len(df[df['Self'] == "Sì"]) / len(df)) * 100
            st.session_state.score = 40 + (30 if avg_p > 13.5 else 0) + (30 if self_r > 40 else 0)
            
            if st.session_state.score >= 60:
                p_ebook = f"Analisi POSITIVA per '{final_q}'. Genera 3 titoli e 3 trame eBook. Target: {p_target}. Descrizione: {p_desc}. Formato: TITOLO: [testo] | TRAMA: [testo]"
                st.session_state.ebook_ideas = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p_ebook}]).choices[0].message.content
            else:
                st.session_state.ebook_ideas = "NEGATIVE"

# ==============================================================================
# 6. DASHBOARD (VISUALIZZAZIONE PERSISTENTE)
# ==============================================================================
# Questa parte è FUORI dal blocco "if run_btn", così i risultati restano visibili sempre!
if st.session_state.results_df is not None:
    st.header(f"📊 Sniper Report: {final_q.upper()}")
    
    st.dataframe(st.session_state.results_df, column_config={"Preview": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns(2)
    c1.metric("Prezzo Medio", f"{st.session_state.results_df['Prezzo'].mean():.2f} €")
    c2.metric("Indie Ratio", f"{int((len(st.session_state.results_df[st.session_state.results_df['Self'] == 'Sì']) / len(st.session_state.results_df)) * 100)}%")

    if st.session_state.score >= 60:
        st.success(f"✅ ANALISI POSITIVA ({st.session_state.score}/100)")
        st.header("🎯 Strategia Editoriale eBook")
        ebooks = st.session_state.ebook_ideas.split("TITOLO:")
        for eb in ebooks[1:]:
            parts = eb.split("| TRAMA:")
            if len(parts) > 1:
                st.markdown(f'<div class="ebook-suggestion-card"><span class="ebook-title">📘 {parts[0].strip()}</span><p class="ebook-plot">{parts[1].strip()}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="negative-verdict">❌ ANALISI NEGATIVA ({st.session_state.score}/100)</div>', unsafe_allow_html=True)
        st.warning("⚠️ Nicchia sconsigliata. Prova a rigenerare la keyword cambiando angolo d'attacco.")
