import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# 1. Configurazione Pagina
st.set_page_config(
    page_title="KDP Niche Analyzer Gold", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CSS per bloccare la sidebar e stile tabelle
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# LA TUA CHIAVE API
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
            
            # Estrazione Prezzo
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = 0.0
            if p_whole and p_frac:
                try:
                    price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}")
                except: price = 0.0
            
            # Estrazione Recensioni
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            # Estrazione BSR (Metodo dinamico)
            # Nota: Amazon spesso nasconde il BSR nei risultati di ricerca. 
            # Se non presente, assegniamo un valore stimato basato sulla popolarità/rank.
            bsr = 0
            bsr_text = item.get_text()
            bsr_match = re.search(r'#([0-9.,]+) in', bsr_text)
            if bsr_match:
                bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
            else:
                # Similiamo un BSR medio per i primi risultati se il dato è protetto
                bsr = 0 # Valore 0 indica dato non disponibile in questa vista
            
            results.append({
                "Libro": title, "Prezzo": price, "Recensioni": reviews, "BSR": bsr
            })
            
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Errore: {e}")
        return None

def analizza_strategia_bsr(df, keyword):
    if df.empty: return
    
    avg_price = df[df["Prezzo"] > 0]["Prezzo"].mean()
    avg_revs = df["Recensioni"].mean()
    
    # Filtriamo i BSR validi (alcuni potrebbero essere 0 se non trovati)
    valid_bsrs = df[df["BSR"] > 0]["BSR"]
    avg_bsr = valid_bsrs.mean() if not valid_bsrs.empty else "N/D"

    st.header(f"📊 Report Strategico: {keyword.upper()}")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Medio", f"{avg_price:.2f} €")
    c2.metric("Media Recensioni", f"{int(avg_revs)}")
    c3.metric("BSR Medio Stimato", f"{avg_bsr}")

    st.markdown("---")

    # LOGICA DI ANALISI PROFITTO
    if avg_price < 10:
        st.error("⚠️ **NICCHIA A BASSO MARGINE**: I prezzi sono troppo bassi. Anche con vendite alte, il guadagno netto dopo Ads e Royalty sarà minimo.")
    elif avg_revs > 1000:
        st.warning("🔥 **NICCHIA IPER-COMPETITIVA**: Troppe recensioni. Per scalare questa nicchia serve un budget pubblicitario massiccio.")
    elif avg_bsr != "N/D" and avg_bsr < 50000:
        st.success("💰 **NICCHIA D'ORO**: Alta domanda (BSR basso) e prezzi sani. Qui si fanno i soldi veri.")
    elif avg_bsr != "N/D" and avg_bsr > 200000:
        st.info("🏜️ **NICCHIA DESERTA**: Poca competizione, ma anche pochissime vendite. Rischi di pubblicare un libro che nessuno cerca.")
    else:
        st.success("✅ **BUCO DI MERCATO**: Competizione moderata e prezzi accettabili. Consigliato creare un prodotto 'Premium' (Bundle o Copertina Rigida).")

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎯 KDP Expert Tool")
    
    if st.button("🔄 Nuova Ricerca", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key = st.text_input("Inserisci Keyword Strategica")
    
    st.markdown("---")
    
    # SEZIONE AIUTO RICERCA (Richiesta utente)
    with st.expander("💡 Aiuto Ricerca Mirata"):
        st.markdown("""
        **Come trovare nicchie profittevoli:**
        1. **Non usare parole singole**: Invece di 'Yoga', usa 'Yoga per anziani con mobilità ridotta'.
        2. **Cerca il 'Dolore'**: Le persone comprano per risolvere problemi. Esempio: 'Come smettere di procrastinare'.
        3. **Verifica il prezzo**: Se i primi 5 risultati costano meno di 9€, scappa. Cerca nicchie dove si vende a 14.90€+.
        4. **BSR Target**: Punta a keyword dove i primi 3 libri hanno un BSR tra 5.000 e 80.000.
        """)
        
    run = st.button("AVVIA ANALISI", type="primary", use_container_width=True)

# --- LOGICA MAIN ---
if run and key:
    with st.spinner("Analizzando il mercato..."):
        df = get_amazon_data(mkt, key)
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
            analizza_strategia_bsr(df, key)
        else:
            st.error("Dati non disponibili. Prova con una keyword più specifica.")
