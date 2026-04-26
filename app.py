import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM - TOTAL DARK MODE
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 16.0", page_icon="🌙", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        section[data-testid="stSidebar"] * { color: #8b949e !important; }
        .program-title { color: #58a6ff !important; font-size: 2.2rem !important; font-weight: 800; border-bottom: 2px solid #30363d; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        .section-title { color: #f0f6fc !important; font-size: 1.3rem !important; font-weight: 700; margin-bottom: 1rem; }
        .ai-panel { background-color: #161b22; padding: 2rem; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 10px 30px rgba(0,0,0,0.6); color: #f0f6fc !important; }
        .ai-panel h3 { color: #58a6ff !important; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        div[data-testid="stWidgetLabel"] p { color: #f0f6fc !important; font-weight: 600; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] { background-color: #0d1117 !important; color: #ffffff !important; border: 1px solid #30363d !important; }
        [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
        .stButton button { border-radius: 8px !important; font-weight: 700 !important; width: 100%; transition: 0.3s; }
        button[kind="primary"] { background-color: #238636 !important; color: white !important; border: 1px solid #2ea043 !important; }
        button[kind="primary"]:hover { background-color: #2ea043 !important; box-shadow: 0 0 15px rgba(46, 160, 67, 0.4); }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v16.0 🌙</div>", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR - ELABORAZIONE ROBUSTA
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#58a6ff;'>📥 CARICAMENTO DATI</p>", unsafe_allow_html=True)
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt]}"

    files = st.file_uploader("Trascina i tuoi CSV qui", type=["csv"], accept_multiple_files=True)

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

                # INIZIALIZZAZIONE PREVENTIVA (Evita il KeyError)
                temp = pd.DataFrame(index=df_raw.index)
                for c_name in ['Copertina', 'Titolo', 'BSR', 'Prezzo', 'Recensioni', 'Nome Autore', 'Categoria Editore']:
                    temp[c_name] = np.nan

                # --- MAPPING ---
                img_c = find_col(['s-image src', 'a-dynamic-image src', 'image', 'copertina', 'src'])
                if img_c: temp['Copertina'] = df_raw[img_c]
                
                t_c = find_col(['a-size-medium', 'title', 'titolo', 'name', '_cdezb_p13n-sc-css-line-clamp-1_1fn1y'])
                raw_t = df_raw[t_c].fillna("N/D").astype(str) if t_c else pd.Series(["N/D"]*len(df_raw))
                link_c = find_col(['a-link-normal href', 'href', 'url', 'link'])
                def fix_url(i):
                    if not link_c: return None
                    v = str(df_raw.iloc[i][link_c])
                    return v if 'http' in v else f"{base_url}{v}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({fix_url(i)})" if fix_url(i) else str(t) for i, t in enumerate(raw_t)]
                
                b_c = find_col(['zg-bdg-text', 'extension-rank', 'rank', 'bsr'])
                if not b_c:
                    for c in df_raw.columns:
                        if df_raw[c].astype(str).str.contains('#').any(): b_c = c; break
                if b_c:
                    def cl_bsr(v):
                        m = re.search(r'#?(\d{1,3}(?:[.,]\d{3})*|\d+)', str(v))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp['BSR'] = df_raw[b_c].apply(cl_bsr)
                
                p_c = find_col(['a-offscreen', 'price', 'prezzo', 'a-price-whole', 'p13n-sc-price'])
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                r_c = find_col(['a-size-mini', 'a-size-small', 'a-size-base', 'voti', 'review'])
                if r_c:
                    def cl_r(v):
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_c].apply(cl_r)
                
                # --- AUTORE FIX ---
                e_c = find_col(['a-size-base 2', 'a-color-secondary', 'author', 'editore', 'byline', 'brand'])
                if e_c:
                    def get_author(v):
                        t = str(v).strip()
                        if t.lower() in ['nan', 'none', '']: return "N/D"
                        return re.sub(r'^(di|by|Author:)\s+', '', t, flags=re.IGNORECASE)
                    temp['Nome Autore'] = df_raw[e_c].apply(get_author)
                    
                    def check_i(v):
                        t = str(v).lower()
                        return "Independent" if any(s in t for s in ['independently', 'kdp', 'indipendente']) else "Publishing House"
                    temp['Categoria Editore'] = df_raw[e_c].apply(check_i)
                else:
                    temp['Categoria Editore'] = "Publishing House"

                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'N. Libro', range(1, len(st.session_state.raw_data) + 1))
            st.rerun()

    if st.session_state.raw_data is not None:
        st.markdown("---")
        tipo = st.selectbox("Filtra per Tipo:", ["Tutti", "Independent", "Publishing House"])
        st.session_state.pub_filter = tipo

    if st.button("🔄 RESET"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD
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
        
        # VALVOLA DI SICUREZZA PER LE COLONNE
        desired = ["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Autore"]
        actual = [c for c in desired if c in df_f.columns]
        
        st.dataframe(
            df_f[actual], use_container_width=True, height=800, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "Titolo": st.column_config.TextColumn("Titolo (Link)", width="large")
            }
        )

    with col_r:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia")
        target = st.text_input("Target")
        
        if st.button("🪄 GENERA STRATEGIA", type="primary"):
            if nicchia and target:
                with st.spinner("L'AI sta analizzando i dati..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"Expert KDP analyzer. Nicchia: {nicchia}, Target: {target}. Genera 3 titoli e trama."
                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = res.choices[0].message.content
        
        if st.session_state.suggestions:
            st.markdown("<hr style='border-color:#30363d;'>", unsafe_allow_html=True)
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i file CSV per illuminare i dati.")
