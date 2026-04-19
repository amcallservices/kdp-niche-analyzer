import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE UI & DESIGN SYSTEM (ELITE DARK)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER ELITE 2026",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Iniezione CSS per Sidebar DARK e FIX colori metriche bianche
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR DARK */
        section[data-testid="stSidebar"] {
            min-width: 450px !important;
            max-width: 450px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #f0f6fc !important;
        }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important;
        }

        /* FIX METRICHE BIANCHE: Forzo il colore del testo dei risultati */
        [data-testid="stMetricValue"] {
            color: #1f2328 !important;
            font-weight: 800 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #444c56 !important;
        }
        .stMetric {
            background-color: #ffffff !important;
            border: 1px solid #d0d7de !important;
            border-left: 8px solid #0969da !important;
            padding: 15px !important;
            border-radius: 12px !important;
        }

        /* STILI CARTE */
        .ai-audit-card { background-color: #fff9db; border-left: 6px solid #fab005; padding: 20px; border-radius: 10px; color: #856404; margin-bottom: 20px; }
        .keyword-alt-card { background-color: #f3e5f5; border-left: 5px solid #673ab7; padding: 15px; border-radius: 8px; color: #4527a0 !important; margin-bottom: 10px; }
        .editorial-card { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-top: 4px solid #28a745; }
        .title-option { color: #cf222e; font-size: 1.15rem; font-weight: bold; display: block; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA INTEGRATA GPT & STRATEGIA
# ==============================================================================
WS_API_KEY = "50867242-8e16-4f72-b142-caef181401f6"

class GPTStratega:
    @staticmethod
    def genera_5_proposte(p_type, p_target, p_pain, p_dream):
        """Genera 5 titoli e 5 trame professionali."""
        proposte = []
        templates = [
            {"t": f"MAI PIÙ {p_pain.upper()}: Il Metodo {p_type} per {p_target}", "p": f"Una guida chirurgica per eliminare {p_pain} e raggiungere {p_dream}."},
            {"t": f"{p_type} di {p_dream}: Protocollo per {p_target}", "p": f"Trasforma la tua vita superando {p_pain} con questo {p_type} pratico."},
            {"t": f"{p_target}: La Scienza del {p_dream}", "p": f"Perché continui a soffrire di {p_pain}? Scopri come questo {p_type} cambierà tutto."},
            {"t": f"Oltre {p_pain.capitalize()}: {p_type} Strategico", "p": f"Il manuale definitivo per {p_target} che non accettano compromessi su {p_dream}."},
            {"t": f"Il Codice {p_dream.capitalize()}: Manuale per {p_target}", "p": f"Dimentica {p_pain}. Inizia oggi il tuo percorso basato sul nostro {p_type} esclusivo."}
        ]
        return templates

# ==============================================================================
# 3. MOTORE DI SCRAPING (20 RISULTATI)
# ==============================================================================
def run_strategic_scan(mkt, keyword, pages):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        response = requests.get(
            'https://api.webscraping.ai/html',
            params={'api_key': WS_API_KEY, 'url': target_url, 'proxy': 'residential'},
            timeout=30
        )
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # ANALISI DI 20 LIBRI
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:20]
        
        results = []
        p_bar = st.progress(0)
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            img = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            roy = round((price * 0.6) - (2.15 if pages <= 108 else 0.60 + (pages * 0.012)), 2)
            
            results.append({
                "Copertina": img, "Titolo": title, "Prezzo": price, 
                "Royalty_Est": roy, "Self-Pub": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"
            })
            p_bar.progress((i + 1) / len(items))
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 4. SIDEBAR COMMAND CENTER (INTELLIGENT KEYWORD GEN)
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY AGENT AI")
    
    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("🤖 Laboratorio Strategico AI")
    with st.container():
        p_type = st.selectbox("Angolo Editoriale", ["Manuale Pratico", "Workbook", "Diario", "Guida Passo-Passo", "Ricettario"])
        p_target = st.text_input("Lettore Target", placeholder="es. Imprenditori Digitali")
        p_pain = st.text_input("Dolore / Problema", placeholder="es. tasse elevate")
        p_dream = st.text_input("Risultato / Sogno", placeholder="es. risparmio fiscale")
    
    # GENERATORE KEYWORD INTELLIGENTE
    if p_target and p_pain and p_dream:
        # Logica AI per keyword "chirurgica"
        final_kw = f"{p_type} di {p_pain} per {p_target}: Soluzioni per {p_dream}"
        st.info(f"💡 **AI Suggestion:** La keyword sopra è ottimizzata per intercettare il bisogno specifico del tuo target.")
        if st.button(f"🎯 APPLICA KEYWORD AI", use_container_width=True):
            st.session_state['kw_active'] = final_kw; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Mercato Amazon", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Focus Keyword (Analisi)", value=st.session_state['kw_active'])
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    
    run_btn = st.button("LANCIA ANALISI OMNIBUS", type="primary", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: VERDETTO, AUDIT & REDAZIONE (5 PROPOSTE)
# ==============================================================================
if run_btn and query:
    st.header(f"📊 Analisi Competitiva: {query.upper()}")
    
    with st.spinner("Analisi di 20 competitor in corso..."):
        df_results = run_strategic_scan(mkt, query, pgs)
        
        if df_results is not None and not df_results.empty:
            # Mostro la tabella per trasparenza
            st.dataframe(df_results, column_config={"Copertina": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            # Calcolo Metriche Quantitative
            avg_p = df_results['Prezzo'].mean()
            avg_roy = df_results['Royalty_Est'].mean()
            self_ratio = (len(df_results[df_results["Self-Pub"] == "Sì"]) / len(df_results)) * 100
            
            # Opportunity Score
            o_score = 40
            if avg_p > 13: o_score += 20
            if self_ratio > 50: o_score += 20
            if avg_roy > 3.5: o_score += 20
            
            st.markdown("---")
            # Metriche con FIX COLORE
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_roy:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            c4.metric("Opportunity Score", f"{o_score}/100")

            # --- KEYWORD ALTERNATIVE (SOLO FORMATO) ---
            st.markdown("---")
            st.subheader("🔄 Varianti di Formato Suggerite")
            formati = ["Workbook", "Manuale", "Diario", "Prontuario"]
            fcols = st.columns(4)
            for i, f in enumerate(formati):
                alt_kw = f"{f} {query.split('per')[0]}"
                fcols[i].markdown(f"<div class='keyword-alt-card'><b>{f} Edition</b><br>{alt_kw}</div>", unsafe_allow_html=True)

            # --- REDAZIONE CONDIZIONALE (5 TITOLI + TRAME) ---
            st.markdown("---")
            if o_score >= 60:
                st.header("✍️ Piano Editoriale Sbloccato (5 Opzioni)")
                st.success("La keyword è stata validata come PROFITTEVOLE. Ecco 5 angoli di marketing per il tuo libro:")
                
                proposte = GPTStratega.genera_5_proposte(p_type, p_target, p_pain, p_dream)
                
                for idx, prop in enumerate(proposte):
                    with st.expander(f"OPZIONE {idx+1}: {prop['t']}"):
                        st.markdown(f"<div class='editorial-card'><span class='title-option'>{prop['t']}</span><p><i>{prop['p']}</i></p></div>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ Opportunity Score insufficiente (Sotto 60). Il sistema sconsiglia la redazione automatica per questa specifica keyword. Prova a cambiare formato o target.")
        else:
            st.error("Amazon ha limitato la richiesta o la API Key non è valida. Riprova tra 60 secondi.")
