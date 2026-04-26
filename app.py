import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.1", page_icon="📈", layout="wide")

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

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.1 (Smart Filter)</div>", unsafe_allow_html=True)

# --- STATO ---
for key in ['raw_data', 'suggestions', 'selected_market', 'raw_cols']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# 2. SIDEBAR E LOGICA DI IMPORT MULTI-FILE
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 1: IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt_choice
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt_choice]}"

    uploaded_files = st.file_uploader("Carica CSV di Amazon (Puoi selezionarne a decine!)", type=["csv"], accept_multiple_files=True)

    if st.button("📊 Elabora Tutti i Dati", type="primary"):
        if uploaded_files:
            try:
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
                                clean_c = str(c).lower().strip().replace('\n', ' ').replace('\r', '')
                                if k.lower() in clean_c: return c
                        return None

                    mapped_df = pd.DataFrame(index=df_raw.index)
                    
                    # --- A: COPERTINA ---
                    img_col = find_col(['s-image src', 'a-dynamic-image src', 'src', 'image', 'img', 'thumbnail', 'copertina'])
                    mapped_df['Copertina'] = df_raw[img_col] if img_col else None
                    
                    # --- B: TITOLO E LINK ---
                    t_col = find_col(['a-size-medium', '_cdezb_p13n-sc-css-line-clamp-1_1fn1y', 'title', 'titolo', 'name', 'nome', 'text-normal'])
                    raw_titles = df_raw[t_col].fillna("Titolo non disponibile").astype(str) if t_col else pd.Series(["N/D"] * len(df_raw))
                    
                    link_col = find_col(['a-link-normal href', 'href', 'url', 'link'])
                    asin_col = find_col(['asin', 'id'])
                    
                    def make_url(row_idx):
                        if link_col:
                            val = str(df_raw.iloc[row_idx][link_col])
                            if 'http' in val: return val
                            if val.startswith('/'): return f"{base_url}{val}"
                        if asin_col:
                            asin_val = str(df_raw.iloc[row_idx][asin_col]).strip()
                            if len(asin_val) >= 10: return f"{base_url}/dp/{asin_val[:10]}"
                        return None

                    mapped_df['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({make_url(i)})" if make_url(i) else str(t) for i, t in enumerate(raw_titles)]
                    
                    # --- C: BSR (Rank) ---
                    b_col = find_col(['zg-bdg-text', 'bsr', 'rank', 'classifica', 'sales', 'best'])
                    if b_col:
                        def estrai_bsr_estremo(testo):
                            try:
                                t = str(testo).lower()
                                if t == 'nan' or t == 'none' or t == '' or pd.isna(testo): return np.nan
                                match = re.search(r'\b(\d{1,3}(?:[.,]\d{3})*|\d+)\b', t)
                                if match:
                                    numero_pulito = match.group(1).replace('.', '').replace(',', '')
                                    return int(numero_pulito)
                                return np.nan
                            except: return np.nan
                        mapped_df['BSR'] = df_raw[b_col].apply(estrai_bsr_estremo)
                    else:
                        mapped_df['BSR'] = np.nan
                    
                    # --- D: PREZZO ---
                    p_col = find_col(['a-offscreen', 'p13n-sc-price', '_cdezb_p13n-sc-price_3mj9z', 'price', 'prezzo', 'costo'])
                    if p_col:
                        mapped_df['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                    else:
                        mapped_df['Prezzo'] = np.nan
                    
                    # --- E: RECENSIONI ---
                    r_col = find_col(['a-size-mini', 'a-size-small', 'a-icon-alt', 'review', 'rating', 'recensioni', 'voti', 'count'])
                    if r_col:
                        def estrai_recensioni(testo):
                            testo = str(testo).replace('.', '').replace(',', '')
                            numeri = re.findall(r'\b\d+\b', testo)
                            if numeri:
                                return int(max(numeri, key=int))
                            return np.nan
                        mapped_df['Recensioni'] = df_raw[r_col].apply(estrai_recensioni)
                    else:
                        mapped_df['Recensioni'] = np.nan

                    # --- F: EDITORE E AUTORE ---
                    e_col = find_col(['a-size-base 2', 'a-color-secondary', 'brand', 'manufacturer', 'author', 'editore', 'publisher'])
                    if e_col:
                        def analizza_editore(val):
                            testo = str(val).replace('by ', '').replace('di ', '').strip()
                            if pd.isna(val) or testo.lower() == 'nan' or testo == '': return "N/D"
                            if any(s in testo.lower() for s in ['independently', 'kdp', 'indipendente', 'createspace']):
                                return "Independent"
                            return testo
                        mapped_df['Editore / Autore'] = df_raw[e_col].apply(analizza_editore)
                    else:
                        mapped_df['Editore / Autore'] = "N/D"

                    all_mapped_dfs.append(mapped_df)
                
                final_df = pd.concat(all_mapped_dfs, ignore_index=True)
                final_df.insert(1, 'N. Libro', range(1, len(final_df) + 1))
                
                st.session_state.raw_data = final_df
                st.session_state.raw_cols = list(set(all_cols_debug))
                st.success(f"Dati estratti e uniti con successo da {len(uploaded_files)} file CSV!")
            except Exception as e:
                st.error(f"Errore durante l'elaborazione dei file: {e}")
        else:
            st.warning("Carica almeno un file prima di elaborare.")

    # --- NUOVO FILTRO A TENDINA (Appare solo dopo aver elaborato i dati) ---
    if st.session_state.raw_data is not None:
        st.markdown("---")
        st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 2: FILTRA DATI</p>", unsafe_allow_html=True)
        
        # Estrai la lista unica di tutti gli autori trovati, in ordine alfabetico
        autori_unici = sorted([str(x) for x in st.session_state.raw_data['Editore / Autore'].dropna().unique()])
        lista_opzioni = ["Tutti"] + autori_unici
        
        search_author = st.selectbox("Seleziona Autore / Editore", lista_opzioni)
    else:
        search_author = "Tutti"

    if st.session_state.raw_cols:
        with st.expander("🔍 Mapping Helper (Diagnostica CSV)"):
            st.write(st.session_state.raw_cols)

    if st.button("🔄 Reset Tabella"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.session_state.raw_cols = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD E TABELLA
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data
    
    # Applica Filtro Autore/Editore a tendina
    if search_author != "Tutti":
        df = df[df['Editore / Autore'] == search_author]

    col_left, col_right = st.columns([7, 3], gap="large")

    with col_left:
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Libri Mostrati", len(df))
        prezzo_medio = df['Prezzo'].mean()
        c2.metric("Prezzo Avg", f"{prezzo_medio:.2f} €" if pd.notna(prezzo_medio) else "N/D")
        bsr_medio = df['BSR'].mean()
        c3.metric("BSR Avg", f"{int(bsr_medio):,}".replace(',', '.') if pd.notna(bsr_medio) else "N/D")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        desired_order = ["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Editore / Autore"]
        actual_order = [c for c in desired_order if c in df.columns]
        df_display = df[actual_order]
        
        st.dataframe(
            df_display, 
            use_container_width=True, 
            height=700, 
            hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover", width="small"),
                "N. Libro": st.column_config.NumberColumn("ID", width="small"),
                "BSR": st.column_config.NumberColumn("BSR Rank", format="%d", width="small"),
                "Titolo": st.column_config.TextColumn("Titolo (Clicca per aprire)", width="large"),
                "Prezzo": st.column_config.NumberColumn("Prezzo", format="%.2f", width="small"),
                "Recensioni": st.column_config.NumberColumn("Recensioni", format="%d", width="small"),
                "Editore / Autore": st.column_config.TextColumn("Autore / Editore", width="medium")
            }
        )

    with col_right:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia analizzata", placeholder="es. Real Estate Investing")
        target = st.text_input("Target Lettore", placeholder="es. Principianti e impiegati")
        
        if st.button("🪄 Genera Idee KDP", type="primary"):
            if nicchia and target:
                with st.spinner("L'AI sta studiando i dati filtrati e generando la strategia..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"Basandoti sui dati combinati del mercato KDP {st.session_state.selected_market}, analizza la nicchia '{nicchia}' per il target '{target}'. Suggerisci 3 titoli magnetici, sottotitoli SEO e una trama persuasiva ispirata alle best practices del mercato."
                    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = response.choices[0].message.content
            else:
                st.error("Riempi i campi nicchia e target per avviare l'IA.")
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("👈 Trascina uno o più file CSV nella sidebar per avviare l'elaborazione di massa.")
