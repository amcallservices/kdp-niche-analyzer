import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io

# ==============================================================================
# 1. CONFIGURAZIONE AVANZATA DELLA PAGINA E UI
# ==============================================================================
st.set_page_config(
    page_title="KDP NICHE ANALYZER ELITE v.2026",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded" # Forza la sidebar aperta all'avvio
)

# Iniezione CSS per SIDEBAR DARK, FISSA e contenuto leggibile
st.markdown("""
    <style>
        /* Nasconde elementi nativi Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* BLOCCA SIDEBAR: Impedisce la chiusura e forza la visibilità */
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* --- SIDEBAR DARK STYLE --- */
        section[data-testid="stSidebar"] {
            min-width: 380px !important;
            max-width: 380px !important;
            background-color: #1a1c24 !important; /* Grigio scuro profondo */
            border-right: 1px solid #3e4149;
        }

        /* Forza il colore del testo e delle etichette nella Sidebar in BIANCO */
        [data-testid="stSidebar"] .stMarkdown p, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] .stHeader,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p {
            color: #ffffff !important;
        }

        /* Colore degli Input nella Sidebar per contrasto Dark */
        [data-testid="stSidebar"] input {
            background-color: #2b2e3b !important;
            color: #ffffff !important;
            border: 1px solid #4a4d5a !important;
        }

        /* --- MAIN AREA STYLE --- */
        [data-testid="stMetricValue"] { color: #0E1117 !important; font-size: 2rem !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #555555 !important; font-size: 1rem !important; }
        .stMetric {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-left: 6px solid #ff9900 !important;
            padding: 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        }

        /* BOX KEYWORD STRATEGICHE */
        .kw-container {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #3182ce;
        }
        .kw-title { color: #2c5282 !important; font-weight: bold; font-size: 1.1rem; display: block; margin-bottom: 5px; }
        .kw-desc { color: #4a5568 !important; font-size: 0.9rem; line-height: 1.4; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI BUSINESS E COSTANTI
# ==============================================================================
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

class KDPBrain:
    """Motore di calcolo per le metriche KDP."""
    
    @staticmethod
    def estimate_monthly_sales(bsr):
        """Converte il BSR in vendite mensili stimate."""
        if bsr <= 0: return 0
        if bsr <= 500: return 2500
        if bsr <= 2000: return 800
        if bsr <= 10000: return 250
        if bsr <= 30000: return 80
        if bsr <= 70000: return 35
        if bsr <= 120000: return 12
        if bsr <= 250000: return 4
        return 1

    @staticmethod
    def calculate_kdp_royalty(price, pages, is_color):
        """Calcola la royalty netta."""
        if price <= 0: return 0.0
        if not is_color:
            print_cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
        else:
            print_cost = 0.60 + (pages * 0.042)
            if print_cost < 2.15: print_cost = 2.15
        
        royalty = (price * 0.60) - print_cost
        return round(royalty, 2) if royalty > 0 else 0.0

    @staticmethod
    def get_opportunity_score(avg_p, avg_r, avg_bsr, self_ratio):
        score = 40
        if avg_p >= 14.90: score += 20
        elif avg_p < 10: score -= 20
        if avg_r < 150: score += 20
        elif avg_r > 1000: score -= 30
        if 5000 < avg_bsr < 80000: score += 20
        if self_ratio > 50: score += 20
        return max(0, min(100, score))

# ==============================================================================
# 3. MOTORE DI SCRAPING CATEGORICO (LIBRI & EBOOK)
# ==============================================================================
def get_niche_data(mkt, keyword, user_pages, user_color):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    country = 'it' if mkt == "Italia" else 'us'
    
    # --- CATEGORICO ---
    # L'uso di '&i=stripbooks' forza Amazon a cercare esclusivamente nel dipartimento LIBRI.
    search_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        res = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': search_url, 'render': 'true', 'country_code': country})
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # Filtriamo solo i risultati che sono effettivamente libri
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
        final_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "Titolo non trovato"
            status_text.info(f"🔍 Analisi Categorica Libri: {i+1}/15 | {title[:40]}...")
            
            img = item.find('img', class_='s-image')
            cover = img['src'] if img else ""
            
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}") if p_whole and p_frac else 0.0
            
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            # DEEP SCAN per validare che sia un libro e prendere il BSR
            bsr = 0
            is_self = False
            link = item.find('a', class_='a-link-normal s-no-outline')
            if link:
                prod_url = f"https://www.{domain}" + link['href']
                res_p = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': prod_url, 'country_code': country})
                if res_p.status_code == 200:
                    p_soup = BeautifulSoup(res_p.text, 'html.parser').get_text().lower()
                    # Cerca BSR specifico per Libri
                    bsr_m = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', p_soup)
                    if bsr_m: bsr = int(bsr_m.group(1).replace('.', '').replace(',', ''))
                    # Cerca Editore Indipendente
                    is_self = any(x in p_soup for x in ["indipendentemente pubblicato", "independently published", "kdp"])

            roy = KDPBrain.calculate_kdp_royalty(price, user_pages, user_color == "A Colori")
            v_mese = KDPBrain.estimate_monthly_sales(bsr)
            
            final_data.append({
                "Copertina": cover,
                "Titolo": title,
                "Prezzo": price,
                "Royalty Netta": f"{roy} €",
                "Recensioni": reviews,
                "BSR": bsr if bsr > 0 else "N/D",
                "Vendite/Mese": v_mese,
                "Utile/Mese": f"{round(v_mese * roy, 2)} €",
                "KDP": "Sì" if is_self else "No"
            })
            progress_bar.progress((i + 1) / len(items))
            
        status_text.empty()
        progress_bar.empty()
        return pd.DataFrame(final_data)
    except Exception as e:
        st.error(f"Errore: {e}")
        return None

# ==============================================================================
# 4. INTERFACCIA SIDEBAR (DARK, FISSA & APERTA)
# ==============================================================================
with st.sidebar:
    st.image("https://www.amcallservices.it/wp-content/uploads/2023/10/cropped-logo-amcall.png", width=200)
    st.title("⚡ KDP STRATEGY HUB")
    
    if st.button("🔄 RESET APPLICAZIONE", use_container_width=True):
        st.session_state['target_keyword'] = ""
        st.rerun()

    st.markdown("---")
    
    st.subheader("🛠️ Ingegneria della Keyword")
    with st.expander("Modelli di Nicchia Profittevole", expanded=True):
        arg = st.text_input("1. Argomento:", placeholder="es. Yoga")
        target = st.text_input("2. Target:", placeholder="es. Donne over 50")
        ben = st.text_input("3. Beneficio:", placeholder="es. Alleviare il mal di schiena")
        
        if arg and target and ben:
            st.caption("Seleziona l'angolo d'attacco:")
            k1 = f"{arg} per {target}: {ben}"
            if st.button(f"🎯 Strategia 'Pain & Gain': {k1}", use_container_width=True):
                st.session_state['target_keyword'] = k1
                st.rerun()
            k2 = f"Esercizi di {arg} per {target} per {ben}"
            if st.button(f"📦 Strategia 'Pratica/Workbook': {k2}", use_container_width=True):
                st.session_state['target_keyword'] = k2
                st.rerun()

    st.markdown("---")
    
    st.subheader("⚙️ Configurazione Scansione")
    mkt = st.selectbox("Marketplace di Analisi", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    query = st.text_input("🔍 Keyword da Analizzare", value=st.session_state.get('target_keyword', ""))
    pagine = st.number_input("Pagine del tuo libro", min_value=24, max_value=800, value=120)
    colore = st.selectbox("Tipo di Stampa", ["Bianco e Nero", "A Colori"])
    goal = st.radio("Obiettivo Strategico:", ["Royalty Passive", "Lead Generation", "Brand Authority"])
    
    run_btn = st.button("LANCIA ANALISI PROFONDA", type="primary", use_container_width=True)

# ==============================================================================
# 5. LOGICA PRINCIPALE (MAIN DASHBOARD)
# ==============================================================================
if run_btn and query:
    st.header(f"📈 Dashboard Analisi Categorica: {query.upper()}")
    
    with st.spinner("Analizzando esclusivamente Libri ed Ebook su Amazon..."):
        df = get_niche_data(mkt, query, pagine, colore)
        
        if df is not None and not df.empty:
            st.success("Dati estratti con successo! Analisi limitata al dipartimento Libri.")
            
            st.dataframe(
                df,
                column_config={"Copertina": st.column_config.ImageColumn("Cover", width="small")},
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            
            df['Utile_Num'] = df['Utile/Mese'].str.replace(' €', '').astype(float)
            df['Royalty_Num'] = df['Royalty Netta'].str.replace(' €', '').astype(float)
            
            avg_price = df['Prezzo'].mean()
            avg_royalty = df['Royalty_Num'].mean()
            self_ratio = (len(df[df["KDP"] == "Sì"]) / len(df)) * 100
            avg_bsr = pd.to_numeric(df[df['BSR'] != 'N/D']['BSR']).mean() if not df[df['BSR'] != 'N/D'].empty else 0
            
            opp_score = KDPBrain.get_opportunity_score(avg_price, df['Recensioni'].mean(), avg_bsr, self_ratio)
            
            st.header("🏁 Verdetto Professionale KDP")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Prezzo Medio", f"{avg_price:.2f} €")
            m2.metric("Royalty Media", f"{avg_royalty:.2f} €")
            m3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            m4.metric("Opportunity Score", f"{int(opp_score)}/100")
            
            st.markdown("---")
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.subheader("📝 Analisi Fattibilità")
                if opp_score >= 70:
                    st.success("**🟢 NICCHIA VALIDATA**: Mercato ideale per Libri/Ebook.")
                elif avg_price < 11:
                    st.error("**🔴 ERRORE MARGINI**: Prezzi troppo bassi per le Ads.")
                else:
                    st.info("**🔵 NICCHIA MODERATA**: Richiede differenziazione forte.")

            with c_right:
                st.subheader("💡 Strategia di Espansione")
                kw_low = query.lower()
                st.info(f"1. Guida strategica a {kw_low}\n2. {kw_low} per principianti")

        else:
            st.error("Errore: Amazon ha limitato la scansione. Riprova tra 60 secondi.")
else:
    st.title("Benvenuto nel Centro di Comando KDP")
    st.write("Configura la tua ricerca nella sidebar scura a sinistra per analizzare nicchie editoriali.")
