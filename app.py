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

# 2. CSS per UI Pulita
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); }
        .keyword-box { padding: 10px; background-color: #e8f4f8; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #00a8cc;}
    </style>
""", unsafe_allow_html=True)

# LA TUA CHIAVE API
API_KEY = "ce57dc2330590954355f5c12171c7ce9"

# --- FUNZIONI DI CALCOLO AVANZATE ---

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
    """Genera sotto-nicchie profittevoli basate sulla keyword originale"""
    kw = keyword.lower().strip()
    return [
        f"**{kw.title()} per Principianti:** Il target più ampio che cerca guide base.",
        f"**Esercizi di {kw.title()} / Workbook:** Altamente profittevole, le persone amano i libri pratici in cui scrivere.",
        f"**{kw.title()} per Donne / Uomini / Ragazzi:** Specializzare il target abbassa drasticamente la concorrenza.",
        f"**Manuale Completo di {kw.title()}:** Posiziona il tuo libro come l'unica risorsa definitiva, permettendoti di alzare il prezzo (es. 19.90€).",
        f"**Bundle: {kw.title()} (3 in 1):** Unisci tre argomenti correlati. Distrugge i concorrenti che vendono libri singoli a basso costo."
    ]

# --- CORE SCRAPER CON DEEP SCAN ---

def get_amazon_data(marketplace, keyword, pagine, colore):
    domains = {
        "Italia": "amazon.it", "USA": "amazon.com", "Spagna": "amazon.es", 
        "Francia": "amazon.fr", "Germania": "amazon.de"
    }
    domain = domains.get(marketplace, "amazon.it")
    country = 'it' if marketplace == "Italia" else 'us'
    target_url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}&i=stripbooks"
    
    payload = {'api_key': API_KEY, 'url': target_url, 'render': 'true', 'country_code': country}
    
    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        if res.status_code != 200: return None
            
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        items = soup.find_all('div', {'data-component-type': 's-search-result'})[:10]
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        for i, item in enumerate(items):
            title = item.h2.text.strip() if item.h2 else "N/A"
            progress_text.info(f"🔍 Scansione profonda: Analizzando il libro {i+1}/10... ({title[:30]}...)")
            
            img_tag = item.find('img', class_='s-image')
            cover_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else "https://via.placeholder.com/150?text=No+Cover"
            
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
                payload_deep = {'api_key': API_KEY, 'url': book_url, 'country_code': country}
                
                try:
                    res_deep = requests.get('http://api.scraperapi.com', params=payload_deep)
                    if res_deep.status_code == 200:
                        deep_soup = BeautifulSoup(res_deep.text, 'html.parser')
                        deep_text = deep_soup.get_text().lower()
                        
                        bsr_match = re.search(r'(?:n\.|#)\s*([0-9.,]+)\s*in', deep_text)
                        if bsr_match:
                            try: bsr = int(bsr_match.group(1).replace('.', '').replace(',', ''))
                            except: bsr = 0
                                
                        is_self_pub = "indipendentemente pubblicato" in deep_text or "independently published" in deep_text
                except Exception as e:
                    pass
            
            vendite_stimate = stima_vendite_mensili(bsr)
            royalty = calcola_royalty_netta(price, pagine, colore)
            utile_mensile = vendite_stimate * royalty
            
            results.append({
                "Copertina": cover_url, 
                "Libro": title, 
                "Prezzo (€/$)": price, 
                "Royalty Netta": str(royalty), # Salvato come stringa base per evitare crash UI
                "Recensioni": reviews, 
                "BSR": bsr if bsr > 0 else "N/D",
                "Vendite/Mese": vendite_stimate,
                "Utile/Mese Stimato": str(round(utile_mensile, 2)), # Salvato come stringa base
                "Self-Published": "Sì" if is_self_pub else "Sconosciuto/Tradizionale"
            })
            
            progress_bar.progress((i + 1) / len(items))
            
        progress_text.empty()
        progress_bar.empty()
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Errore: {e}")
        return None

def calcola_opportunity_score(prezzo, recensioni, bsr, royalty):
    score = 50 
    if prezzo > 14.90: score += 15
    elif prezzo < 9.90: score -= 20
    if 10 < recensioni < 150: score += 20
    elif recensioni > 1000: score -= 30
    if 100 < bsr < 50000: score += 20
    elif bsr > 300000: score -= 20
    if royalty > 4.0: score += 15
    elif royalty < 1.5: score -= 15
    return max(0, min(100, score))

def analizza_strategia_pro(df, keyword, obiettivo):
    if df.empty: return
    
    # PULIZIA DATI SICURA (Bug Fix per evitare che il report sparisca)
    df_calc = df.copy()
    df_calc["Royalty Num"] = pd.to_numeric(df_calc["Royalty Netta"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df_calc["Utile Num"] = pd.to_numeric(df_calc["Utile/Mese Stimato"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    avg_price = df[df["Prezzo (€/$)"] > 0]["Prezzo (€/$)"].mean()
    avg_royalty = df_calc["Royalty Num"].mean()
    avg_revs = df["Recensioni"].mean()
    
    valid_bsrs = df[df["BSR"] != "N/D"]["BSR"].astype(int)
    avg_bsr = valid_bsrs.mean() if not valid_bsrs.empty else 0
    tot_utile = df_calc["Utile Num"].sum()
    
    self_pub_count = len(df[df["Self-Published"] == "Sì"])
    self_pub_ratio = (self_pub_count / len(df)) * 100

    opp_score = calcola_opportunity_score(avg_price, avg_revs, avg_bsr if avg_bsr > 0 else 150000, avg_royalty)

    st.header(f"📊 Report Professionale KDP: {keyword.upper()}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prezzo Medio", f"{avg_price:.2f} €")
    c2.metric("Royalty Media", f"{avg_royalty:.2f} €")
    c3.metric("Mercato (Top 10)", f"{int(tot_utile)} €/mese")
    c4.metric("Opportunity Score", f"{int(opp_score)}/100")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🕵️ Analisi Dominanza (KDP vs Tradizionale)")
        if self_pub_ratio >= 40:
            st.success(f"✅ **Ecosistema KDP Favorevole:** Abbiamo rilevato un {int(self_pub_ratio)}% di libri chiaramente Self-Published nella Top 10. Amazon premia gli autori indipendenti in questa nicchia.")
        elif self_pub_ratio > 0:
            st.info(f"⚖️ **Ecosistema Misto:** Ci sono autori Self-Published ({int(self_pub_ratio)}%) ma anche case editrici. Puoi competere, ma la tua copertina dovrà sembrare Premium.")
        else:
            st.warning("⚠️ **Dominio Case Editrici:** Nessun libro Self-Published rilevato in cima. Entrare qui richiede un brand forte o un posizionamento molto specifico.")
        
        st.subheader(f"🎯 Verdetto: {obiettivo}")
        if obiettivo == "Reddito Passivo (Royalty)":
            if opp_score >= 70:
                st.success(f"**🟢 SEMAFORO VERDE:** Nicchia eccellente. Il mercato muove circa {int(tot_utile)}€ netti al mese tra i leader. Procedi puntando a una royalty di almeno {avg_royalty:.2f}€.")
            elif avg_royalty < 2.0:
                st.error(f"**🔴 PROBLEMA MARGINI:** Anche vendendo, la royalty netta media è di soli {avg_royalty:.2f}€. Aumenta il valore percepito (es. Workbook incluso) e vendi a 15.90€+.")
            else:
                st.warning("**🟡 COMPETIZIONE ALTA:** C'è mercato, ma i leader sono forti. Sfrutta le keyword alternative qui accanto.")

    with col2:
        # NUOVA FUNZIONE: Suggerimento Keyword Alternative
        st.subheader("💡 Generatore Nicchie Alternative")
        st.write(f"Se la parola chiave **'{keyword}'** risulta troppo competitiva o ha margini bassi, ecco 5 angoli di attacco consigliati:")
        
        alternative = genera_keyword_alternative(keyword)
        for alt in alternative:
            st.markdown(f"<div class='keyword-box'>{alt}</div>", unsafe_allow_html=True)

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎯 KDP Expert Ultimate")
    
    if st.button("🔄 Nuova Ricerca", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.subheader("1. Ricerca Intelligente")
    mkt = st.selectbox("Marketplace", ["Italia", "USA", "Spagna", "Francia", "Germania"])
    key = st.text_input("Inserisci Keyword Strategica")
    
    # NUOVO: Bussola della Ricerca
    with st.expander("🧭 Bussola della Ricerca"):
        st.markdown("""
        **Non cercare parole generiche!** ❌ *Sbagliato:* "Dieta"  
        ✅ *Giusto:* "Dieta chetogenica per over 50"  
        
        Usa la formula: **[Argomento] + [Per Chi] + [Beneficio]** per trovare le nicchie in cui è più facile posizionarsi.
        """)
    
    st.markdown("---")
    st.subheader("2. Dati Libro (Per Royalty)")
    pagine = st.number_input("Stima Pagine del tuo libro", min_value=24, max_value=800, value=120, step=10)
    colore = st.selectbox("Interno", ["Bianco e Nero", "A Colori (Premium)"])
    
    st.markdown("---")
    st.subheader("3. Obiettivo")
    obiettivo = st.radio(
        "Scopo della pubblicazione:",
        ["Reddito Passivo (Royalty)", "Lead Generation (Acquisire clienti)", "Costruzione Brand / Authority"]
    )
        
    run = st.button("AVVIA ANALISI DEFINITIVA", type="primary", use_container_width=True)

# --- LOGICA MAIN ---
if run and key:
    st.info("💡 Attenzione: La scansione profonda per estrarre BSR, vendite stimate e copertine richiede circa 45-60 secondi.")
    with st.spinner("Connessione ai server di Amazon in corso..."):
        df = get_amazon_data(mkt, key, pagine, colore)
        
        if df is not None and not df.empty:
            st.success("Analisi profonda completata con successo!")
            
            # Per l'interfaccia utente aggiungiamo il simbolo € solo nella visualizzazione
            df_display = df.copy()
            df_display["Royalty Netta"] = df_display["Royalty Netta"] + " €"
            df_display["Utile/Mese Stimato"] = df_display["Utile/Mese Stimato"] + " €"
            
            st.dataframe(
                df_display, 
                column_config={
                    "Copertina": st.column_config.ImageColumn(
                        "Cover", help="Immagine di copertina (Amazon)"
                    )
                },
                use_container_width=True,
                hide_index=True
            )
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Scarica Dati (CSV)",
                data=csv,
                file_name=f"Analisi_KDP_{key.replace(' ', '_')}.csv",
                mime="text/csv",
            )
            
            st.markdown("---")
            # Il report ora è protetto da errori matematici
            analizza_strategia_pro(df, key, obiettivo)
        else:
            st.error("Dati non disponibili. Prova con una keyword più specifica.")
