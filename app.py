import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 17.6", page_icon="💰", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .program-title { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800; border-bottom: 2px solid #30363d; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        .profit-card { background: #1c2128; border: 1px solid #30363d; padding: 20px; border-radius: 10px; margin-bottom: 20px; min-height: 150px; }
        .status-green { color: #3fb950; font-weight: bold; }
        .status-yellow { color: #d29922; font-weight: bold; }
        .status-red { color: #f85149; font-weight: bold; }
        .ai-panel { background-color: #161b22; padding: 2rem; border-radius: 12px; border: 1px solid #30363d; margin-top: 20px; }
        [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Intelligence Hub v17.6 💰</div>", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'ai_output' not in st.session_state: st.session_state.ai_output = None
if 'ai_plot' not in st.session_state: st.session_state.ai_plot = None 

# ==============================================================================
# 2. LOGICA DI ESTRAZIONE POTENZIATA (Omni-BSR & Universal Support)
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
                
                for col_name in ["Copertina", "Titolo", "BSR", "Prezzo", "Autore", "Recensioni"]:
                    temp[col_name] = np.nan

                bsrs, authors = [], []
                for _, row in df_raw.iterrows():
                    # --- RADAR BSR POTENZIATO (Omni-Format) ---
                    ranks = []
                    for v in row.dropna():
                        v_s = str(v).strip()
                        # Identifica stringhe che contengono indicatori di classifica, escludendo i link
                        if 'http' not in v_s.lower() and len(v_s) < 150:
                            if any(k in v_s.lower() for k in ['#', 'n.', 'pos.', 'rank', 'classifica', 'bestseller']):
                                # Estrae gruppi di numeri (gestisce 1.234 o 1,234)
                                matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*|\d+)', v_s)
                                for m in matches:
                                    try:
                                        val = int(m.replace('.','').replace(',',''))
                                        if val > 0: ranks.append(val)
                                    except: continue
                    # Prende il valore più alto (che solitamente è il BSR globale)
                    bsrs.append(max(ranks) if ranks else np.nan)
                    
                    # --- LOGICA AUTORE ---
                    auth = "N/D"
                    for i, c in enumerate(cols):
                        val_c = str(row[c]).strip()
                        if "author" in str(c).lower() or val_c.lower() in ["author", "di", "by"]:
                            if val_c.lower() in ["author", "di", "by"]:
                                for j in range(1, 4):
                                    if i+j < len(cols):
                                        candidate = str(row[cols[i+j]]).strip()
                                        if candidate and candidate.lower() != 'nan' and 'http' not in candidate:
                                            auth = candidate
                                            break
                            else:
                                auth = val_c
                            break
                    authors.append(re.sub(r'^(di|by|Author:)\s+', '', auth, flags=re.IGNORECASE))

                temp['BSR'] = bsrs
                temp['Autore'] = authors
                
                # --- MAPPING COLONNE ---
                img_c = next((c for c in cols if any(k in c.lower() for k in ['s-image src', 'image', 'copertina', 'src'])), None)
                if img_c: temp['Copertina'] = df_raw[img_c]

                tit_c = next((c for c in cols if any(k in c.lower() for k in ['line-clamp-1', 'title', 'titolo', 'name', 'a-size-medium', 'a-size-base-plus'])), None)
                if tit_c: temp['Titolo'] = df_raw[tit_c]

                p_c = next((c for c in cols if any(k in c.lower() for k in ['price', 'prezzo', 'offscreen'])), None)
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                rev_c = next((c for c in cols if any(k in c.lower() for k in ['review', 'voti', 'rating', 'a-size-base', 'a-size-mini'])), None)
                if rev_c:
                    def cl_rev(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[rev_c].apply(cl_rev)
                
                temp = temp[temp['Titolo'].notna()]
                temp = temp[temp['Titolo'].astype(str).str.strip() != '']
                temp = temp[temp['Titolo'].astype(str).str.lower() != 'nan']

                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'ID', range(1, len(st.session_state.raw_data) + 1))
            st.session_state.ai_output = None
            st.session_state.ai_plot = None
            st.rerun()

    if st.button("🔄 RESET"):
        st.session_state.raw_data = None
        st.session_state.ai_output = None
        st.session_state.ai_plot = None
        st.rerun()

# ==============================================================================
# 3. PROFITABILITY ANALYSIS
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data.copy()
    avg_bsr = df['BSR'].mean() if not df['BSR'].isna().all() else 0
    avg_price = df['Prezzo'].mean() if not df['Prezzo'].isna().all() else 0
    
    st.markdown("### 📈 Valutazione Ragionata della Nicchia")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if avg_bsr > 0 and avg_bsr < 80000: status, color, desc = "PROFITTABILITÀ ALTA", "status-green", "Volume di vendite elevato. Ottima nicchia."
        elif avg_bsr > 0 and avg_bsr < 150000: status, color, desc = "PROFITTABILITÀ MEDIA", "status-yellow", "Richiede Ads attive."
        else: status, color, desc = "PROFITTABILITÀ BASSA", "status-red", "Poche vendite o mercato saturo."
        
        st.markdown(f"<div class='profit-card'><p style='color:#8b949e;'>VENDITE STIMATE</p><h2 class='{color}'>{status}</h2><p>{desc}</p></div>", unsafe_allow_html=True)

    with c2:
        p_status = "BUON MARGINE" if avg_price > 12 else "BASSO MARGINE"
        p_color = "status-green" if avg_price > 12 else "status-red"
        st.markdown(f"<div class='profit-card'><p style='color:#8b949e;'>ECONOMIA</p><h2 class='{p_color}'>{p_status}</h2><p>Prezzo medio: {avg_price:.2f}€</p></div>", unsafe_allow_html=True)

    with c3:
        verdict = "ECCELLENTE" if avg_bsr < 80000 and avg_bsr > 0 and avg_price > 12 else "VALUTARE"
        st.markdown(f"<div class='profit-card'><p style='color:#8b949e;'>VERDETTO FINALE</p><h2 style='color:#58a6ff;'>{verdict}</h2><p>Analisi su {len(df)} libri concorrenti.</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================================================
    # 4. TABELLA DATI E STEP 2 (AI STRATEGY LAB)
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
        st.markdown("<div class='ai-panel' style='margin-top:0px;'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ Step 2: AI Strategy Lab</h3>", unsafe_allow_html=True)
        nicchia_target = st.text_input("Nicchia analizzata")
        
        if st.button("🪄 GENERA STRATEGIA"):
            if nicchia_target and not df['Titolo'].isna().all():
                with st.spinner("L'IA sta analizzando i competitor..."):
                    try:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        top_titles = "\n".join(df['Titolo'].dropna().head(10).astype(str).tolist())
                        
                        prompt = f"""
                        Sei un esperto di KDP Marketing per il marketplace {mkt}.
                        Nicchia: {nicchia_target}
                        Competitors attuali:
                        {top_titles}
                        
                        Genera:
                        1. 5 Titoli magnetici ad alta conversione.
                        2. 5 Sottotitoli SEO per scalare il ranking.
                        3. Spiega brevemente perché questi titoli batteranno i competitor.
                        """
                        
                        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                        st.session_state.ai_output = response.choices[0].message.content
                    except Exception as e:
                        st.error(f"Errore: {e}")
            else:
                st.warning("Assicurati di aver inserito la nicchia e caricato i dati correttamente.")

        if st.session_state.ai_output:
            st.markdown("---")
            st.markdown(st.session_state.ai_output)
        st.markdown("</div>", unsafe_allow_html=True)

    # ==============================================================================
    # 5. STEP 3: BOOK ARCHITECT (TRAMA E OBIETTIVO)
    # ==============================================================================
    st.markdown("---")
    st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
    st.markdown("<h3>✍️ Step 3: Book Architect (Obiettivo & Trama)</h3>", unsafe_allow_html=True)
    
    col_input, col_empty = st.columns([1, 1])
    with col_input:
        titolo_scelto = st.text_input("Inserisci il Titolo del Libro scelto per generare la Trama:")
    
    if st.button("📝 ELABORA TRAMA DETTAGLIATA", type="primary"):
        if titolo_scelto:
            with st.spinner("L'IA sta redigendo l'obiettivo e la struttura complessa del libro..."):
                try:
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    lingue_mercato = {"IT": "Italiano", "US": "Inglese Americano", "UK": "Inglese Britannico", "DE": "Tedesco", "FR": "Francese", "ES": "Spagnolo"}
                    lingua_destinazione = lingue_mercato.get(mkt, "Inglese")

                    prompt_trama = f"""
                    Sei un Ghostwriter professionista e un Book Architect esperto in saggistica e manualistica per il mercato Amazon KDP.
                    Titolo: "{titolo_scelto}".
                    Lingua: {lingua_destinazione}.
                    Redigi l'obiettivo del libro e una trama (outline) dettagliata, complessa e specifica capitolo per capitolo.
                    """
                    
                    response_trama = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_trama}])
                    st.session_state.ai_plot = response_trama.choices[0].message.content
                except Exception as e:
                    st.error(f"Errore: {e}")
        else:
            st.warning("Devi prima inserire un titolo.")

    if st.session_state.ai_plot:
        st.markdown("<hr style='border-color:#30363d;'>", unsafe_allow_html=True)
        st.markdown(st.session_state.ai_plot)
    
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i tuoi file CSV per iniziare l'analisi di mercato.")
