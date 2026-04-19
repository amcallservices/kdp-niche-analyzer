import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# 1. Configurazione Pagina
st.set_page_config(
    page_title="KDP Niche Analyzer Pro", 
    page_icon="👑", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CSS per bloccare la sidebar e stile
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #ff9900; }
    </style>
""", unsafe_allow_html=True)

# LA TUA CHIAVE API SCRAPER
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

def get_amazon_data(marketplace, keyword):
    domains = {
        "Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", 
        "Francia": "amazon.fr", "Germania": "amazon.de"
    }
    domain = domains.get(marketplace, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    payload = {
        'api_key': API_KEY, 
        'url': target_url, 
        'render': 'true', 
        'country_code': 'it' if marketplace == "Italia" else 'us'
    }
    
    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        if res.status_code != 200: return None
            
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        for item in soup.find_all('div', {'data-component-type': 's-search-result'}):
            title = item.h2.text.strip() if item.h2 else "N/A"
            text_block = item.get_text().lower()
            
            # Estrazione Prezzo
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = 0.0
            if p_whole and p_frac:
                try: price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}")
                except: price = 0.0
            
            # Estrazione Recensioni
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            # Estrazione BSR
            bsr = 0
            bsr_match = re.search(r'#([0-9.,]+) in', item.get_text())
            if bsr_match:
                bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
                
            # Rilevamento Self-Publishing (KDP)
            is_self_pub = "indipendentemente pubblicato" in text_block or "independently published" in text_block
            
            results.append({
                "Libro": title, 
                "Prezzo": price, 
                "Recensioni": reviews, 
                "BSR": bsr,
                "Self-Published": "Sì" if is_self_pub else "Sconosciuto/Tradizionale"
            })
            
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Errore: {e}")
        return None

def calcola_opportunity_score(prezzo, recensioni, bsr):
    """Calcola un punteggio da 0 a 100 sulla fattibilità della nicchia"""
    score = 50 # Base di partenza
    
    # Valutazione Prezzo (Premiamo i margini alti)
    if prezzo > 14.90: score += 20
    elif prezzo < 9.90: score -= 20
    
    # Valutazione Concorrenza (Premiamo le recensioni basse)
    if 10 < recensioni < 150: score += 20
    elif recensioni > 1000: score -= 30
    
    # Valutazione Domanda (Premiamo BSR tra 5k e 80k)
    if 5000 < bsr < 80000: score += 20
    elif bsr > 300000: score -= 20
    
    return max(0, min(100, score)) # Mantiene il punteggio tra 0 e 100

def analizza_strategia_pro(df, keyword, obiettivo):
    if df.empty: return
    
    avg_price = df[df["Prezzo"] > 0]["Prezzo"].mean()
    avg_revs = df["Recensioni"].mean()
    valid_bsrs = df[df["BSR"] > 0]["BSR"]
    avg_bsr = valid_bsrs.mean() if not valid_bsrs.empty else 0
    
    # Calcolo Metriche Avanzate
    self_pub_count = len(df[df["Self-Published"] == "Sì"])
    self_pub_ratio = (self_pub_count / len(df)) * 100
    opp_score = calcola_opportunity_score(avg_price, avg_revs, avg_bsr if avg_bsr > 0 else 150000)

    st.header(f"📊 Report Professionale: {keyword.upper()}")
    
    # Box Metriche
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prezzo Medio", f"{avg_price:.2f} €")
    c2.metric("Media Recensioni", f"{int(avg_revs)}")
    c3.metric("BSR Medio", f"{int(avg_bsr)}" if avg_bsr > 0 else "N/D")
    c4.metric("Opportunity Score", f"{int(opp_score)}/100")

    st.markdown("---")
    
    # 1. ANALISI COMPETITORS (Tradizionale vs KDP)
    st.subheader("🕵️ Analisi dei Competitor")
    if self_pub_ratio > 30:
        st.success(f"✅ **Ecosistema KDP Favorevole:** Abbiamo rilevato un {int(self_pub_ratio)}% di libri chiaramente Self-Published in prima pagina. Questo significa che Amazon premia gli autori indipendenti in questa nicchia. Non c'è un monopolio delle grandi case editrici.")
    else:
        st.warning(f"⚠️ **Dominio Case Editrici:** Pochi o nessun libro self-published rilevato chiaramente in cima. Questa nicchia potrebbe essere dominata da autori famosi o case editrici tradizionali (es. Mondadori). Entrare qui richiede un brand forte.")

    # 2. ANALISI BASATA SULL'OBIETTIVO
    st.subheader(f"🎯 Strategia per: {obiettivo}")
    
    if obiettivo == "Reddito Passivo (Royalty)":
        if opp_score >= 70:
            st.success("**VERDETTO: NICCHIA VALIDATA.** I margini sono buoni (prezzi sopra i 10€) e la concorrenza è battibile. Procedi con la creazione: punta a una copertina superiore alla media e lancia con un prezzo di 12.90€-14.90€.")
        elif avg_price < 10:
            st.error("**PROBLEMA MARGINI:** Con prezzi medi così bassi, Amazon tratterrà gran parte dei guadagni per i costi di stampa. Per fare royalty qui, devi creare un **Bundle (3 in 1)** e venderlo ad almeno 17.90€.")
        else:
            st.warning("**COMPETIZIONE ALTA:** Le royalty potenziali ci sono, ma dovrai investire pesantemente in Amazon Ads per superare i leader attuali. Cerca una sotto-nicchia più specifica (es. aggiungendo 'per principianti').")
            
    elif obiettivo == "Lead Generation (Acquisire clienti)":
        st.info("**VERDETTO LEAD GEN:** Poiché il tuo scopo è acquisire contatti (es. per vendere corsi o consulenze), il volume di vendita massivo è meno importante della qualità del lettore.")
        if avg_bsr > 0 and avg_bsr < 200000:
            st.success("✅ **C'è traffico sufficiente.** Inserisci un QR code o un link nelle prime pagine del libro (Lead Magnet) per catturare l'email dei lettori prima ancora che finiscano di leggere.")
        else:
            st.warning("⚠️ **Poco Traffico:** I BSR sono molto alti. Rischia di essere un libro 'biglietto da visita' che dovrai promuovere tu esternamente (es. sui tuoi social), perché Amazon porterà poco traffico organico.")

    elif obiettivo == "Costruzione Brand / Authority":
        st.info("**VERDETTO AUTHORITY:** Se vuoi usare il libro per posizionarti come esperto, il prezzo deve riflettere il tuo valore.")
        if avg_price < 12:
            st.success("✅ **Vantaggio Competitivo:** I concorrenti si svendono. Crea un libro Premium (Copertina Rigida, impaginazione curata) e vendilo a 19.90€. Verrai percepito immediatamente come l'esperto di fascia alta della nicchia.")
        else:
            st.success("✅ **Mercato Educato:** Il pubblico è già abituato a pagare bene per queste informazioni. Crea un testo estremamente approfondito per ottenere recensioni a 5 stelle e dominare il settore.")

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎯 KDP Expert Tool")
    
    if st.button("🔄 Nuova Ricerca", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key = st.text_input("Inserisci Keyword Strategica")
    
    # NUOVO: Selezione Obiettivo
    st.markdown("---")
    obiettivo = st.radio(
        "Qual è il tuo obiettivo con questo libro?",
        ["Reddito Passivo (Royalty)", "Lead Generation (Acquisire clienti)", "Costruzione Brand / Authority"],
        help="L'intelligenza artificiale adatterà i consigli strategici in base a ciò che vuoi ottenere."
    )
    
    st.markdown("---")
    with st.expander("💡 Aiuto Ricerca Mirata"):
        st.markdown("""
        **Come trovare nicchie profittevoli:**
        1. **Non usare parole singole**: Invece di 'Yoga', usa 'Yoga per anziani'.
        2. **Risolvi un Dolore**: Le persone comprano per risolvere problemi.
        3. **Verifica il prezzo**: Punta a nicchie dove si vende a 14.90€+.
        4. **Opportunity Score**: Punta a un punteggio superiore a 60/100.
        """)
        
    run = st.button("AVVIA ANALISI", type="primary", use_container_width=True)

# --- LOGICA MAIN ---
if run and key:
    with st.spinner(f"Scansione e calcolo Opportunity Score in corso... (~15 sec)"):
        df = get_amazon_data(mkt, key)
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
            analizza_strategia_pro(df, key, obiettivo)
        else:
            st.error("Dati non disponibili. Prova con una keyword più specifica o riprova tra poco.")
