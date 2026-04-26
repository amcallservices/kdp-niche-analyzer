import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.4", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }
        .stApp { background-color: #f9fafb !important; }
        section[data-testid="stSidebar"] { background-color: #1f2937 !important; min-width: 350px !important; border-right: 1px solid #374151; padding-top: 1rem; }
        section[data-testid="stSidebar"] * { color: #f3f4f6 !important; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] { background-color: #374151 !important; border: 1px solid #4b5563 !important; color: white !important; border-radius: 6px !important; }
        .program-title { color: #111827 !important; font-size: 2rem !important; font-weight: 800; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.5rem; margin-bottom: 1rem; }
        .section-title { color: #374151 !important; font-size: 1.2rem !important; font-weight: 700; margin-bottom: 1rem; }
        [data-testid="stMetricValue"] { color: #2563eb !important; font-weight: 800; }
        .ai-panel { background-color: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        .stButton button { border-radius: 6px !important; font-weight: 600 !important; width: 100%;}
        button[kind="primary"] { background-color: #2563eb !important; color: white !important; border: none !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.4</div>", unsafe_allow_html=True)

# --- STATO ---
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR (LOGICA MULTI-FILE & FILTRI)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 1: IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt_choice
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt_choice]}"

    uploaded_files = st.file_uploader("Trascina qui fino a 100 CSV", type=["csv"], accept_multiple_files=True)

    if st.button("📊 Elabora Dati Combinati", type="primary"):
        if uploaded_files:
            all_dfs = []
            for uploaded_file in uploaded_files:
                try:
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
                except:
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')

                cols = df_raw.columns.tolist()
                def find_col(keywords):
                    for k in keywords:
                        for c in cols:
                            if k.lower() in str(c).lower().strip(): return c
                    return None

                temp = pd.DataFrame(index=df_raw.index)
                
                # --- A: COPERTINA ---
                img_col = find_col(['s-image src', 'a-dynamic-image src', 'src', 'image'])
                temp['Copertina'] = df_raw[img_col] if img_col else None
                
                # --- B: TITOLO E LINK ---
                t_col = find_col(['a-size-medium', 'line-clamp', 'title', 'titolo', 'name'])
                raw_t = df_raw[t_col].fillna("N/D").astype(str) if t_col else pd.Series(["N/D"] * len(df_raw))
                link_col = find_col(['href', 'url', 'link'])
                def get_url(i):
                    if not link_col: return None
                    val = str(df_raw.iloc[i][link_col])
                    return val if 'http' in val else f"{base_url}{val}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({get_url(i)})" if get_url(i) else str(t) for i, t in enumerate(raw_t)]
                
                # --- C: BSR (LOGICA RADAR) ---
                b_col = find_col(['zg-bdg-text', 'extension-rank', 'bsr', 'rank', 'classifica'])
                if not b_col:
                    # Se non trova la colonna, cerca in tutto il dataframe il simbolo #
                    for c in df_raw.columns:
                        if df_raw[c].astype(str).str.contains('#').any():
                            b_col = c
                            break
                if b_col:
                    def clean_bsr(val):
                        m = re.search(r'#?(\d{1,3}(?:[.,]\d{3})*|\d+)', str(val))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp['BSR'] = df_raw[b_col].apply(clean_bsr)
                else: temp['BSR'] = np.nan

                # --- D: PREZZO ---
                p_col = find_col(['a-offscreen', 'price', 'prezzo', '3mj9z', 'a-color-base'])
                if p_col:
                    temp['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                else: temp['Prezzo'] = np.nan

                # --- E: RECENSIONI ---
                r_col = find_col(['a-size-base', 'voti', 'review', 'rating'])
                if r_col:
                    def clean_r(val):
                        n = re.findall(r'\b\d+\b', str(val).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_col].apply(clean_r)
                
                # --- F: EDITORE (CATEGORIA E NOME) ---
                e_col = find_col(['a-color-secondary', 'author', 'editore', 'a-size-base 2'])
                if e_col:
                    def check_indie(val):
                        t = str(val).lower()
                        return "Independent" if any(s in t for s in ['independently', 'kdp', 'indipendente']) else "Publishing House"
                    temp['Categoria Editore'] = df_raw[e_col].apply(check_indie)
                    temp['Nome Editore'] = df_raw[e_col].fillna("N/D")
                else:
                    temp['Categoria Editore'] = "Publishing House"
                    temp['Nome Editore'] = "N/D"

                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'N. Libro', range(1, len(st.session_state.raw_data) + 1))
            st.session_state.suggestions = None # Reset AI su nuovi file
            st.rerun()

    if st.session_state.raw_data is not None:
        st.markdown("---")
        # FILTRO A TENDINA RICHIESTO
        tipo_filtro = st.selectbox("Seleziona Tipo Editore:", ["Tutti", "Independent", "Publishing House"])
        st.session_state.pub_filter = tipo_filtro

    if st.button("🔄 Reset"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data.copy()
    if st.session_state.get('pub_filter', "Tutti") != "Tutti":
        df = df[df['Categoria Editore'] == st.session_state.pub_filter]

    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Libri", len(df))
        c2.metric("Prezzo Avg", f"{df['Prezzo'].mean():.2f} €" if pd.notna(df['Prezzo'].mean()) else "N/D")
        c3.metric("BSR Avg", f"{int(df['BSR'].mean()):,}".replace(',', '.') if pd.notna(df['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Editore"]], 
            use_container_width=True, height=750, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "BSR": st.column_config.NumberColumn("BSR Rank", format="%d")
            }
        )

    with col_r:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia")
        target = st.text_input("Target")
        
        if st.button("🪄 Genera Strategia", type="primary"):
            if nicchia and target:
                with st.spinner("L'AI sta analizzando i dati..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    tipo = st.session_state.get('pub_filter', 'Tutti')
                    prompt = f"Expert KDP analyzer. Nicchia: {nicchia}, Target: {target}. Filtro attuale: {tipo}. Genera 3 titoli, sottotitoli e trama."
                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = res.choices[0].message.content
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("👈 Trascina i file CSV nella sidebar per iniziare.")
