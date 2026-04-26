import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM - TOTAL DARK & CLEAN UI
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.9", page_icon="🌙", layout="wide")

st.markdown("""
    <style>
        /* RIMOZIONE MENU ALTO DESTRA E FOOTER BASSO DESTRA */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        /* Sfondo Totale dell'App - Deep Black */
        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
        
        /* Sidebar Total Dark */
        section[data-testid="stSidebar"] { 
            background-color: #161b22 !important; 
            border-right: 1px solid #30363d; 
        }
        section[data-testid="stSidebar"] * { color: #8b949e !important; }

        /* Titoli Neon */
        .program-title { 
            color: #58a6ff !important; 
            font-size: 2.2rem !important; 
            font-weight: 800; 
            border-bottom: 2px solid #30363d; 
            padding-bottom: 0.5rem; 
            margin-bottom: 1.5rem;
        }
        .section-title { color: #f0f6fc !important; font-size: 1.3rem !important; font-weight: 700; margin-bottom: 1rem; }
        
        /* AI PANEL - DARK GLASS */
        .ai-panel { 
            background-color: #161b22; 
            padding: 2rem; 
            border-radius: 12px; 
            border: 1px solid #30363d; 
            color: #f0f6fc !important;
        }
        
        /* Widget Labels & Inputs */
        div[data-testid="stWidgetLabel"] p { color: #f0f6fc !important; font-weight: 600; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #0d1117 !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }
        
        /* Pulsanti */
        .stButton button { border-radius: 8px !important; font-weight: 700 !important; width: 100%; }
        button[kind="primary"] { background-color: #238636 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.9 🌙</div>", unsafe_allow_html=True)

# --- STATO SESSIONE ---
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR - LOGICA DI ELABORAZIONE (INVARIATA)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#58a6ff;'>📥 IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt]}"

    files = st.file_uploader("Carica fino a 100 CSV", type=["csv"], accept_multiple_files=True)

    if st.button("📊 ELABORA E COMBINA", type="primary"):
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
                
                # Mapping core
                img_c = find_col(['s-image src', 'image', 'copertina'])
                temp['Copertina'] = df_raw[img_c] if img_c else None
                
                t_c = find_col(['a-size-medium', 'title', 'titolo'])
                raw_t = df_raw[t_c].fillna("N/D").astype(str) if t_c else pd.Series(["N/D"]*len(df_raw))
                link_c = find_col(['href', 'url', 'link'])
                def fix_url(i):
                    if not link_c: return None
                    v = str(df_raw.iloc[i][link_c])
                    return v if 'http' in v else f"{base_url}{v}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({fix_url(i)})" if fix_url(i) else str(t) for i, t in enumerate(raw_t)]
                
                # BSR Radar
                b_c = find_col(['zg-bdg-text', 'rank', 'bsr', 'extension-rank'])
                if not b_c:
                    for c in df_raw.columns:
                        if df_raw[c].astype(str).str.contains('#').any(): b_c = c; break
                if b_c:
                    def cl_bsr(v):
                        m = re.search(r'#?(\d{1,3}(?:[.,]\d{3})*|\d+)', str(v))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp['BSR'] = df_raw[b_c].apply(cl_bsr)
                
                # Prezzo & Recensioni (Fix v15.8)
                p_c = find_col(['a-offscreen', 'price', 'prezzo'])
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                r_c = find_col(['a-size-mini', 'a-size-small', 'voti', 'review'])
                if r_c:
                    def cl_r(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_c].apply(cl_r)

                # Editore/Autore (Fix v15.9)
                e_c = find_col(['a-color-secondary', 'author', 'editore', 'a-size-base 2'])
                if e_c:
                    def check_i(v):
                        t = str(v).lower()
                        return "Independent" if any(s in t for s in ['independently', 'kdp', 'indipendente']) else "Publishing House"
                    temp['Categoria Editore'] = df_raw[e_c].apply(check_i)
                    temp['Nome Autore'] = df_raw[e_c].fillna("N/D")
                else:
                    temp['Categoria Editore'] = "Publishing House"
                    temp['Nome Autore'] = "N/D"

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
# 3. DASHBOARD (INVARIATA)
# ==============================================================================
if st.session_state.raw_data is not None:
    df_f = st.session_state.raw_data.copy()
    if st.session_state.get('pub_filter', "Tutti") != "Tutti":
        df_f = df_f[df_f['Categoria Editore'] == st.session_state.pub_filter]

    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Libri", len(df_f))
        m2.metric("Prezzo Avg", f"{df_f['Prezzo'].mean():.2f} €" if pd.notna(df_f['Prezzo'].mean()) else "N/D")
        m3.metric("BSR Avg", f"{int(df_f['BSR'].mean()):,}".replace(',', '.') if pd.notna(df_f['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df_f[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Autore"]], 
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f")
            }
        )

    with col_r:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia")
        target = st.text_input("Target")
        
        if st.button("🪄 GENERA REPORT", type="primary"):
            if nicchia and target:
                with st.spinner("Analizzando..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    tipo_p = st.session_state.get('pub_filter', 'Tutti')
                    prompt = f"Expert KDP analyzer. Nicchia: {nicchia}, Target: {target}. Filtro: {tipo_p}. Genera 3 titoli e trama."
                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = res.choices[0].message.content
        
        if st.session_state.suggestions:
            st.markdown("<hr style='border-color:#30363d;'>", unsafe_allow_html=True)
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i file CSV nella sidebar per iniziare.")
