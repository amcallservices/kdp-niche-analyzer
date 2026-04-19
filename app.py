import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. ARCHITETTURA UI & DESIGN SYSTEM (ELITE DARK)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER ELITE 2026",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Iniezione CSS per Sidebar DARK, FISSA e componenti UI strategici
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* SIDEBAR DARK & FIXED */
        section[data-testid="stSidebar"] {
            min-width: 450px !important;
            max-width: 450px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p { color: #f0f6fc !important; }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important;
        }

        /* BOX RAGIONAMENTO GPT (SIDEBAR) */
        .gpt-reasoning-sidebar {
            background-color: #1c2128;
            border: 1px solid #3182ce;
            padding: 15px;
            border-radius: 8px;
            color: #90cdf4;
            font-size: 0.85rem;
            margin-bottom: 15px;
            border-left: 5px solid #3182ce;
        }

        /* METRICHE PRINCIPALI */
        .stMetric {
            background-color: #ffffff !important; border: 1px solid #d0d7de !important;
            border-left: 8px solid #0969da !important; padding: 20px !important;
            border-radius: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
        }

        /* AUDIT AI QUALITATIVO */
        .ai-audit-card {
            background-color: #fff9db;
            border: 1px solid #fab005;
            padding: 20px;
            border-radius: 10px;
            color: #856404;
            margin-bottom: 25px;
            border-left: 6px solid #fab005;
        }

        /* KEYWORD ALTERNATIVE (VIOLA/LAVANDA) */
        .keyword-alt-card {
            background-color: #f3e5f5; border: 1px solid #d1c4e9;
            padding: 15px; border-radius: 8px; margin-bottom: 10px;
            border-left: 5px solid #673ab7; color: #4527a0 !important;
        }

        /* CARTE EDITORIALI (SUCCESS) */
        .editorial-card {
            background-color: #ffffff; border: 1px solid #e1e4e8;
            padding: 25px; border-radius: 12px; margin-bottom: 20px;
            border-top: 5px solid #28a745; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .title-option { color: #cf222e; font-size: 1.25rem; font-weight: bold; display: block; margin-bottom: 8px; }

        .persona-summary {
            background-color: #f0f9ff; border-left: 5px solid #0369a1; 
            padding: 20px; border-radius: 10px; color: #0369a1; margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA INTEGRATA GPT & STRATEGIA
# ==============================================================================
WS_API_KEY = "50867242-8e16-4f72-b142-caef181401f6"

class GPTStratega:
    """Simula un agente GPT specializzato in KDP Marketing."""
    
    @staticmethod
    def sidebar_diagnosi(p_type, p_target, p_pain, p_dream):
        if not p_target or not p_pain:
            return "👨‍💻 In attesa di input per la dissezione psicografica..."
        
        # Logica di ragionamento simulata
        return f"""
        <b>Audit Predittivo AI:</b> Stai configurando un <i>{p_type}</i> per risolvere il conflitto <i>'{p_pain}'</i>. 
        <b>Consiglio:</b> Assicurati che il sottotitolo prometta esplicitamente il passaggio a <i>'{p_dream}'</i>. 
        La keyword generata agirà come un bisturi per isolare il tuo target dalla massa.
        """

    @staticmethod
    def audit_risultati(df, p_pain, p_dream):
        """Analizza i titoli della concorrenza per trovare buchi di mercato."""
        full_text = " ".join(df['Titolo'].tolist()).lower()
        pain_kws = p_pain.lower().split()
        dream_kws = p_dream.lower().split()
        
        found_pain = any(kw in full_text for kw in pain_kws if len(kw) > 3)
        found_dream = any(kw in full_text for kw in dream_kws if len(kw) > 3)
        
        if not found_pain and not found_dream:
            return "🌟 <b>WHITE SPACE RILEVATO:</b> I competitor ignorano sia il dolore che il sogno specifico. Questa è una nicchia vergine per il tuo posizionamento."
        elif found_pain and not found_dream:
            return "💡 <b>OPPORTUNITÀ DI POSIZIONAMENTO:</b> Tutti parlano del problema, ma nessuno vende la soluzione <i>'{p_dream}'</i>. Usa questo come tuo gancio principale."
        else:
            return "🚩 <b>MERCATO CONSAPEVOLE:</b> La concorrenza è già allineata. Dovrai differenziarti con un design di copertina superiore o un'offerta bundle."

    @staticmethod
    def genera_contenuti_editoriali(p_type, p_target, p_pain, p_dream, keyword):
        titles = [
            f"{p_type.upper()}: Addio {p_pain.capitalize()} per {p_target}",
            f"{keyword.split(':')[0]}: Il Metodo per {p_dream}",
            f"{p_target}: Protocollo pratico per trasformare {p_pain} in {p_dream}"
        ]
        trama = f"Sei un {p_target} stanco di lottare con {p_pain}? Questo {p_type} è stato progettato come una cura letteraria per portarti finalmente a {p_dream}."
        return titles, trama

# ==============================================================================
# 3. MOTORE DI SCRAPING (WEBSCRAPING.AI - CATEGORIA LIBRI)
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
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
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
# 4. SIDEBAR COMMAND CENTER (DARK & FISSA)
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ STRATEGY AGENT")
    
    with st.expander("📖 Istruzioni Strategiche", expanded=False):
        st.markdown("""
        1. **Diagnosi:** Inserisci Tipo Libro, Target e il Conflitto (Dolore/Sogno).
        2. **Analisi GPT:** Leggi il feedback in tempo reale dello Stratega AI.
        3. **Iniezione:** Clicca 'Applica Keyword' per caricare la stringa chirurgica.
        4. **Validazione:** Il sistema sblocca i contenuti solo se la nicchia è profittevole.
        """)

    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['kw_active'] = ""; st.rerun()

    st.markdown("---")
    st.subheader("👤 Identikit Persona & Libro")
    with st.expander("Configurazione Modello", expanded=True):
        p_type = st.selectbox("Angolo Editoriale", ["Manuale Pratico", "Workbook", "Diario", "Guida Passo-Passo", "Ricettario"])
        p_target = st.text_input("Lettore (Target)", placeholder="es. Liberi professionisti")
        p_pain = st.text_input("Problema (Dolore)", placeholder="es. gestione tasse")
        p_dream = st.text_input("Risultato (Sogno)", placeholder="es. serenità finanziaria")
    
    # AGENTE GPT SIDEBAR
    diagnosi_text = GPTStratega.sidebar_diagnosi(p_type, p_target, p_pain, p_dream)
    st.markdown(f'<div class="gpt-reasoning-sidebar">{diagnosi_text}</div>', unsafe_allow_html=True)
    
    if p_target and p_pain and p_dream:
        surgical_kw = f"{p_type} di {p_pain} per {p_target}: Guida per {p_dream}"
        if st.button(f"🎯 APPLICA KEYWORD AI: {surgical_kw}", use_container_width=True):
            st.session_state['kw_active'] = surgical_kw; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Mercato", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Focus", value=st.session_state['kw_active'])
    
    # AUTOCOMPLETE ENGINE (FREE)
    if query:
        with st.expander("💡 Espansione Keyword"):
            url_sug = f"https://completion.amazon.com/api/2017/suggestions?limit=5&prefix={urllib.parse.quote(query)}&alias=stripbooks"
            try:
                sug_res = requests.get(url_sug, headers={"User-Agent": "Mozilla/5.0"}).json()
                for s in sug_res.get('suggestions', []):
                    if st.button(f"🔎 {s['value']}", key=f"s_{s['value']}", use_container_width=True):
                        st.session_state['kw_active'] = s['value']; st.rerun()
            except: st.caption("Autocomplete non disponibile momentaneamente.")

    st.markdown("---")
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    run_btn = st.button("LANCIA ANALISI OMNIBUS", type="primary", use_container_width=True)

# ==============================================================================
# 5. DASHBOARD: VERDETTO, AUDIT & REDAZIONE
# ==============================================================================
if run_btn and query:
    st.header(f"📊 Report Strategico: {query.upper()}")
    
    st.markdown(f"""
    <div class="persona-summary">
        <b>POSIZIONAMENTO:</b> Utilizzo di un <b>{p_type}</b> per risolvere <b>{p_pain}</b> nel target <b>{p_target}</b>.
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("L'Agente GPT sta analizzando i dati di mercato..."):
        df_results = run_strategic_scan(mkt, query, pgs)
        
        if df_results is not None and not df_results.empty:
            # --- AI AUDIT QUALITATIVO ---
            audit_msg = GPTStratega.audit_risultati(df_results, p_pain, p_dream)
            st.markdown(f'<div class="ai-audit-card">{audit_msg}</div>', unsafe_allow_html=True)
            
            st.dataframe(df_results, column_config={"Copertina": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            # Calcolo Metriche
            avg_p = df_results['Prezzo'].mean()
            avg_roy = df_results['Royalty_Est'].mean()
            self_ratio = (len(df_results[df_results["Self-Pub"] == "Sì"]) / len(df_results)) * 100
            
            # Opportunity Score
            o_score = 40
            if avg_p > 13: o_score += 20
            if self_ratio > 45: o_score += 20
            if avg_roy > 3.5: o_score += 20
            
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Royalty Media", f"{avg_roy:.2f} €")
            c3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            c4.metric("Opportunity Score", f"{o_score}/100")

            # --- KEYWORD PIVOT (VIOLA) ---
            st.markdown("---")
            st.subheader("💡 Keyword Pivot Suggerite")
            ca1, ca2 = st.columns(2)
            ca1.markdown(f"<div class='keyword-alt-card'><b>Focus Problema:</b><br>{p_pain.capitalize()} per {p_target} in 30 giorni</div>", unsafe_allow_html=True)
            ca2.markdown(f"<div class='keyword-alt-card'><b>Focus Formato:</b><br>Workbook pratico per {p_dream.lower()}</div>", unsafe_allow_html=True)

            # --- REDAZIONE CONDIZIONALE ---
            st.markdown("---")
            if o_score >= 60:
                st.header("✍️ Proposta Editoriale Sbloccata")
                titoli, trama = GPTStratega.genera_contenuti_editoriali(p_type, p_target, p_pain, p_dream, query)
                col_t, col_p = st.columns([1, 1.5])
                with col_t:
                    st.subheader("📌 Titoli Hook")
                    for t in titoli:
                        st.markdown(f"<div class='editorial-card'><span class='title-option'>{t}</span></div>", unsafe_allow_html=True)
                with col_p:
                    st.subheader("📖 Bozza Trama")
                    st.markdown(f"<div class='editorial-card'><p style='font-style:italic;'>{trama}</p></div>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ Opportunity Score insufficiente per procedere alla redazione automatica. Lo Stratega AI consiglia di cambiare Angolo Editoriale o Target.")
        else:
            st.error("Amazon ha limitato la richiesta o la API Key non è valida. Riprova tra 60 secondi.")
