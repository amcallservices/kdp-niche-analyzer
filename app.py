import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 16.8", page_icon="💰", layout="wide")

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
        [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Intelligence Hub v16.8 💰</div>", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. LOGICA DI ESTRAZIONE (BACKEND ANTI-CRASH)
# ==============================================================================
with st.sidebar:
    st.header("📥 Configurazione")
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    files = st.file_uploader("Carica CSV Amazon", type=["csv"], accept_multiple_files=True)

    if st.button("📊 AVVIA ANALISI PROFITTO", type="primary"):
        if files:
            all_dfs = []
            for f in files:
                try:
                    df_raw = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip')
                except:
                    f.seek(0)
                    df_raw = pd.read_csv(f, sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')
                
                cols = df_raw.columns.tolist()
                temp = pd.DataFrame(index=df_raw.index)
                
                target_cols = ["Copertina", "Titolo", "BSR", "Prezzo", "Autore", "Recensioni"]
                for c in target_cols:
                    temp[c] = np.nan

                bsrs, authors = [], []
                for _, row in df_raw.iterrows():
                    ranks = []
                    for v in row.dropna():
                        v_s = str(v)
                        if '#' in v_s:
                            matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*|\d+)', v_s)
                            for m in matches:
                                try:
                                    ranks.append(int(m.replace('.','').replace(',','')))
                                except: continue
                    bsrs.append(max(ranks) if ranks else np.nan)
                    
                    auth = "N/D"
                    for i, c in enumerate(cols):
                        cell_val = str(row[c])
                        if "author" in str(c).lower() or cell_val.lower() == "author":
                            if cell_val.lower() == "author" and i+1 < len(cols):
                                auth = str(row[cols[i+1]])
                            else:
                                auth = cell_val
                            break
                    authors.append(re.sub(r'^(di|by|Author:)\s+', '', auth, flags=re.IGNORECASE))

                temp['BSR'] = bsrs
                temp['Autore'] = authors
                
                img_c = next((c for c in cols if any(k in c.lower() for k in ['s-image src', 'image', 'copertina', 'src', 'dynamic-image'])), None)
                if img_c: temp['Copertina'] = df_raw[img_c]

                tit_c = next((c for c in cols if any(k in c.lower() for k in ['a-size-medium', 'title', 'titolo', 'name', 'clamp'])), None)
                if tit_c: temp['Titolo'] = df_raw[tit_c]

                p_c = next((c for c in cols if any(k in c.lower() for k in ['a-offscreen', 'price', 'prezzo', 'a-price-whole'])), None)
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                rev_c = next((c for c in cols if any(k in c.lower() for k in ['review', 'voti', 'rating', 'a-size-base', 'a-size-small'])), None)
                if rev_c:
                    def clean_rev(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[rev_c].apply(clean_rev)
                
                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'ID', range(1, len(st.session_state.raw_data) + 1))
            st.session_state.suggestions = None
            st.rerun()

    if st.button("🔄 RESET"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. PROFITABILITY ANALYSIS
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data.copy()
    avg_bsr = df['BSR'].mean()
    avg_price = df['Prezzo'].mean()
    
    st.markdown("### 📈 Valutazione Ragionata della Nicchia")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if avg_bsr < 80000: status, color, desc = "PROFITTABILITÀ ALTA", "status-green", "Volume di vendite elevato. Ottima nicchia."
        elif avg_bsr < 150000: status, color, desc = "PROFITTABILITÀ MEDIA", "status-yellow", "Richiede sforzo pubblicitario."
        else: status, color, desc = "PROFITTABILITÀ BASSA", "status-red", "Poche vendite o mercato saturo."
        st.markdown(f"<div class='profit-card'><p style='color:#8b949e;'>VENDITE STIMATE</p><h2 class='{color}'>{status}</h2><p>{desc}</p></div>", unsafe_allow_html=True)

    with c2:
        p_status = "BUON MARGINE" if avg_price > 12 else "BASSO MARGINE"
        p_color = "status-green" if avg_price > 12 else "status-red"
        st.markdown(f<div class='profit-card'><p style='color:#8b949e;'>ECONOMIA</p><h2 class='{p_color}'>{p_status}</h2><p>Prezzo medio: {avg_price:.2f}€</p></div>", unsafe_allow_html=True)

    with c3:
        verdict = "ECCELLENTE" if avg_bsr < 80000 and avg_price > 12 else "VALUTARE"
        st.markdown(f"<div class='profit-card'><p style='color:#8b949e;'>VERDETTO FINALE</p><h2 style='color:#58a6ff;'>{verdict}</h2><p>Analisi su {len(df)} libri.</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================================================
    # 4. TABELLA DATI COMPLETA & STEP 2 AI (AGGIORNATO)
    # ==============================================================================
    col_table, col_ai = st.columns([7, 3])
    
    with col_table:
        st.markdown("<p style='font-weight:bold; font-size:1.2rem;'>Dati Estratti (BSR Globale Corretto)</p>", unsafe_allow_html=True)
        cols_to_show = ["Copertina", "ID", "Titolo", "BSR", "Prezzo", "Autore", "Recensioni"]
        st.dataframe(df[cols_to_show], use_container_width=True, hide_index=True, height=600,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover", width="small"),
                "Titolo": st.column_config.TextColumn("Titolo", width="large"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "BSR": st.column_config.NumberColumn("BSR Rank", format="%d")
            }
        )

    with col_ai:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        nicchia_target = st.text_input("Nicchia analizzata")
        
        # --- LOGICA AI AGGIUNTA QUI ---
        if st.button("🪄 GENERA STRATEGIA"):
            if nicchia_target:
                with st.spinner("L'AI sta analizzando la nicchia e i concorrenti..."):
                    try:
                        # Recupera i primi 5 titoli della tabella per dare contesto all'IA
                        top_competitors = ", ".join(df['Titolo'].dropna().head(5).tolist())
                        
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        
                        system_prompt = f"Sei un esperto mondiale di marketing su Amazon KDP per il mercato {mkt}."
                        user_prompt = f"""
                        Analizza la nicchia: "{nicchia_target}".
                        Dati rilevati: BSR medio di {int(avg_bsr)} e Prezzo medio di {avg_price:.2f}€.
                        Competitors principali: {top_competitors}.

                        Genera una strategia vincente:
                        1. 5 Potenziali Titoli magnetici ad alta conversione.
                        2. 5 Sottotitoli SEO-Optimized.
                        3. Breve consiglio su quale 'angolo' di marketing usare per battere questi concorrenti.
                        """

                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ]
                        )
                        st.session_state.suggestions = response.choices[0].message.content
                    except Exception as e:
                        st.error(f"Errore: {e}")
            else:
                st.warning("Inserisci il nome della nicchia prima di generare.")
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        # ------------------------------
        
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i tuoi file CSV per iniziare l'analisi di mercato.")
