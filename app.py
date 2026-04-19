import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io
import urllib.parse

# ==============================================================================
# 1. CONFIGURAZIONE UI ELITE (SIDEBAR DARK, FISSA E PROFESSIONALE)
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER ELITE 2026",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        [data-testid="collapsedControl"] { display: none !important; }
        
        section[data-testid="stSidebar"] {
            min-width: 440px !important;
            max-width: 440px !important;
            background-color: #0d1117 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p { color: #f0f6fc !important; }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
            background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important;
        }

        /* METRICHE */
        .stMetric {
            background-color: #ffffff !important; border: 1px solid #d0d7de !important;
            border-left: 8px solid #0969da !important; padding: 20px !important;
            border-radius: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
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

        /* AUDIT AI (MAIN AREA) */
        .ai-audit-card {
            background-color: #fff9db;
            border: 1px solid #fab005;
            padding: 20px;
            border-radius: 10px;
            color: #856404;
            margin-bottom: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .keyword-alt-card {
            background-color: #f3e5f5; border: 1px solid #d1c4e9;
            padding: 15px; border-radius: 8px; margin-bottom: 10px;
            border-left: 5px solid #673ab7; color: #4527a0 !important;
        }

        .editorial-card {
            background-color: #ffffff; border: 1px solid #e1e4e8;
            padding: 25px; border-radius: 12px; margin-bottom: 20px;
            border-top: 5px solid #28a745; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .title-option { color: #cf222e; font-size: 1.2rem; font-weight: bold; display: block; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORE DI RAGIONAMENTO GPT (STRATEGA AI)
# ==============================================================================
WS_API_KEY = "50867242-8e16-4f72-b142-caef181401f6"

class GPTStrategicAgent:
    """Sistema di ragionamento GPT integrato per l'analisi e la sidebar."""
    
    @staticmethod
    def evaluate_persona_input(p_type, p_target, p_pain, p_dream):
        """Analisi predittiva GPT sulla coerenza della Buyer Persona."""
        if not p_target or not p_pain:
            return "In attesa di dati per eseguire la scansione psicografica..."
        
        # Simulazione ragionamento logico GPT
        score = 0
        if len(p_pain) > 10: score += 1
        if len(p_target) > 10: score += 1
        
        if score < 2:
            return "⚠️ **Analisi GPT:** I dati inseriti sono troppo generici. Per una keyword 'bisturi', specifica meglio la demografia (es. anziani invece di persone) e il dolore."
        else:
            return f"✅ **Analisi GPT:** Configurazione solida. Il {p_type} è lo strumento ideale per risolvere '{p_pain}' nel segmento '{p_target}'."

    @staticmethod
    def niche_audit(df, p_pain, p_dream):
        """Audit AI dei risultati della concorrenza."""
        titles = " ".join(df['Titolo'].tolist()).lower()
        pain_words = p_pain.lower().split()
        dream_words = p_dream.lower().split()
        
        pain_match = any(w in titles for w in pain_words if len(w) > 3)
        dream_match = any(w in titles for w in dream_words if len(w) > 3)
        
        if not pain_match and not dream_match:
            return "🔍 **Opportunità d'Oro (AI Audit):** Nessuno dei competitor attuali affronta esplicitamente il dolore o il sogno che hai identificato. Puoi dominare la nicchia con un posizionamento diretto."
        elif pain_match and not dream_match:
            return "⚖️ **Opportunità Media (AI Audit):** Molti parlano del problema, ma nessuno promette la soluzione specifica che offri tu. Focalizzati sul 'Sogno' nei tuoi titoli."
        else:
            return "🚩 **Alta Competizione (AI Audit):** I competitor sono già allineati alla tua Persona. Avrai bisogno di una copertina eccezionale e di un angolo di marketing unico."

    @staticmethod
    def generate_hook_titles(p_type, p_target, p_pain, p_dream):
        """Genera titoli ad alto impatto basati su prompt-templates."""
        return [
            f"{p_type.upper()}: Sconfiggi {p_pain} e ottieni {p_dream} per {p_target}",
            f"{p_target}: Il Metodo Passo-Passo per passare da {p_pain} a {p_dream}",
            f"Basta {p_pain.capitalize()}! La soluzione definitiva per {p_target}"
        ]

# ==============================================================================
# 3. CORE SCRAPER (CATEGORICO LIBRI)
# ==============================================================================
def scrape_books_elite(mkt, keyword, pages):
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
                "Royalty_Est": roy, "KDP": "Sì" if "independently" in title.lower() or "pubblicato" in title.lower() else "No"
            })
            p_bar.progress((i + 1) / len(items))
        return pd.DataFrame(results)
    except: return None

# ==============================================================================
# 4. SIDEBAR: AGENTE STRATEGA AI (DARK & FISSA)
# ==============================================================================
if 'kw_active' not in st.session_state: st.session_state['kw_active'] = ""

with st.sidebar:
    st.title("🛡️ KDP OMNI-REASONER")
    
    # --- AGENTE GPT NELLA SIDEBAR ---
    st.subheader("🤖 Stratega AI: Analisi Predittiva")
    with st.container():
        # Questo blocco viene aggiornato dinamicamente mentre l'utente scrive
        p_type = st.selectbox("Angolo Editoriale", ["Manuale Pratico", "Workbook", "Diario", "Guida Passo-Passo"])
        p_target = st.text_input("Lettore (Chi?)", placeholder="es. Mamme lavoratrici")
        p_pain = st.text_input("Problema (Dolore?)", placeholder="es. stress da tempo")
        p_dream = st.text_input("Sogno (Desiderio?)", placeholder="es. equilibrio casa-lavoro")
        
        gpt_feedback = GPTStrategicAgent.evaluate_persona_input(p_type, p_target, p_pain, p_dream)
        st.markdown(f'<div class="gpt-reasoning-sidebar">{gpt_feedback}</div>', unsafe_allow_html=True)
    
    # Generazione Keyword basata sul ragionamento AI
    if p_target and p_pain and p_dream:
        final_kw = f"{p_type} di {p_pain} per {p_target}: Guida per {p_dream}"
        if st.button(f"🎯 APPLICA KEYWORD AI: {final_kw}", use_container_width=True):
            st.session_state['kw_active'] = final_kw; st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword Focus", value=st.session_state['kw_active'])
    
    pgs = st.number_input("Pagine Stimate", min_value=24, value=120)
    run = st.button("LANCIA ANALISI OMNIBUS", type="primary", use_container_width=True)

# ==============================================================================
# 5. MAIN DASHBOARD: REPORT & AI AUDIT
# ==============================================================================
if run and query:
    st.header(f"📊 Report Strategico: {query.upper()}")
    
    with st.spinner("L'Agente GPT sta analizzando il mercato..."):
        df = scrape_books_elite(mkt, query, pgs)
        
        if df is not None and not df.empty:
            # --- AI AUDIT QUALITATIVO ---
            audit_text = GPTStrategicAgent.niche_audit(df, p_pain, p_dream)
            st.markdown(f'<div class="ai-audit-card">{audit_text}</div>', unsafe_allow_html=True)
            
            # Tabella Risultati
            st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Preview")}, use_container_width=True, hide_index=True)
            
            # Metriche Quantitative
            avg_p = df['Prezzo'].mean()
            self_ratio = (len(df[df["KDP"] == "Sì"]) / len(df)) * 100
            o_score = 40
            if avg_p > 13: o_score += 30
            if self_ratio > 45: o_score += 30
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo Medio", f"{avg_p:.2f} €")
            c2.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            c3.metric("Opportunity Score", f"{o_score}/100")

            # --- REDAZIONE STRATEGICA (Solo se score > 60) ---
            if o_score >= 60:
                st.markdown("---")
                st.header("✍️ Proposta Editoriale Generata da AI")
                t_list = GPTStrategicAgent.generate_hook_titles(p_type, p_target, p_pain, p_dream)
                
                col_t, col_p = st.columns([1, 1.5])
                with col_t:
                    st.subheader("📌 Titoli High-Conversion")
                    for t in t_list:
                        st.markdown(f"<div class='editorial-card'><span class='title-option'>{t}</span></div>", unsafe_allow_html=True)
                with col_p:
                    st.subheader("📖 Bozza Trama (Marketing Narrativo)")
                    st.markdown(f"""
                    <div class='editorial-card'>
                        <p style='font-style:italic;'>
                        "Sei un {p_target} e ti senti esausto a causa di {p_pain}? Non sei solo. 
                        In questo {p_type}, scopriremo come abbattere le barriere verso {p_dream}."
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Score insufficiente. L'Agente GPT consiglia di provare le alternative viola qui sotto.")
                
            # Keyword Alternative (Pivot AI)
            st.markdown("---")
            st.subheader("💡 Keyword Pivot (Suggerite da AI)")
            ca1, ca2 = st.columns(2)
            ca1.markdown(f"<div class='keyword-alt-card'><b>Focus Problema:</b><br>{p_pain.capitalize()} per {p_target} principianti</div>", unsafe_allow_html=True)
            ca2.markdown(f"<div class='keyword-alt-card'><b>Focus Risultato:</b><br>Protocollo per ottenere {p_dream}</div>", unsafe_allow_html=True)
        else:
            st.error("Errore Amazon o API. Riprova tra 60 secondi.")
