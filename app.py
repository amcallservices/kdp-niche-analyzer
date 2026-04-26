import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM (DARK MODE PER AI PANEL AGGIUNTA)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 15.5", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }
        .stApp { background-color: #f9fafb !important; }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] { background-color: #111827 !important; min-width: 350px !important; border-right: 1px solid #374151; padding-top: 1rem; }
        section[data-testid="stSidebar"] * { color: #f3f4f6 !important; }
        
        /* Titoli e Testi */
        .program-title { color: #111827 !important; font-size: 2rem !important; font-weight: 800; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.5rem; margin-bottom: 1rem; }
        .section-title { color: #374151 !important; font-size: 1.2rem !important; font-weight: 700; margin-bottom: 1rem; }
        
        /* DARK AI PANEL STYLING */
        .ai-panel { 
            background-color: #1f2937; 
            padding: 2rem; 
            border-radius: 12px; 
            border: 1px solid #374151; 
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
            color: #ffffff !important;
        }
        .ai-panel h3, .ai-panel p, .ai-panel span { color: #ffffff !important; }
        .ai-panel label { color: #9ca3af !important; font-weight: 600; }
        
        /* Button Styling */
        .stButton button { border-radius: 8px !important; font-weight: 600 !important; width: 100%; transition: 0.3s; }
        button[kind="primary"] { background-color: #3b82f6 !important; color: white !important; border: none !important; }
        button[kind="primary"]:hover { background-color: #2563eb !important; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5); }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v15.5</div>", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE STATO ---
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'suggestions' not in st.session_state: st.session_state.suggestions = None

# ==============================================================================
# 2. SIDEBAR (LOGICA MULTI-FILE & FILTRI)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#60a5fa; font-size:0.9rem;'>STEP 1: CARICAMENTO DI MASSA</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt_choice
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt_choice]}"

    uploaded_files = st.file_uploader("Trascina fino a 100 CSV", type=["csv"], accept_multiple_files=True)

    if st.button("📊 Elabora Tutti i File", type="primary"):
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
                
                # MAPPING DATI
                img_col = find_col(['s-image src', 'a-dynamic-image src', 'src', 'image'])
                temp['Copertina'] = df_raw[img_col] if img_col else None
                
                t_col = find_col(['a-size-medium', 'line-clamp', 'title', 'titolo', 'name'])
                raw_t = df_raw[t_col].fillna("N/D").astype(str) if t_col else pd.Series(["N/D"] * len(df_raw))
                link_col = find_col(['href', 'url', 'link'])
                def get_url(i):
                    if not link_col: return None
                    val = str(df_raw.iloc[i][link_col])
                    return val if 'http' in val else f"{base_url}{val}"
                temp['Titolo'] = [f"[{str(t).replace('[','').replace(']','')}]({get_url(i)})" if get_url(i) else str(t) for i, t in enumerate(raw_t)]
                
                b_col = find_col(['zg-bdg-text', 'rank', 'bsr', 'classifica'])
                if b_col:
                    def clean_bsr(val):
                        m = re.search(r'#?(\d{1,3}(?:[.,]\d{3})*|\d+)', str(val))
                        return int(m.group(1).replace('.','').replace(',','')) if m else np.nan
                    temp['BSR'] = df_raw[b_col].apply(clean_bsr)
                else: temp['BSR'] = np.nan

                p_col = find_col(['a-offscreen', 'price', 'prezzo', 'p13n-sc-price'])
                if p_col: temp['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                
                r_col = find_col(['a-size-base', 'voti', 'review', 'rating'])
                if r_col:
                    def clean_r(val):
                        n = re.findall(r'\b\d+\b', str(val).replace('.','').replace(',',''))
                        return int(max(n, key=int)) if n else np.nan
                    temp['Recensioni'] = df_raw[r_col].apply(clean_r)
                
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
            st.session_state.suggestions = None
            st.rerun()

    if st.session_state.raw_data is not None:
        st.markdown("---")
        st.markdown("<p style='font-weight:700; color:#60a5fa; font-size:0.9rem;'>STEP 2: FILTRO CATEGORIA</p>", unsafe_allow_html=True)
        tipo_filtro = st.selectbox("Seleziona Tipo Editore:", ["Tutti", "Independent", "Publishing House"])
        st.session_state.pub_filter = tipo_filtro

    if st.button("🔄 Reset"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD E AI STRATEGY LAB (DARK MODE)
# ==============================================================================
if st.session_state.raw_data is not None:
    df_f = st.session_state.raw_data.copy()
    if st.session_state.get('pub_filter', "Tutti") != "Tutti":
        df_f = df_f[df_f['Categoria Editore'] == st.session_state.pub_filter]

    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Libri", len(df_f))
        c2.metric("Prezzo Medio", f"{df_f['Prezzo'].mean():.2f} €" if pd.notna(df_f['Prezzo'].mean()) else "N/D")
        c3.metric("BSR Medio", f"{int(df_f['BSR'].mean()):,}".replace(',', '.') if pd.notna(df_f['BSR'].mean()) else "N/D")
        
        st.dataframe(
            df_f[["Copertina", "N. Libro", "BSR", "Titolo", "Prezzo", "Recensioni", "Nome Editore"]], 
            use_container_width=True, height=800, hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Cover"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "Titolo": st.column_config.TextColumn("Titolo (Cliccabile)", width="large")
            }
        )

    with col_r:
        # APERTURA PANEL DARK
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; color:#3b82f6;'>✨ AI Strategy Lab</h3>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.9rem; color:#9ca3af;'>Analisi avanzata basata sui dati filtrati</p>", unsafe_allow_html=True)
        
        nicchia = st.text_input("Definisci Nicchia")
        target = st.text_input("Definisci Target")
        
        if st.button("🪄 Genera Strategia KDP", type="primary"):
            if nicchia and target:
                with st.spinner("AI al lavoro..."):
                    try:
                        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        tipo = st.session_state.get('pub_filter', 'Tutti')
                        prompt = f"Sei un esperto KDP. Analizza la nicchia '{nicchia}' per il target '{target}'. Filtro: {tipo}. Suggerisci 3 titoli, sottotitoli SEO e trama."
                        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                        st.session_state.suggestions = res.choices[0].message.content
                    except Exception as e:
                        st.error(f"Errore: {e}")
        
        if st.session_state.suggestions:
            st.markdown("<br><hr style='border-color:#374151;'><br>", unsafe_allow_html=True)
            st.markdown(st.session_state.suggestions)
            
        st.markdown("</div>", unsafe_allow_html=True) # CHIUSURA PANEL DARK
else:
    st.info("👈 Carica i file CSV per avviare l'analisi.")
