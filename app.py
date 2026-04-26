import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM - TOTAL DARK MODE
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.8", page_icon="🌙", layout="wide")

st.markdown("""
    <style>
        /* Sfondo Totale dell'App - Deep Black */
        .stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
        
        /* Sidebar Total Dark */
        section[data-testid="stSidebar"] { 
            background-color: #161b22 !important; 
            border-right: 1px solid #30363d; 
        }
        section[data-testid="stSidebar"] * { color: #8b949e !important; }

        /* Header e Titoli Neon */
        .program-title { 
            color: #58a6ff !important; 
            font-size: 2.2rem !important; 
            font-weight: 800; 
            border-bottom: 2px solid #30363d; 
            padding-bottom: 0.5rem; 
            margin-bottom: 1.5rem;
            text-shadow: 0 0 10px rgba(88, 166, 255, 0.3);
        }
        .section-title { color: #f0f6fc !important; font-size: 1.3rem !important; font-weight: 700; margin-bottom: 1rem; }
        
        /* AI PANEL - DARK GLASS EFFECT */
        .ai-panel { 
            background-color: #161b22; 
            padding: 2rem; 
            border-radius: 12px; 
            border: 1px solid #30363d; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            color: #f0f6fc !important;
        }
        .ai-panel h3 { color: #58a6ff !important; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .ai-panel p { color: #8b949e !important; }
        
        /* Inputs e Widget - No Bianchi */
        div[data-testid="stWidgetLabel"] p { color: #f0f6fc !important; font-weight: 600; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #0d1117 !important;
            color: #ffffff !important;
            border: 1px solid #30363d !important;
        }
        
        /* Metric Styling */
        [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
        [data-testid="stMetricLabel"] { color: #8b949e !important; }

        /* Pulsanti Professionali */
        .stButton button { border-radius: 8px !important; font-weight: 700 !important; width: 100%; transition: 0.3s; }
        button[kind="primary"] { background-color: #238636 !important; color: white !important; border: 1px solid #2ea043 !important; }
        button[kind="primary"]:hover { background-color: #2ea043 !important; box-shadow: 0 0 15px rgba(46, 160, 67, 0.4); }
        
        /* Dataframe fix per Dark Mode */
        .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.8 🌙</div>", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE STATO ---
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR - CARICAMENTO MULTI-FILE E FILTRI
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#58a6ff; font-size:1rem;'>📥 IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt]}"

    files = st.file_uploader("Trascina fino a 100 CSV", type=["csv"], accept_multiple_files=True)

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
                
                # --- Copertina ---
                img_c = find_col(['s-image src', 'a-dynamic-image src', 'image', 'copertina', 'src'])
                temp['Copertina'] = df_raw[img_c] if img_c else None
                
                # --- Titolo ---
                t_c = find_col(['a-size-medium', 'title', 'titolo', 'name', 'text-normal'])
                raw_t = df_raw[t_c].fillna("N/D").astype(str) if t_c else pd.Series(["N/D"]*len(df_raw))
                link_c = find_col(['a-link-normal href', 'href', 'url', 'link'])
                def fix_url(i):
                    if not link_c: return None
                    v = str(df_raw.iloc[i][link_c])
                    return v if 'http' in v else f"{base_url}{v}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({fix_url(i)})" if fix_url(i) else str(t) for i, t in enumerate(raw_t)]
                
                # --- BSR Radar (Potenziato) ---
                b_c = find_col(['extension-rank', 'zg-bdg-text', 'rank', 'bsr', 'classifica'])
                if not b_c:
                    for c in df_raw.columns:
                        if df_raw[c].astype(str).str.contains('#').any(): b_c = c; break
                if b_c:
                    def cl_bsr(v):
                        m = re.search(r'#?(\d{1,3}(?:[.,]\d{3})*|\d+)', str(v))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp['BSR'] = df_raw[b_c].apply(cl_bsr)
                else: temp['BSR'] = np.nan
                
                # --- Prezzo ---
                p_c = find_col(['a-offscreen', 'price', 'prezzo', 'a-price-whole'])
                if p_c: temp['Prezzo'] = pd.to_numeric(df_raw[p_c].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                # --- Recensioni (Fix: Aggiunto a-size-mini) ---
                r_c = find_col(['a-size-mini', 'a-size-small', 'a-size-base', 'voti', 'review', 'rating'])
                if r_c:
                    def cl_r(v):
                        # Estrae solo i numeri, ignorando parentesi e separatori migliaia
                        n = re.findall(r'\b\d+\b', str(v).replace('.','').replace(',',''))
                        # Prende il numero più alto (per evitare di prendere le stelle es. 4.5)
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_c].apply(cl_r)
                else: temp['Recensioni'] = np.nan

                # --- Editore ---
                e_c = find_col(['a-color-secondary', 'author', 'editore', 'a-size-base 2'])
                if e_c:
                    def check_i(v):
                        t = str(v).lower()
                        return "Independent" if any(s in t for s in ['independently', 'kdp', 'indipendente', 'createspace']) else "Publishing House"
                    temp['Categoria Editore'] = df_raw[e_c].apply(check_i)
                    temp['Nome Editore'] = df_raw[e_c].fillna("N/D")
                else:
                    temp['Categoria Editore'] = "Publishing House"
                    temp['Nome Editore'] = "N/D"

                all_dfs.append(temp)
            
            st.session_state.raw_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.raw_data.insert(1, 'N. Libro', range(1, len(st.session_state.raw_data) + 1))
            st.rerun()

    if st.session_state.raw_data is not None:
        st.markdown("---")
        st.markdown("<p style='font-weight:700; color:#58a6ff;'>🔍 FILTRA RISULTATI</p>", unsafe_allow_html=True)
        tipo = st.selectbox("Mostra solo:", ["Tutti", "Independent", "Publishing House"])
        st.session_state.pub_filter = tipo

    if st.button("🔄 SVUOTA TUTTO"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD E AI STRATEGY LAB
# ==============================================================================
if st.session_state.raw_data is not None:
    df_f = st.session_state.raw_data.copy()
    if st.session_state.get('pub_filter', "Tutti") != "Tutti":
        df_f = df_f[df_f['Categoria Editore'] == st.session_state.pub_filter]

    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Libri Caricati", len(df_f))
        m2.metric("Prezzo Avg", f"{df_f['Prezzo'].mean():.2f} €" if pd.notna(df_f['Prezzo'].mean()) else "N/D")
        m3.metric("BSR Avg", f"{int(df_f['BSR'].mean()):,}".replace(',', '.') if pd.notna(df_f['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df_f[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Editore"]], 
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "Recensioni": st.column_config.NumberColumn("Recensioni", format="%d"),
                "BSR": st.column_config.NumberColumn("BSR Rank", format="%d"),
                "Titolo": st.column_config.TextColumn("Titolo (Cliccabile)", width="large")
            }
        )

    with col_r:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        st.markdown("<p>Analisi basata sui dati reali estratti.</p>", unsafe_allow_html=True)
        
        nicchia = st.text_input("Definisci Nicchia")
        target = st.text_input("Definisci Target")
        
        if st.button("🪄 GENERA REPORT STRATEGICO", type="primary"):
            if nicchia and target:
                with st.spinner("L'AI sta analizzando i dati del mercato..."):
                    try:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        tipo_p = st.session_state.get('pub_filter', 'Tutti')
                        prompt = f"Expert KDP analyzer. Nicchia: {nicchia}, Target: {target}. Filtro: {tipo_p}. Genera 3 titoli magnetici, sottotitoli e strategia trama."
                        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                        st.session_state.suggestions = res.choices[0].message.content
                    except Exception as e:
                        st.error(f"Errore API: {e}")
        
        if st.session_state.suggestions:
            st.markdown("<hr style='border-color:#30363d;'>", unsafe_allow_html=True)
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("🌙 Carica i tuoi file CSV per iniziare l'analisi di mercato.")
