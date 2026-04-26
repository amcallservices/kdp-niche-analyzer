import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.2", page_icon="📈", layout="wide")

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

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.2</div>", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE STATO ---
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None
if 'raw_cols' not in st.session_state: st.session_state.raw_cols = None

# ==============================================================================
# 2. SIDEBAR (LOGICA MULTI-FILE E FILTRO CATEGORIA EDITORE)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 1: IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt_choice
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt_choice]}"

    uploaded_files = st.file_uploader("Carica CSV (Fino a 100 file)", type=["csv"], accept_multiple_files=True)

    if st.button("📊 Elabora Tutti i Dati", type="primary"):
        if uploaded_files:
            all_mapped_dfs = []
            all_cols_debug = []
            for uploaded_file in uploaded_files:
                try:
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
                except:
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')

                cols = df_raw.columns.tolist()
                all_cols_debug.extend(cols)
                
                def find_col(keywords):
                    for k in keywords:
                        for c in cols:
                            clean_c = str(c).lower().strip()
                            if k.lower() in clean_c: return c
                    return None

                temp_df = pd.DataFrame(index=df_raw.index)
                
                # --- MAPPING DATI ---
                img_col = find_col(['s-image src', 'a-dynamic-image src', 'src', 'image', 'img', 'thumbnail'])
                temp_df['Copertina'] = df_raw[img_col] if img_col else None
                
                t_col = find_col(['a-size-medium', 'line-clamp', 'title', 'titolo', 'name'])
                raw_titles = df_raw[t_col].fillna("N/D").astype(str) if t_col else pd.Series(["N/D"] * len(df_raw))
                
                link_col = find_col(['href', 'url', 'link'])
                asin_col = find_col(['asin', 'id'])
                
                def make_url(idx):
                    if link_col:
                        val = str(df_raw.iloc[idx][link_col])
                        if 'http' in val: return val
                        if val.startswith('/'): return f"{base_url}{val}"
                    if asin_col:
                        asin_val = str(df_raw.iloc[idx][asin_col]).strip()
                        if len(asin_val) >= 10: return f"{base_url}/dp/{asin_val[:10]}"
                    return None

                temp_df['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({make_url(i)})" if make_url(i) else str(t) for i, t in enumerate(raw_titles)]
                
                b_col = find_col(['zg-bdg-text', 'bsr', 'rank', 'classifica', 'sales'])
                if b_col:
                    def clean_bsr(testo):
                        m = re.search(r'\b(\d{1,3}(?:[.,]\d{3})*|\d+)\b', str(testo))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp_df['BSR'] = df_raw[b_col].apply(clean_bsr)
                else: temp_df['BSR'] = np.nan
                
                p_col = find_col(['price', 'prezzo', 'a-offscreen', '3mj9z'])
                if p_col: temp_df['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                r_col = find_col(['review', 'rating', 'voti', 'count', 'a-size-small', 'a-size-mini'])
                if r_col:
                    def clean_rev(testo):
                        nums = re.findall(r'\b\d+\b', str(testo).replace('.','').replace(',',''))
                        return int(max(nums, key=int)) if nums else np.nan
                    temp_df['Recensioni'] = df_raw[r_col].apply(clean_rev)
                
                e_col = find_col(['a-color-secondary', 'brand', 'author', 'editore', 'publisher', 'a-size-base 2'])
                if e_col:
                    def categorizza_editore(val):
                        t = str(val).lower()
                        if any(s in t for s in ['independently', 'kdp', 'indipendente', 'createspace']): return "Independent"
                        return "Publishing House"
                    temp_df['Categoria Editore'] = df_raw[e_col].apply(categorizza_editore)
                    temp_df['Nome Editore'] = df_raw[e_col].fillna("N/D")
                else:
                    temp_df['Categoria Editore'] = "Publishing House"
                    temp_df['Nome Editore'] = "N/D"

                all_mapped_dfs.append(temp_df)
            
            final_df = pd.concat(all_mapped_dfs, ignore_index=True)
            final_df.insert(1, 'N. Libro', range(1, len(final_df) + 1))
            st.session_state.raw_data = final_df
            st.session_state.raw_cols = list(set(all_cols_debug))
            st.rerun()

    # --- FILTRO RICHIESTO: AUTORI INDIPENDENTI VS CASE EDITRICI ---
    if st.session_state.raw_data is not None:
        st.markdown("---")
        st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 2: FILTRA TIPO EDITORE</p>", unsafe_allow_html=True)
        tipo_filtro = st.selectbox("Mostra Libri di:", ["Tutti", "Independent", "Publishing House"])
        st.session_state.pub_filter = tipo_filtro

    if st.button("🔄 Reset"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD E AI STRATEGY LAB (CORRETTO)
# ==============================================================================
if st.session_state.raw_data is not None:
    # Applichiamo il filtro scelto nel menu a tendina
    df_filtered = st.session_state.raw_data.copy()
    if st.session_state.get('pub_filter', "Tutti") != "Tutti":
        df_filtered = df_filtered[df_filtered['Categoria Editore'] == st.session_state.pub_filter]

    col_left, col_right = st.columns([7, 3], gap="large")

    with col_left:
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Libri", len(df_filtered))
        m2.metric("Prezzo Avg", f"{df_filtered['Prezzo'].mean():.2f} €" if pd.notna(df_filtered['Prezzo'].mean()) else "N/D")
        m3.metric("BSR Avg", f"{int(df_filtered['BSR'].mean()):,}".replace(',', '.') if pd.notna(df_filtered['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df_filtered[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Editore"]], 
            use_container_width=True, height=750, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Titolo": st.column_config.TextColumn("Titolo (Cliccabile)", width="large"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f")
            }
        )

    with col_right:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia", placeholder="es. Trading online")
        target = st.text_input("Target", placeholder="es. Pensionati")
        
        # LOGICA FIX: Usiamo un pulsante che forza l'analisi basandosi su df_filtered
        if st.button("🪄 Genera Strategia AI", type="primary"):
            if nicchia and target:
                with st.spinner("L'AI sta analizzando la nicchia..."):
                    try:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        # Passiamo all'AI anche il contesto del filtro (se stiamo guardando independent o no)
                        filtro_attuale = st.session_state.get('pub_filter', 'Tutti')
                        prompt = f"""Agisci come esperto KDP. Nicchia: '{nicchia}'. Target: '{target}'. 
                        Il cliente sta analizzando libri di tipo: {filtro_attuale}.
                        Genera 3 titoli magnetici, sottotitoli SEO e una trama breve basata su questi dati."""
                        
                        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                        st.session_state.suggestions = response.choices[0].message.content
                    except Exception as e:
                        st.error(f"Errore API: {e}")
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("👈 Carica i file CSV per iniziare.")
