import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 16.6", page_icon="💰", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .program-title { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800; border-bottom: 2px solid #30363d; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        .profit-card { background: #1c2128; border: 1px solid #30363d; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .status-green { color: #3fb950; font-weight: bold; }
        .status-yellow { color: #d29922; font-weight: bold; }
        .status-red { color: #f85149; font-weight: bold; }
        .ai-panel { background-color: #161b22; padding: 2rem; border-radius: 12px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Intelligence Hub v16.6 💰</div>", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state.raw_data = None

# ==============================================================================
# 2. LOGICA DI ESTRAZIONE (BACKEND AGGIORNATO)
# ==============================================================================
with st.sidebar:
    st.header("📥 Configurazione")
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    files = st.file_uploader("Carica CSV Amazon", type=["csv"], accept_multiple_files=True)

    if st.button("📊 AVVIA ANALISI PROFITTO", type="primary"):
        if files:
            all_dfs = []
            for f in files:
                df_raw = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip')
                cols = df_raw.columns.tolist()
                temp = pd.DataFrame(index=df_raw.index)
                
                bsrs, authors = [], []
                for _, row in df_raw.iterrows():
                    # Radar BSR Reale (Max Value)
                    ranks = []
                    for v in row.dropna():
                        v_s = str(v)
                        if '#' in v_s:
                            matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*|\d+)', v_s)
                            for m in matches:
                                ranks.append(int(m.replace('.','').replace(',','')))
                    bsrs.append(max(ranks) if ranks else np.nan)
                    
                    # Logic Autore
                    auth = "N/D"
                    for i, c in enumerate(cols):
                        if "author" in str(c).lower() or str(row[c]).lower() == "author":
                            auth = str(row[cols[i+1]]) if str(row[c]).lower() == "author" and i+1 < len(cols) else str(row[c])
                            break
                    authors.append(re.sub(r'^(di|by|Author:)\s+', '', auth, flags=re.IGNORECASE))

                temp['BSR'] = bsrs
                temp['Autore'] = authors
                
                # --- AGGIUNTA RIGHE RICHIESTE ---
                
                # Mapping Copertina (Immagine)
                img_c = next((c for c in cols if any(k in c.lower() for k in ['s-image src', 'image', 'copertina', 'src'])), None)
                temp['Copertina'] = df_raw[img_c] if img_c else None

                # Mapping Titolo
                tit_c = next((c for c in cols if any(k in c.lower() for k in ['a-size-medium', 'title', 'titolo', 'name'])), None)
                temp['Titolo'] = df_raw[tit_c] if tit_c else "N/D"

                # Mapping Prezzo
                p_c = next((c for c in cols if any(k in c.lower() for k in ['price', 'prezzo', 'offscreen'])), None)
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                # Mapping Recensioni
                rev_c = next((c for c in cols if any(k in c.lower() for k in ['review', 'voti', 'rating', 'a-size-base'])), None)
                if rev_c:
                    def clean_rev(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[rev_c].apply(clean_rev)
                else: temp['Recensioni'] = np.nan
                
                all_dfs.append(temp)
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.rerun()

# ==============================================================================
# 3. PROFITABILITY ANALYSIS
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data.copy()
    avg_bsr = df['BSR'].mean()
    avg_price = df['Prezzo'].mean()
    
    st.markdown("### 📈 Valutazione Ragionata della Nicchia")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if avg_bsr < 20000:
            status, color, desc = "MOLTO ALTO", "status-green", "Domanda massiccia. Vendite quotidiane garantite."
        elif avg_bsr < 80000:
            status, color, desc = "BUONO / OTTIMO", "status-green", "Nicchia sana. Ottimo bilanciamento domanda/concorrenza."
        elif avg_bsr < 150000:
            status, color, desc = "MODERATO", "status-yellow", "Richiede marketing attivo o una sottocategoria specifica."
        else:
            status, color, desc = "BASSO", "status-red", "Poco movimento. Rischio di invenduto elevato."
            
        st.markdown(f"<div class='profit-card'><p style='margin:0; font-size:0.9rem; color:#8b949e;'>POTENZIALE VENDITE</p><h2 class='{color}'>{status}</h2><p style='font-size:0.85rem;'>{desc}</p></div>", unsafe_allow_html=True)

    with col2:
        if avg_price > 14.0:
            p_status, p_color = "MARGINE ALTO", "status-green"
        elif avg_price > 9.0:
            p_status, p_color = "MARGINE MEDIO", "status-yellow"
        else:
            p_status, p_color = "MARGINE BASSO", "status-red"
            
        st.markdown(f"<div class='profit-card'><p style='margin:0; font-size:0.9rem; color:#8b949e;'>PROFILO ECONOMICO</p><h2 class='{p_color}'>{p_status}</h2><p style='font-size:0.85rem;'>Basato su un prezzo medio di {avg_price:.2f}€.</p></div>", unsafe_allow_html=True)

    with col3:
        if avg_bsr < 80000 and avg_price > 12:
            verdict = "ECCELLENTE: Entra ora."
        elif avg_bsr < 100000:
            verdict = "INTERESSANTE: Valuta le Ads."
        else:
            verdict = "CAUTELA: Nicchia satura o ferma."
            
        st.markdown(f"<div class='profit-card'><p style='margin:0; font-size:0.9rem; color:#8b949e;'>VERDETTO OMNI-REASONER</p><h2 style='color:#58a6ff;'>{verdict}</h2><p style='font-size:0.85rem;'>Analisi calcolata su {len(df)} libri concorrenti.</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================================================
    # 4. STEP 2: AI STRATEGY LAB & DATA TABLE (AGGIORNATA CON COLONNE)
    # ==============================================================================
    col_table, col_ai = st.columns([7, 3])
    
    with col_table:
        st.markdown("<p class='section-title'>Dati Estratti (BSR Globale Corretto)</p>", unsafe_allow_html=True)
        
        # Selezione ordinata delle colonne richieste
        display_cols = ["Copertina", "Titolo", "BSR", "Prezzo", "Autore", "Recensioni"]
        
        st.dataframe(
            df[display_cols], 
            use_container_width=True, 
            hide_index=True,
            height=600,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover", width="small"),
                "Titolo": st.column_config.TextColumn("Titolo Libro", width="large"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "Recensioni": st.column_config.NumberColumn("Recensioni", format="%d"),
                "BSR": st.column_config.NumberColumn("BSR Rank", format="%d")
            }
        )

    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        nicchia_target = st.text_input("Nicchia Target")
        if st.button("🪄 GENERA STRATEGIA"):
            st.write(f"Analisi AI per {nicchia_target} basata su BSR medio di {int(avg_bsr)}...")
        st.markdown("</div>", unsafe_allow_html=True)
