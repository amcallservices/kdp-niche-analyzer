import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import io

# ==============================================================================
# 1. CONFIGURAZIONE SUITE ELITE & UI PERSONALIZZATA
# ==============================================================================
st.set_page_config(
    page_title="KDP NICHE ANALYZER ELITE v.2026",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Iniezione CSS per Sidebar Dark, Fissa, Rimozione Menu e Grafica Professionale
st.markdown("""
    <style>
        /* Nasconde categoricamente il menu nativo di Streamlit e il footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* BLOCCA LA SIDEBAR: Impedisce la chiusura e garantisce la visibilità costante */
        [data-testid="collapsedControl"] { display: none !important; }
        
        /* --- SIDEBAR DARK STYLE --- */
        section[data-testid="stSidebar"] {
            min-width: 400px !important;
            max-width: 400px !important;
            background-color: #0f1116 !important; /* Nero profondo */
            border-right: 1px solid #30363d;
        }

        /* Testi e Label in bianco per massima leggibilità su sfondo Dark */
        [data-testid="stSidebar"] .stMarkdown p, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] .stHeader,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stExpander p {
            color: #f0f6fc !important;
        }

        /* Styling degli input all'interno della Sidebar */
        [data-testid="stSidebar"] input {
            background-color: #161b22 !important;
            color: #c9d1d9 !important;
            border: 1px solid #30363d !important;
        }

        /* --- MAIN DASHBOARD STYLE --- */
        [data-testid="stMetricValue"] { color: #1f2328 !important; font-size: 2.2rem !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #656d76 !important; font-size: 1.1rem !important; }
        .stMetric {
            background-color: #ffffff !important;
            border: 1px solid #d0d7de !important;
            border-left: 8px solid #f78166 !important; /* Arancione KDP */
            padding: 24px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        }

        /* Box Keyword Strategiche generate */
        .kw-container {
            background-color: #f6f8fa;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
            border: 1px solid #d0d7de;
            border-left: 5px solid #0969da;
        }
        .kw-title { color: #0969da !important; font-weight: bold; font-size: 1.2rem; display: block; margin-bottom: 8px; }
        .kw-desc { color: #24292f !important; font-size: 0.95rem; line-height: 1.5; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORE DI INTELLIGENZA EDITORIALE (BRAIN)
# ==============================================================================
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

class KDPBrain:
    """Modelli matematici basati sulle metriche Amazon KDP 2026."""
    
    @staticmethod
    def estimate_sales(bsr):
        """Traduzione algoritmica del BSR in volume di vendite mensili."""
        if bsr <= 0: return 0
        if bsr <= 1000: return 750
        if bsr <= 5000: return 250
        if bsr <= 15000: return 110
        if bsr <= 40000: return 45
        if bsr <= 90000: return 15
        if bsr <= 200000: return 5
        return 1

    @staticmethod
    def calculate_margin(price, pages, is_color):
        """Calcolo del profitto netto post-royalty e costi di stampa (Amazon EU)."""
        if price <= 0: return 0.0
        # Formula stimata per il mercato 2026
        if not is_color:
            print_cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
        else:
            print_cost = 0.60 + (pages * 0.045)
            if print_cost < 2.25: print_cost = 2.25
        
        # Amazon trattiene il 40% sul cartaceo (Royalty 60%)
        margin = (price * 0.60) - print_cost
        return round(margin, 2) if margin > 0 else 0.0

    @staticmethod
    def compute_opportunity_score(avg_p, avg_rev, avg_bsr, self_ratio):
        """Score finale di validazione della nicchia (0-100)."""
        score = 45
        if avg_p >= 14.90: score += 15
        if avg_rev < 250: score += 20
        elif avg_rev > 1500: score -= 35
        if 5000 < avg_bsr < 75000: score += 25
        if self_ratio > 45: score += 15
        return max(0, min(100, score))

# ==============================================================================
# 3. SCRAPER CATEGORICO (CATEGORICALLY BOOKS & EBOOKS)
# ==============================================================================
def get_exclusive_book_data(mkt, keyword, user_pages, user_color):
    """Estrae dati esclusivamente dal database Libri ed Ebook di Amazon."""
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    country = 'it' if mkt == "Italia" else 'us'
    
    # PARAMETRO CATEGORICO: '&i=stripbooks' forza la ricerca nel dipartimento Libri
    search_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        res = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': search_url, 'render': 'true', 'country_code': country})
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
        results_list = []
        progress = st.progress(0)
        status = st.empty()
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "Titolo Ignoto"
            status.info(f"🔍 Scansione Libri: {i+1}/15 | {title[:40]}...")
            
            img_src = item.find('img', class_='s-image')['src'] if item.find('img', class_='s-image') else ""
            
            # Parsing Prezzo
            p_w = item.find('span', 'a-price-whole')
            p_f = item.find('span', 'a-price-fraction')
            price = float(f"{p_w.text.replace(',','').replace('.','')}.{p_f.text}") if p_w and p_f else 0.0
            
            # Parsing Recensioni
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            # DEEP SCAN: Apertura pagina prodotto per BSR ed Editore
            bsr = 0
            is_self_pub = False
            link_tag = item.find('a', class_='a-link-normal s-no-outline')
            
            if link_tag:
                full_link = f"https://www.{domain}" + link_tag['href']
                res_p = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': full_link, 'country_code': country})
                if res_p.status_code == 200:
                    p_soup = BeautifulSoup(res_p.text, 'html.parser').get_text().lower()
                    # Ricerca BSR nel database Libri
                    bsr_match = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', p_soup)
                    if bsr_match: bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
                    # Verifica Editore Indipendente
                    is_self_pub = any(x in p_soup for x in ["indipendentemente pubblicato", "independently published", "kdp"])

            royalty_val = KDPBrain.calculate_margin(price, user_pages, user_color == "A Colori")
            est_sales = KDPBrain.estimate_sales(bsr)
            
            results_list.append({
                "Copertina": img_src,
                "Libro": title,
                "Prezzo": price,
                "Royalty Netta": f"{royalty_val} €",
                "Recensioni": reviews,
                "BSR Reale": bsr if bsr > 0 else "N/D",
                "Vendite Est.": est_sales,
                "Profitto Stimato": f"{round(est_sales * royalty_val, 2)} €",
                "Self-Pub": "Sì" if is_self_pub else "No"
            })
            progress.progress((i + 1) / len(items))
            
        status.empty()
        progress.empty()
        return pd.DataFrame(results_list)
    except Exception as e:
        st.error(f"Errore Scraper: {e}")
        return None

# ==============================================================================
# 4. SIDEBAR DARK & FISSA (STRATEGIC PANEL)
# ==============================================================================
if 'target_kw' not in st.session_state:
    st.session_state['target_kw'] = ""

with st.sidebar:
    st.title("🛡️ KDP STRATEGY HUB")
    st.caption("Analisi Esclusiva Libri ed Ebook")
    
    if st.button("🔄 NUOVA SESSIONE", use_container_width=True):
        st.session_state['target_kw'] = ""
        st.rerun()

    st.markdown("---")
    
    # GENERATORE DI KEYWORD STRATEGICA (Formula di Marketing)
    st.subheader("🛠️ Ingegneria della Keyword")
    with st.expander("Generatore Pro (Target + Beneficio)", expanded=True):
        t_topic = st.text_input("Argomento:", placeholder="es. Yoga")
        t_target = st.text_input("Target:", placeholder="es. Donne over 60")
        t_benefit = st.text_input("Beneficio:", placeholder="es. mobilità articolare")
        
        if t_topic and t_target and t_benefit:
            st.caption("Seleziona il modello di vendita:")
            # Modello 1: Risultato Diretto
            k1 = f"{t_topic} per {t_target}: {t_benefit}"
            if st.button(f"🎯 Strategia Risultato: {k1}", use_container_width=True):
                st.session_state['target_kw'] = k1
                st.rerun()
            # Modello 2: Metodo/Workbook
            k2 = f"Esercizi di {t_topic} per {t_target} per {t_benefit}"
            if st.button(f"📦 Strategia Metodo: {k2}", use_container_width=True):
                st.session_state['target_kw'] = k2
                st.rerun()

    st.markdown("---")
    
    st.subheader("⚙️ Parametri Analisi")
    mkt_sel = st.selectbox("Marketplace Amazon", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    final_query = st.text_input("🔍 Keyword sotto Analisi", value=st.session_state['target_kw'])
    
    st.caption("Dati per calcolo Royalty:")
    num_pagine = st.number_input("Pagine del libro", min_value=24, max_value=800, value=120)
    tipo_stampa = st.selectbox("Interno", ["Bianco e Nero", "A Colori"])
    
    st.markdown("---")
    lancia_analisi = st.button("AVVIA DEEP SCAN LIBRI", type="primary", use_container_width=True)

# ==============================================================================
# 5. MAIN DASHBOARD (REPORT PROFESSIONALE)
# ==============================================================================
if lancia_analisi and final_query:
    st.header(f"📊 Report Analisi Editoriale: {final_query.upper()}")
    
    with st.spinner("Scansione categorica in corso... (Esclusione altri prodotti)"):
        data_df = get_exclusive_book_data(mkt_sel, final_query, num_pagine, tipo_stampa)
        
        if data_df is not None and not data_df.empty:
            st.success("Analisi completata! Database focalizzato esclusivamente su Libri ed Ebook.")
            
            # Tabella Risultati
            st.dataframe(
                data_df,
                column_config={"Copertina": st.column_config.ImageColumn("Cover", width="small")},
                use_container_width=True,
                hide_index=True
            )
            
            # Conversione dati per metriche
            data_df['Profitto_Num'] = data_df['Profitto Stimato'].str.replace(' €', '').astype(float)
            data_df['Royalty_Num'] = data_df['Royalty Netta'].str.replace(' €', '').astype(float)
            avg_p = data_df['Prezzo'].mean()
            avg_r = data_df['Royalty_Num'].mean()
            total_pot = data_df['Profitto_Num'].sum()
            s_ratio = (len(data_df[data_df["Self-Pub"] == "Sì"]) / len(data_df)) * 100
            valid_bsrs = pd.to_numeric(data_df[data_df['BSR Reale'] != 'N/D']['BSR Reale']).mean() if not data_df[data_df['BSR Reale'] != 'N/D'].empty else 0
            
            o_score = KDPBrain.compute_opportunity_score(avg_p, data_df['Recensioni'].mean(), valid_bsrs, s_ratio)
            
            st.markdown("---")
            st.subheader("🏁 Verdetto di Business KDP")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Prezzo Medio Pagina", f"{avg_p:.2f} €")
            m2.metric("Royalty Media Netta", f"{avg_r:.2f} €")
            m3.metric("Self-Pub Ratio", f"{int(s_ratio)}%")
            m4.metric("Opportunity Score", f"{int(o_score)}/100")
            
            st.markdown("---")
            
            col_l, col_r = st.columns(2)
            with col_l:
                st.subheader("📝 Validazione Strategica")
                if o_score >= 70:
                    st.success("**🟢 NICCHIA VALIDATA**: Mercato profittevole con barriere d'ingresso gestibili. Consigliata la pubblicazione immediata.")
                elif avg_p < 12:
                    st.error("**🔴 MARGINI TROPPO BASSI**: I prezzi medi non giustificano l'investimento in Amazon Ads. Punta a un Bundle per alzare il valore.")
                elif s_ratio < 25:
                    st.warning("**🟡 DOMINIO CASE EDITRICI**: La pagina è in mano a grandi editori. Difficile posizionarsi organicamente.")
                else:
                    st.info("**🔵 ANALISI NECESSARIA**: La nicchia è bilanciata. Richiede un posizionamento molto specifico per emergere.")

            with col_r:
                st.subheader("💡 Strategie di Espansione")
                kw_l = final_query.lower()
                st.markdown(f"<div class='kw-container'><span class='kw-title'>Espansione Manuale</span><span class='kw-desc'>Crea una guida 'passo-passo' dedicata a {kw_l} per massimizzare la conversione organica.</span></div>", unsafe_allow_html=True)
                st.info(f"Prova anche queste keyword: \n1. {kw_l} per principianti assoluti\n2. {kw_l} rapido ed efficace")

        else:
            st.error("Amazon ha limitato la scansione. Attendi 60 secondi prima di una nuova ricerca.")
else:
    # Pagina Welcome
    st.title("Benvenuto nel KDP Analyzer Elite")
    st.write("Configura la tua ricerca nella sidebar scura a sinistra per iniziare l'analisi professionale.")
    st.image("https://m.media-amazon.com/images/G/01/mobile-apps/dex/app-submission/kdp_logo._CB485935043_.png", width=180)
