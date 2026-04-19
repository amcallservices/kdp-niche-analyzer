import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

st.set_page_config(page_title="KDP Analyzer Pro", page_icon="📈", layout="wide")

def get_amazon_data(marketplace, keyword, api_key):
    domains = {
        "Italia": "amazon.it",
        "USA": "amazon.com",
        "Spagna": "amazon.es",
        "Francia": "amazon.fr",
        "Germania": "amazon.de"
    }
    
    domain = domains.get(marketplace, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    # Integrazione ScraperAPI: Maschera la richiesta per aggirare i blocchi
    payload = {
        'api_key': api_key, 
        'url': target_url, 
        'render': 'true', # Risolve JavaScript se necessario
        'country_code': 'it' if marketplace == "Italia" else 'us'
    }
    
    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        
        if res.status_code != 200: 
            return None
            
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        for item in soup.find_all('div', {'data-component-type': 's-search-result'}):
            title_tag = item.h2
            title = title_tag.text.strip() if title_tag else "N/A"
            
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = 0.0
            if p_whole and p_frac:
                try:
                    price_str = f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}"
                    price = float(price_str)
                except:
                    price = 0.0
            
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = 0
            if rev_tag:
                try:
                    reviews = int(re.sub(r'\D', '', rev_tag.text))
                except:
                    reviews = 0
            
            status = "Da valutare"
            if 12 <= price <= 25 and 50 < reviews < 500:
                status = "Ottima (Margine + Domanda)"
            elif reviews > 1000:
                status = "Satura (Alta concorrenza)"
            elif price < 10 and price > 0:
                status = "Bassa (Margini scarsi)"
            
            results.append({
                "Libro": title, 
                "Prezzo (€/$)": price, 
                "Recensioni": reviews, 
                "Potenziale": status
            })
            
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
        return None

# --- Interfaccia Utente ---
st.title("🚀 Amazon KDP Niche Analyzer")
st.info("Connessione protetta via ScraperAPI per evitare i blocchi di Amazon.")

with st.sidebar:
    st.header("Impostazioni")
    api_key = st.text_input("Inserisci la tua ScraperAPI Key", type="password")
    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key = st.text_input("Parola Chiave (es. 'diario della gratitudine')")
    run = st.button("Analizza Mercato", type="primary")

if run:
    if not api_key:
        st.error("⚠️ Inserisci la tua ScraperAPI Key nella barra laterale per procedere.")
    elif key:
        with st.spinner(f"Aggiramento blocchi in corso su {mkt}... (potrebbe richiedere 10-15 secondi)"):
            df = get_amazon_data(mkt, key, api_key)
            
            if df is not None and not df.empty:
                st.success(f"Trovati {len(df)} risultati per '{key}'.")
                st.dataframe(df, use_container_width=True)
            else:
                st.error("La scansione è fallita. Verifica che la API Key sia corretta.")
    else:
        st.warning("Inserisci una parola chiave per iniziare.")
