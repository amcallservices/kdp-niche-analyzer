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
    initial_sidebar_state="expanded"
)

# Iniezione CSS Massiva per rendere l'interfaccia Fissa, Professionale e Leggibile
st.markdown("""
    <style>
        /* Nasconde elementi nativi Streamlit per un look White-Label */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* BLOCCA SIDEBAR: Impedisce la chiusura e imposta larghezza */
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] {
            min-width: 380px !important;
            max-width: 380px !important;
            background-color: #f4f7f9;
            border-right: 1px solid #e0e0e0;
        }

        /* FIX COLORI: Testo scuro garantito su Metriche e Box per evitare il "Tutto Bianco" */
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

        /* ALERT CUSTOM */
        .verdetto-box {
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: 500;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGICA DI BUSINESS E COSTANTI
# ==============================================================================
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

class KDPBrain:
    """Motore di calcolo per le metriche KDP basate sul manuale 2026."""
    
    @staticmethod
    def estimate_monthly_sales(bsr):
        """Converte il BSR in vendite mensili stimate su Amazon IT/US."""
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
        """Calcola la royalty netta sottraendo commissioni Amazon e costi stampa."""
        if price <= 0: return 0.0
        # Formula Amazon Europa (Media approssimata)
        if not is_color:
            print_cost = 2.15 if pages <= 108 else 0.60 + (pages * 0.012)
        else:
            print_cost = 0.60 + (pages * 0.042)
            if print_cost < 2.15: print_cost = 2.15
        
        royalty = (price * 0.60) - print_cost
        return round(royalty, 2) if royalty > 0 else 0.0

    @staticmethod
    def get_opportunity_score(avg_p, avg_r, avg_bsr, self_ratio):
        """Algoritmo proprietario per misurare la facilità di ingresso."""
        score = 40
        if avg_p >= 14.90: score += 20
        elif avg_p < 10: score -= 20
        
        if avg_r < 150: score += 20
        elif avg_r > 1000: score -= 30
        
        if 5000 < avg_bsr < 80000: score += 20
        
        if self_ratio > 50: score += 20
        return max(0, min(100, score))

# ==============================================================================
# 3. MOTORE DI SCRAPING PROFONDO (DEEP SCAN)
# ==============================================================================
def get_niche_data(mkt, keyword, user_pages, user_color):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(mkt, "amazon.it")
    country = 'it' if mkt == "Italia" else 'us'
    
    # URL filtrato solo per Libri ed Ebook
    search_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    try:
        # Step 1: Pagina di Ricerca Generale
        res = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': search_url, 'render': 'true', 'country_code': country})
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15] # Analizziamo i primi 15
        
        final_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "Titolo non trovato"
            status_text.info(f"🔍 Deep Scanning: {i+1}/15 | {title[:40]}...")
            
            # Immagine
            img = item.find('img', class_='s-image')
            cover = img['src'] if img else ""
            
            # Prezzo
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}") if p_whole and p_frac else 0.0
            
            # Recensioni
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            # DEEP SCAN: Entriamo nel link del prodotto
            bsr = 0
            is_self = False
            link = item.find('a', class_='a-link-normal s-no-outline')
            if link:
                prod_url = f"https://www.{domain}" + link['href']
                res_p = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': prod_url, 'country_code': country})
                if res_p.status_code == 200:
                    p_soup = BeautifulSoup(res_p.text, 'html.parser').get_text().lower()
                    # Cerca BSR
                    bsr_m = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', p_soup)
                    if bsr_m: bsr = int(bsr_m.group(1).replace('.', '').replace(',', ''))
                    # Cerca Editore Indipendente
                    is_self = any(x in p_soup for x in ["indipendentemente pubblicato", "independently published", "kdp"])

            # Calcoli Royalty e Vendite
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
        st.error(f"Errore critico durante la scansione: {e}")
        return None

# ==============================================================================
# 4. INTERFACCIA SIDEBAR (FISSA E SEMPRE APERTA)
# ==============================================================================
with st.sidebar:
    st.image("https://www.amcallservices.it/wp-content/uploads/2023/10/cropped-logo-amcall.png", width=200) # Logo di esempio
    st.title("⚡ KDP STRATEGY HUB")
    
    if st.button("🔄 RESET APPLICAZIONE", use_container_width=True):
        st.session_state['target_keyword'] = ""
        st.rerun()

    st.markdown("---")
    
    # GENERATORE KEYWORD PROFESSIONALE
    st.subheader("🛠️ Ingegneria della Keyword")
    with st.expander("Modelli di Nicchia Profittevole", expanded=True):
        arg = st.text_input("1. Argomento:", placeholder="es. Cucina Chetogenica")
        target = st.text_input("2. Target:", placeholder="es. Donne over 50")
        ben = st.text_input("3. Beneficio:", placeholder="es. Senza rinunciare al gusto")
        
        if arg and target and ben:
            st.caption("Seleziona e carica l'angolo d'attacco:")
            # Modello Problema/Soluzione
            k1 = f"{arg} per {target}: {ben}"
            if st.button(f"🎯 Strategia 'Pain & Gain': {k1}"):
                st.session_state['target_keyword'] = k1
                st.rerun()
            # Modello Pratico
            k2 = f"Esercizi di {arg} per {target} per {ben}"
            if st.button(f"📦 Strategia 'Pratica/Workbook': {k2}"):
                st.session_state['target_keyword'] = k2
                st.rerun()

    st.markdown("---")
    
    # IMPOSTAZIONI ANALISI
    st.subheader("⚙️ Configurazione Scansione")
    mkt = st.selectbox("Marketplace di Analisi", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    
    # Campo di input collegato alla sessione
    query = st.text_input("🔍 Keyword da Analizzare", value=st.session_state.get('target_keyword', ""))
    
    pagine = st.number_input("Pagine del tuo libro (stima)", min_value=24, max_value=800, value=120)
    colore = st.selectbox("Tipo di Stampa", ["Bianco e Nero", "A Colori"])
    goal = st.radio("Obiettivo Strategico:", ["Royalty Passive", "Lead Generation", "Brand Authority"])
    
    analyze_btn = st.button("LANCIA ANALISI PROFONDA", type="primary", use_container_width=True)

# ==============================================================================
# 5. LOGICA PRINCIPALE (MAIN DASHBOARD)
# ==============================================================================
if analyze_btn and query:
    st.header(f"📈 Dashboard Analisi: {query.upper()}")
    
    with st.spinner("Navigazione profonda nei database Amazon... (Attendere 60-90 secondi)"):
        df = get_niche_data(mkt, query, pagine, colore)
        
        if df is not None and not df.empty:
            st.success("Dati estratti con successo dalla prima pagina dei Libri!")
            
            # Tabella Interattiva con Immagini
            st.dataframe(
                df,
                column_config={"Copertina": st.column_config.ImageColumn("Cover", width="small")},
                use_container_width=True,
                hide_index=True
            )
            
            # Esportazione CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 SCARICA REPORT CSV", data=csv, file_name=f"kdp_analysis_{query}.csv", mime="text/csv")
            
            st.markdown("---")
            
            # CALCOLO METRICHE PROFESSIONALI
            # Pulizia stringhe per calcoli
            df['Utile_Num'] = df['Utile/Mese'].str.replace(' €', '').astype(float)
            df['Royalty_Num'] = df['Royalty Netta'].str.replace(' €', '').astype(float)
            
            avg_price = df['Prezzo'].mean()
            avg_royalty = df['Royalty_Num'].mean()
            total_market_cap = df['Utile_Num'].sum()
            self_ratio = (len(df[df["KDP"] == "Sì"]) / len(df)) * 100
            avg_bsr = pd.to_numeric(df[df['BSR'] != 'N/D']['BSR']).mean() if not df[df['BSR'] != 'N/D'].empty else 0
            
            # SCORE FINALE
            opp_score = KDPBrain.get_opportunity_score(avg_price, df['Recensioni'].mean(), avg_bsr, self_ratio)
            
            # Visualizzazione Report
            st.header("🏁 Verdetto Professionale KDP")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Prezzo Medio Nicchia", f"{avg_price:.2f} €")
            m2.metric("Royalty Media a Copia", f"{avg_royalty:.2f} €")
            m3.metric("Self-Pub Ratio", f"{int(self_ratio)}%")
            m4.metric("Opportunity Score", f"{int(opp_score)}/100")
            
            st.markdown("---")
            
            # ANALISI STRATEGICA
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.subheader("📝 Analisi Fattibilità")
                if opp_score >= 70:
                    st.balloons()
                    st.success("**🟢 NICCHIA VALIDATA (BEST OPTION)**: C'è un'altissima presenza di autori indipendenti e i margini sono sani. Puoi scalare questa nicchia con un investimento pubblicitario moderato.")
                elif avg_price < 11:
                    st.error("**🔴 ERRORE MARGINI**: I prezzi medi in questa pagina sono troppo bassi. Non c'è abbastanza 'aria' per pagare le Amazon Ads e restare in profitto. Sconsigliato se non crei un Bundle.")
                elif self_ratio < 20:
                    st.warning("**🟡 DOMINIO TRADIZIONALE**: La pagina è in mano a grandi case editrici. Competere sarà costoso e difficile a livello organico.")
                else:
                    st.info("**🔵 NICCHIA MODERATA**: I dati sono bilanciati. Entra solo se hai un angolo d'attacco (keyword) molto più specifico di quelli attuali.")

            with c_right:
                st.subheader("💡 Strategia di Espansione")
                st.write("In base al tuo obiettivo, ecco come muoverti:")
                
                if goal == "Royalty Passive":
                    st.markdown(f"<div class='kw-container'><span class='kw-title'>Focalizzati sui Volumi</span><span class='kw-desc'>Punta a creare un libro di valore ma con prezzo competitivo. Se la media è {avg_price:.2f}€, posizionati a {avg_price - 1}€ per rubare quote di mercato iniziali.</span></div>", unsafe_allow_html=True)
                elif goal == "Lead Generation":
                    st.markdown("<div class='kw-container'><span class='kw-title'>Il Libro come Funnel</span><span class='kw-desc'>Inserisci QR code e link nelle prime 10 pagine. Il BSR basso indica che molte persone leggeranno il libro: trasformali in contatti email.</span></div>", unsafe_allow_html=True)
                
                st.markdown("**Altre Keyword da testare:**")
                kw_low = query.lower()
                st.info(f"1. Guida passo passo a {kw_low}\n2. {kw_low} per principianti assoluti\n3. Il segreto di {kw_low}: Manuale pratico")

        else:
            st.error("Amazon ha limitato temporaneamente la scansione o non ci sono risultati per questa categoria. Riprova tra 60 secondi.")
else:
    # Pagina di Benvenuto se non c'è analisi attiva
    st.title("Benvenuto nel Centro di Comando KDP")
    st.write("Seleziona o crea una keyword nella barra laterale per iniziare l'analisi professionale.")
    st.markdown("---")
    st.image("https://m.media-amazon.com/images/G/01/mobile-apps/dex/app-submission/kdp_logo._CB485935043_.png", width=150)
