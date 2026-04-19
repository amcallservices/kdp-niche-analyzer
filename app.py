import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# 1. Configurazione Pagina
st.set_page_config(
    page_title="KDP Niche Analyzer Ultimate", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CSS per UI e Colori Professionali
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        .stMetric { background-color: #f8f9fa !important; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); }
        [data-testid="stMetricValue"] { color: #1e1e1e !important; }
        [data-testid="stMetricLabel"] { color: #444444 !important; font-weight: bold; }
        .keyword-box { padding: 12px; background-color: #e8f4f8; color: #003344 !important; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #00a8cc; font-weight: 500;}
        .generated-kw-box { background-color: #ffffff; border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-top: 5px; cursor: pointer; border-left: 3px solid #ff9900; }
    </style>
""", unsafe_allow_html=True)

# LA TUA CHIAVE API
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

# Inizializzazione Session State per la Keyword automatica
if 'target_keyword' not in st.session_state:
    st.session_state['target_keyword'] = ""

# --- FUNZIONI DI CALCOLO ---

def stima_vendite_mensili(bsr):
    if bsr <= 0: return 0
    if bsr <= 100: return 2000
    if bsr <= 1000: return 500
    if bsr <= 5000: return 150
    if bsr <= 10000: return 80
    if bsr <= 30000: return 30
    if bsr <= 100000: return 10
    if bsr <= 250000: return 3
    return 0

def calcola_royalty_netta(prezzo, pagine, colore):
    if prezzo <= 0: return 0.0
    if colore == "Bianco e Nero":
        costo_stampa = 2.15 if pagine <= 108 else 0.60 + (pagine * 0.012)
    else: 
        costo_stampa = 0.60 + (pagine * 0.042)
        if costo_stampa < 2.15: costo_stampa = 2.15
    royalty = (prezzo * 0.60) - costo_stampa
    return round(royalty, 2) if royalty > 0 else 0.0

def genera_keyword_alternative(keyword):
    kw = keyword.lower().strip()
    return [
        f"<b>{kw.title()} per Principianti:</b> Target ampio, guida step-by-step.",
        f"<b>Esercizi di {kw.title()} / Workbook:</b> Formato pratico ad altissima rotazione.",
        f"<b>{kw.title()} per Donne / Senior:</b> Nicchia demografica a bassa competizione.",
        f"<b>Manuale Completo di {kw.title()}:</b> Posizionamento Premium (Prezzi alti).",
        f"<b>Bundle: {kw.title()} (3 in 1):</b> Dominanza totale del mercato."
    ]

# --- CORE SCRAPER CON DEEP SCAN ---

def get_amazon_data(marketplace, keyword, pagine, colore):
    domains = {"Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", "Francia": "amazon.fr", "Germania": "amazon.de"}
    domain = domains.get(marketplace, "amazon.it")
    country = 'it' if marketplace == "Italia" else 'us'
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    payload = {'api_key': API_KEY, 'url': target_url, 'render': 'true', 'country_code': country}
    
    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        if res.status_code != 200: return None
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:15]
        
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            progress_text.info(f"🔍 Analisi libro {i+1}/{len(items)}: {title[:30]}...")
            
            img_tag = item.find('img', class_='s-image')
            cover_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ""
            
            p_whole = item.find('span', 'a-price-whole')
            p_frac = item.find('span', 'a-price-fraction')
            price = 0.0
            if p_whole and p_frac:
                try: price = float(f"{p_whole.text.replace(',','').replace('.','')}.{p_frac.text}")
                except: price = 0.0
            
            rev_tag = item.find('span', {'class': 'a-size-base s-underline-text'})
            reviews = int(re.sub(r'\D', '', rev_tag.text)) if rev_tag else 0
            
            bsr = 0
            is_self_pub = False
            link_tag = item.find('a', class_='a-link-normal s-no-outline')
            
            if link_tag and 'href' in link_tag.attrs:
                book_url = f"https://www.{domain}" + link_tag['href']
                res_deep = requests.get('http://api.scraperapi.com', params={'api_key': API_KEY, 'url': book_url, 'country_code': country})
                if res_deep.status_code == 200:
                    deep_text = BeautifulSoup(res_deep.text, 'html.parser').get_text().lower()
                    bsr_match = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', deep_text)
                    if bsr_match:
                        try: bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
                        except: bsr = 0
                    is_self_pub = "indipendentemente pubblicato" in deep_text or "independently published" in deep_text
            
            vendite_stimate = stima_vendite_mensili(bsr)
            royalty = calcola_royalty_netta(price, pagine, colore)
            results.append({
                "Copertina": cover_url, "Libro": title, "Prezzo (€/$)": price, 
                "Royalty Netta": str(royalty), "Recensioni": reviews, "BSR": bsr if bsr > 0 else "N/D",
                "Vendite/Mese": vendite_stimate, "Utile/Mese Stimato": str(round(vendite_stimate * royalty, 2)),
                "Self-Published": "Sì" if is_self_pub else "No"
            })
            progress_bar.progress((i + 1) / len(items))
            
        progress_text.empty()
        progress_bar.empty()
        return pd.DataFrame(results)
    except: return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎯 KDP Analyzer Gold")
    
    if st.button("🔄 Nuova Ricerca", use_container_width=True):
        st.session_state['target_keyword'] = ""
        st.rerun()
    
    st.markdown("---")
    
    # --- SISTEMA GENERATORE KEYWORD PROFESSIONALE ---
    st.subheader("🛠️ Generatore Keyword Strategica")
    with st.expander("Sviluppa Nicchia"):
        arg = st.text_input("Argomento:", placeholder="es. Yoga")
        target = st.text_input("Target:", placeholder="es. Anziani")
        ben = st.text_input("Beneficio:", placeholder="es. Mobilità articolare")
        
        if arg and target and ben:
            st.write("Scegli un angolo d'attacco:")
            
            # Opzione 1: Strategica
            k1 = f"{arg} per {target}: {ben}"
            if st.button(f"👉 {k1}"):
                st.session_state['target_keyword'] = k1
                st.rerun()
                
            # Opzione 2: Pratica
            k2 = f"Esercizi di {arg} per {target} per migliorare {ben}"
            if st.button(f"👉 {k2}"):
                st.session_state['target_keyword'] = k2
                st.rerun()
                
            # Opzione 3: Guida
            k3 = f"Manuale di {arg} per {target}: Come ottenere {ben}"
            if st.button(f"👉 {k3}"):
                st.session_state['target_keyword'] = k3
                st.rerun()

    st.markdown("---")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    
    # Campo di input collegato al session state per il riempimento automatico
    key = st.text_input("🔍 Incolla qui la Keyword per l'Analisi", value=st.session_state['target_keyword'])
    
    pagine = st.number_input("Pagine libro", min_value=24, value=120)
    colore = st.selectbox("Interno", ["Bianco e Nero", "A Colori (Premium)"])
    obiettivo = st.radio("Obiettivo:", ["Reddito Passivo (Royalty)", "Lead Generation", "Brand / Authority"])
    
    run = st.button("AVVIA ANALISI", type="primary", use_container_width=True)

# --- LOGICA MAIN ---
if run and key:
    st.info(f"Avvio analisi su 15 libri per '{key}'...")
    df = get_amazon_data(mkt, key, pagine, colore)
    
    if df is not None and not df.empty:
        st.success("Dati estratti!")
        st.dataframe(df, column_config={"Copertina": st.column_config.ImageColumn("Cover")}, use_container_width=True, hide_index=True)
        
        # Report Professionale (Semplificato per stabilità)
        df_calc = df.copy()
        df_calc["Utile Num"] = pd.to_numeric(df_calc["Utile/Mese Stimato"]).fillna(0)
        tot_utile = df_calc["Utile Num"].sum()
        
        st.markdown("---")
        st.header(f"📊 Report Professionale KDP: {key.upper()}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Prezzo Medio", f"{df['Prezzo (€/$)'].mean():.2f} €")
        c2.metric("Mercato (Top 15)", f"{int(tot_utile)} €/mese")
        c3.metric("Self-Pub Ratio", f"{int((len(df[df['Self-Published'] == 'Sì']) / len(df)) * 100)}%")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎯 Verdetto Strategico")
            if tot_utile > 500: st.success("✅ Nicchia Profittevole rilevata.")
            else: st.warning("⚠️ Volumi di vendita bassi o prezzi non ottimizzati.")
            
        with col2:
            st.subheader("💡 Keyword Alternative")
            for alt in genera_keyword_alternative(key):
                st.markdown(f"<div class='keyword-box'>{alt}</div>", unsafe_allow_html=True)
