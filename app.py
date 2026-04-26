import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM - TOTAL DARK MODE
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.7", page_icon="🌙", layout="wide")

st.markdown("""
    <style>
        /* Sfondo Totale dell'App */
        .stApp { background-color: #0e1117 !important; color: #ffffff !important; }
        
        /* Nascondi Header e Menu originali */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        
        /* Sidebar Total Dark */
        section[data-testid="stSidebar"] { 
            background-color: #161b22 !important; 
            border-right: 1px solid #30363d; 
        }
        section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

        /* Titoli e Testi */
        .program-title { 
            color: #58a6ff !important; 
            font-size: 2rem !important; 
            font-weight: 800; 
            border-bottom: 1px solid #30363d; 
            padding-bottom: 0.5rem; 
            margin-bottom: 1rem; 
        }
        .section-title { color: #f0f6fc !important; font-size: 1.2rem !important; font-weight: 700; }
        
        /* Dataframe Dark Mode Fix */
        [data-testid="stDataFrame"] { background-color: #0e1117 !important; }
        
        /* AI PANEL - NESSUN COLORE CHIARO */
        .ai-panel { 
            background-color: #161b22; 
            padding: 2rem; 
            border-radius: 12px; 
            border: 1px solid #30363d; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            color: #f0f6fc !important;
        }
        .ai-panel h3 { color: #58a6ff !important; }
        .ai-panel p { color: #8b949e !important; }
        
        /* Widget Labels & Inputs */
        div[data-testid="stWidgetLabel"] p { color: #f0f6fc !important; font-weight: 600; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #0d1117 !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }

        /* Pulsanti */
        .stButton button { border-radius: 6px !important; font-weight: 600 !important; width: 100%; transition: 0.2s; }
        button[kind="primary"] { background-color: #238636 !important; color: white !important; border: none !important; }
        button[kind="primary"]:hover { background-color: #2ea043 !important; }
        
        /* Metric Styling */
        [data-testid="stMetricValue"] { color: #58a6ff !important; }
        [data-testid="stMetricLabel"] { color: #8b949e !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.7 🌙</div>", unsafe_allow_html=True)

# --- STATO SESSIONE ---
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR - ELABORAZIONE E FILTRI
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#58a6ff;'>📦 IMPORTAZIONE DATI</p>", unsafe_allow_html=True)
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt]}"

    files = st.file_uploader("Trascina fino a 100 CSV (No limiti)", type=["csv"], accept_multiple_files=True)

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
                def find_col(keys):
                    for k in keys:
                        for c in cols:
                            if k.lower() in str(c).lower().strip(): return c
                    return None

                temp = pd.DataFrame(index=df_raw.index)
                
                # --- Mapping ---
                img = find_col(['s-image src', 'image', 'copertina'])
                temp['Copertina'] = df_raw[img] if img else None
                
                t_col = find_col(['a-size-medium', 'title', 'titolo'])
                raw_t = df_raw[t_col].fillna("N/D").astype(str) if t_col else pd.Series(["N/D"]*len(df_raw))
                link = find_col(['href', 'url', 'link'])
                def fix_url(i):
                    if not link: return None
                    v = str(df_raw.iloc[i][link])
                    return v if 'http' in v else f"{base_url}{v}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({fix_url(i)})" if fix_url(i) else str(t) for i, t in enumerate(raw_t)]
                
                # BSR Radar
                b_col = find_col(['zg-bdg-text', 'rank', 'bsr'])
                if not b_col:
                    for c in df_raw.columns:
                        if df_raw[c].astype(str).str.contains('#').any(): b_col = c; break
                if b_col:
                    def cl_bsr(v):
                        m = re.search(r'#?(\d{1,3}(?:[.,]\d{3})*|\d+)', str(v))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp['BSR'] = df_raw[b_col].apply(cl_bsr)
                
                p_col = find_col(['a-offscreen', 'price', 'prezzo', 'a-price-whole'])
                if p_col: temp['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                r_col = find_col(['a-size-base', 'voti', 'review'])
                if r_col:
                    def cl_r(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_col].apply(cl_r)

                e_col = find_col(['a-color-secondary', 'author', 'editore'])
                if e_col:
                    def check_i(v):
                        t = str(v).lower()
                        return "Independent" if any(s in t for s in ['independently', 'kdp', 'indipendente']) else "Publishing House"
                    temp['Categoria Editore'] = df_raw[e_col].apply(check_i)
                    temp['Nome Editore'] = df_raw[e_col].fillna("N/D")
                else:
                    temp['Categoria Editore'] = "Publishing House"
                    temp['Nome Editore'] = "N/D"

                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'N. Libro', range(1, len(st.session_state.raw_data) + 1))
            st.rerun()

    if st.session_state.raw_data is not None:
        st.markdown("---")
        tipo = st.selectbox("Filtra Editore", ["Tutti", "Independent", "Publishing House"])
        st.session_state.pub_filter = tipo

    if st.button("🔄 RESET"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD TOTAL DARK
# ==============================================================================
if st.session_state.raw_data is not None:
    df_f = st.session_state.raw_data.copy()
    if st.session_state.get('pub_filter', "Tutti") != "Tutti":
        df_f = df_f[df_f['Categoria Editore'] == st.session_state.pub_filter]

    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown(f"<div class='section-title'>Mercato Corrente: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Libri Totali", len(df_f))
        m2.metric("Prezzo Avg", f"{df_f['Prezzo'].mean():.2f} €" if pd.notna(df_f['Prezzo'].mean()) else "N/D")
        m3.metric("BSR Avg", f"{int(df_f['BSR'].mean()):,}".replace(',', '.') if pd.notna(df_f['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df_f[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Editore"]], 
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f")
            }
        )

    with col_r:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        st.markdown("<p>Analisi strategica in corso...</p>", unsafe_allow_html=True)
        
        nicchia = st.text_input("Nicchia")
        target = st.text_input("Target")
        
        if st.button("🪄 Genera Report AI", type="primary"):
            if nicchia and target:
                with st.spinner("Analizzando i dati..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    tipo_p = st.session_state.get('pub_filter', 'Tutti')
                    prompt = f"Expert KDP analyzer. Nicchia: {nicchia}, Target: {target}. Filtro: {tipo_p}. Genera 3 titoli magnetici, sottotitoli e strategia trama."
                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = res.choices[0].message.content
        
        if st.session_state.suggestions:
            st.markdown("<hr style='border-color:#30363d;'>", unsafe_allow_html=True)
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i file CSV nella sidebar per illuminare i dati.")
