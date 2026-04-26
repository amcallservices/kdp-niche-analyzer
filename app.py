import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM - TOTAL DARK MODE
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 16.4", page_icon="🌙", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        #MainMenu, header, footer, .stAppHeader {visibility: hidden;}
        .program-title { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800; border-bottom: 2px solid #30363d; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        .section-title { color: #f0f6fc !important; font-size: 1.3rem !important; font-weight: 700; }
        .ai-panel { background-color: #161b22; padding: 2rem; border-radius: 12px; border: 1px solid #30363d; }
        div[data-testid="stWidgetLabel"] p { color: #f0f6fc !important; font-weight: 600; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] { background-color: #0d1117 !important; color: #ffffff !important; border: 1px solid #30363d !important; }
        [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
        button[kind="primary"] { background-color: #238636 !important; color: white !important; border: 1px solid #2ea043 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v16.4 🌙</div>", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR - LOGICA TRUE BSR (EVITA BSR FALSATI)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#58a6ff;'>📥 CARICAMENTO DATI</p>", unsafe_allow_html=True)
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt]}"

    files = st.file_uploader("Trascina qui i tuoi CSV", type=["csv"], accept_multiple_files=True)

    if st.button("📊 ANALIZZA TUTTO", type="primary"):
        if files:
            all_dfs = []
            for f in files:
                try:
                    df_raw = pd.read_csv(f, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
                except:
                    f.seek(0)
                    df_raw = pd.read_csv(f, sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')

                cols = df_raw.columns.tolist()
                temp = pd.DataFrame(index=df_raw.index)
                
                # Inizializzazione colonne per evitare KeyError
                for c in ["Copertina", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Autore", "Categoria Editore"]:
                    temp[c] = np.nan

                bsr_list = []
                auth_list = []

                for idx, row in df_raw.iterrows():
                    # --- LOGICA TRUE BSR: Cerca tutti i numeri col # e prendi il più alto (Global Rank) ---
                    found_ranks = []
                    for val in row.dropna():
                        val_s = str(val)
                        if '#' in val_s:
                            nums = re.findall(r'(\d{1,3}(?:[.,]\d{3})*|\d+)', val_s)
                            for n_str in nums:
                                try:
                                    n = int(n_str.replace('.','').replace(',',''))
                                    found_ranks.append(n)
                                except: continue
                    # Prendiamo il valore massimo trovato nella riga
                    bsr_list.append(max(found_ranks) if found_ranks else np.nan)

                    # --- LOGICA AUTORE ---
                    a_name = "N/D"
                    for i, c in enumerate(cols):
                        val_c = str(row[c]).strip()
                        if "author" in str(c).lower() or val_c.lower() == "author":
                            if val_c.lower() == "author" and (i+1) < len(cols):
                                a_name = str(row[cols[i+1]])
                            else: a_name = val_c
                            break
                    auth_list.append(re.sub(r'^(di|by|Author:)\s+', '', a_name, flags=re.IGNORECASE))

                temp['BSR'] = bsr_list
                temp['Nome Autore'] = auth_list
                
                # Altri mapping
                def find_c(keys):
                    for k in keys:
                        for c in cols:
                            if k.lower() in str(c).lower().strip(): return c
                    return None

                img = find_c(['s-image src', 'image', 'src'])
                if img: temp['Copertina'] = df_raw[img]
                
                t_c = find_c(['a-size-medium', 'title', 'titolo', 'clamp'])
                raw_t = df_raw[t_c].fillna("N/D").astype(str) if t_c else pd.Series(["N/D"]*len(df_raw))
                link = find_c(['href', 'url', 'link'])
                def get_u(i):
                    if not link: return None
                    v = str(df_raw.iloc[i][link])
                    return v if 'http' in v else f"{base_url}{v}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({get_u(i)})" if get_u(i) else str(t) for i, t in enumerate(raw_t)]
                
                p_c = find_c(['a-offscreen', 'price', 'prezzo'])
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                r_c = find_c(['a-size-mini', 'voti', 'review', 'rating'])
                if r_c:
                    def cl_r(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_c].apply(cl_r)

                temp['Categoria Editore'] = temp['Nome Autore'].apply(lambda x: "Independent" if any(s in str(x).lower() for s in ['independently', 'kdp', 'indipendente']) else "Publishing House")
                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'N. Libro', range(1, len(st.session_state.raw_data) + 1))
            st.rerun()

    if st.button("🔄 RESET"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data.copy()
    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown(f"<div class='section-title'>Market: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Libri", len(df))
        m2.metric("Prezzo Medio", f"{df['Prezzo'].mean():.2f} €" if pd.notna(df['Prezzo'].mean()) else "N/D")
        m3.metric("BSR Reale Medio", f"{int(df['BSR'].mean()):,}".replace(',', '.') if pd.notna(df['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Autore"]], 
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "BSR": st.column_config.NumberColumn("BSR Global", format="%d")
            }
        )

    with col_r:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia")
        target = st.text_input("Target")
        if st.button("🪄 GENERA STRATEGIA", type="primary"):
            if nicchia and target:
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": f"Analisi per {nicchia}."}])
                st.session_state.suggestions = res.choices[0].message.content
        if st.session_state.suggestions:
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i file per l'analisi.")
