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
    
    try:import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# Configurazione Pagina
st.set_page_config(page_title="KDP Analyzer Pro", page_icon="📈", layout="wide")

# LA TUA CHIAVE API (Inserita nel codice come richiesto)
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

def get_amazon_data(marketplace, keyword):
    domains = {
        "Italia": "amazon.it",
        "USA": "amazon.com",
        "Spagna": "amazon.es",
        "Francia": "amazon.fr",
        "Germania": "amazon.de"
    }
    
    domain = domains.get(marketplace, "amazon.it")
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    # Richiesta tramite ScraperAPI per evitare blocchi
    payload = {
        'api_key': API_KEY, 
        'url': target_url, 
        'render': 'true', 
        'country_code': 'it' if marketplace == "Italia" else 'us'
    }
    
    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        
        if res.status_code != 200: 
            return None
            
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        # Scansione risultati
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
            
            # Logica base libro singolo
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

def analizza_strategia(df, keyword):
    """Analizza il dataframe e genera un consiglio strategico."""
    if df.empty:
        return
        
    prezzo_medio = df["Prezzo (€/$)"].mean()
    recensioni_medie = df["Recensioni"].mean()
    libri_saturi = len(df[df["Potenziale"] == "Satura (Alta concorrenza)"])
    libri_ottimi = len(df[df["Potenziale"] == "Ottima (Margine + Domanda)"])
    
    st.subheader(f"🧠 Analisi Strategica per: '{keyword.upper()}'")
    
    # 1. Nicchia Satura / Molto Competitiva
    if recensioni_medie > 800 or libri_saturi > (len(df) / 3):
        st.error("🔴 **Verdetto: Nicchia Troppo Competitiva**")
        st.write("I leader di questa pagina hanno centinaia (o migliaia) di recensioni. Entrare frontalmente con lo stesso identico argomento richiederebbe un budget Amazon Ads enorme.")
        st.info(f"💡 **Il Consiglio:** Usa il *Cross-Niching*. Non pubblicare un generico '{keyword}', ma specializzati. Prova a cercare: **'{keyword} per principianti'**, **'{keyword} per donne'**, o unisci l'argomento a una professione specifica. Cerca un sottomercato in cui i lettori non trovano un libro dedicato.")
    
    # 2. Nicchia a Bassi Margini
    elif prezzo_medio > 0 and prezzo_medio < 11.0:
        st.warning("🟡 **Verdetto: Problema di Marginalità**")
        st.write("La concorrenza potrebbe essere abbordabile, ma i prezzi medi sono troppo bassi. Pubblicando un libro normale faticherai ad andare in profitto con le sponsorizzate.")
        st.info("💡 **Il Consiglio:** Esci dalla guerra dei prezzi al ribasso creando un prodotto *Premium*. Valuta di pubblicare un **Bundle (2 o 3 libri in 1)**, un'edizione con copertina rigida o interno a colori, posizionando il tuo libro a 14.90€ o più.")
    
    # 3. Nicchia Ottima ("Buco di mercato")
    elif libri_ottimi >= 2 or (prezzo_medio >= 12 and 50 < recensioni_medie < 500):
        st.success("🟢 **Verdetto: Semaforo Verde (Buco di Mercato!)**")
        st.write("Ottimi segnali! Ci sono libri in prima pagina che vendono a buoni prezzi e la media delle recensioni indica che il mercato non è monopolizzato da vecchi colossi.")
        st.info("💡 **Il Consiglio:** Questa nicchia è attaccabile! Vai su Amazon, apri i 3 libri che vendono di più e **leggi le loro recensioni da 2 e 3 stelle**. Scopri cosa manca (es. 'Mancavano esercizi pratici', 'Scritto troppo in piccolo') e crea il tuo libro risolvendo esattamente quel difetto.")
    
    # 4. Dati Misti o Insufficienti
    else:
        st.info("🔵 **Verdetto: Nicchia Incerta**")
        st.write("I dati sono molto misti o il numero di ricerche per questa parola chiave potrebbe essere basso.")
        st.info("💡 **Il Consiglio:** Prima di scrivere il libro, assicurati che la gente stia effettivamente cercando questo argomento. Usa la barra di completamento automatico di Amazon per vedere se ci sono parole chiave correlate suggerite.")

# --- Interfaccia Utente ---
st.title("🚀 Amazon KDP Niche Analyzer")

with st.sidebar:
    st.header("Impostazioni")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key = st.text_input("Parola Chiave (es. 'diario della gratitudine')")
    run = st.button("Analizza e Trova l'Angolo", type="primary")
    
    st.markdown("---")
    st.caption("🔒 Connessione protetta via ScraperAPI (Key preconfigurata).")

if run:
    if key:
        with st.spinner(f"Scansione ed elaborazione strategica in corso su {mkt}... (~15 sec)"):
            df = get_amazon_data(mkt, key)
            
            if df is not None and not df.empty:
                # 1. Mostra i dati
                st.success(f"Dati estratti con successo: {len(df)} concorrenti trovati.")
                st.dataframe(df, use_container_width=True)
                
                st.markdown("---")
                
                # 2. Mostra il consiglio strategico
                analizza_strategia(df, key)
            else:
                st.error("Scansione fallita. Nessun risultato o blocco da parte di Amazon.")
    else:
        st.warning("Inserisci una parola chiave per iniziare.")
