import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# Configurazione Pagina
st.set_page_config(page_title="KDP Analyzer Pro", page_icon="📈", layout="wide")

def get_amazon_data(marketplace, keyword):
    domains = {
        "Italia": "amazon.it",
        "USA": "amazon.com",
        "Spagna": "amazon.es",
        "Francia": "amazon.fr",
        "Germania": "amazon.de"
    }
    
    domain = domains.get(marketplace, "amazon.it")
    url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    # Headers per simulare un browser reale
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8"
    }
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200: 
            return None
            
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        # Analizza i risultati di ricerca
        for item in soup.find_all('div', {'data-component-type': 's-search-result'}):
            title_tag = item.h2
            title = title_tag.text.strip() if title_tag else "N/A"
            
            # Estrazione Prezzo
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = 0.0
            if p_whole and p_frac:
                try:
                    price_str = f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}"
                    price = float(price_str)
                except:
                    price = 0.0
            
            # Estrazione Recensioni
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = 0
            if rev_tag:
                try:
                    reviews = int(re.sub(r'\D', '', rev_tag.text))
                except:
                    reviews = 0
            
            # Logica di Profitto basata sul Manuale Nicchie Profittevoli
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
        st.error(f"Errore durante l'estrazione: {e}")
        return None

# --- Interfaccia Utente ---
st.title("🚀 Amazon KDP Niche Analyzer")
st.info("Analisi basata sui criteri di redditività del *Manuale delle Nicchie Profittevoli*.")

with st.sidebar:
    st.header("Impostazioni di Ricerca")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key = st.text_input("Parola Chiave (es. 'diario della gratitudine')")
    run = st.button("Analizza Mercato", type="primary")

if run:
    if key:
        with st.spinner(f"Scansione in corso su {mkt}..."):
            time.sleep(1) # Pausa per non sovraccaricare il server
            df = get_amazon_data(mkt, key)
            
            if df is not None and not df.empty:
                st.success(f"Trovati {len(df)} risultati per '{key}'.")
                st.dataframe(df, use_container_width=True)
            else:
                st.error("Nessun risultato trovato. Amazon potrebbe aver bloccato la richiesta (CAPTCHA) o la parola chiave è errata.")
    else:
        st.warning("Inserisci una parola chiave per iniziare.")
