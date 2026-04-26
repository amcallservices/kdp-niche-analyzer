import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 13.5", page_icon="📈", layout="wide")

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

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v13.5</div>", unsafe_allow_html=True)

# --- STATO ---
for key in ['raw_data', 'suggestions', 'selected_market', 'pub_filter', 'raw_cols']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# 2. SIDEBAR (NUMERAZIONE AUTOMATICA + OMNI-MAPPER)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 1: IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt_choice

    uploaded_file = st.file_uploader("Carica CSV di Amazon", type=["csv"])
    pub_choice = st.selectbox("Tipo Editore", ["Tutti", "Independent", "Publishing House"])
    st.session_state.pub_filter = pub_choice

    if st.button("📊 Elabora Dati", type="primary"):
        if uploaded_file:
            try:
                try:
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
                except:
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1')

                cols = df_raw.columns.tolist()
                st.session_state.raw_cols = cols 
                
                def find_col(keywords):
                    for k in keywords:
                        for c in cols:
                            if k.lower() in str(c).lower().strip(): return c
                    return None

                mapped_df = pd.DataFrame()
                
                # 1. Copertina
                img_col = find_col(['image', 'img', 'thumbnail', 'photo', 'url', 'src', 'copertina', 'a-dynamic-image'])
                mapped_df['Copertina'] = df_raw[img_col] if img_col else None
                
                # 2. TITOLO: AL POSTO DEL TESTO, USIAMO I NUMERI
                mapped_df['N. Libro'] = range(1, len(df_raw) + 1)
                
                # 3. BSR
                b_col = find_col(['bsr', 'rank', 'classifica', 'sales', 'posizione', 'ranking', 'best sellers'])
                if b_col:
                    mapped_df['BSR'] = pd.to_numeric(df_raw[b_col].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce')
                else:
                    mapped_df['BSR'] = np.nan
                
                # 4. Prezzo
                p_col = find_col(['price', 'prezzo', 'list price', 'buy price', 'costo', 'a-offscreen', 'a-price'])
                if p_col:
                    mapped_df['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                else:
                    mapped_df['Prezzo'] = np.nan
                
                # 5. Recensioni
                r_col = find_col(['review count', 'ratings', 'recensioni', 'voti', 'reviews', 's-underline-text', 'a-size-base', 'rating-count'])
                if r_col:
                    mapped_df['Recensioni'] = pd.to_numeric(df_raw[r_col].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce')
                else:
                    mapped_df['Recensioni'] = np.nan

                # 6. Editore
                e_col = find_col(['brand', 'manufacturer', 'author', 'editore', 'publisher', 'marca', 'vendor', 'byline', 'a-color-secondary'])
                if e_col:
                    mapped_df['Editore'] = df_raw[e_col].apply(lambda x: "Independent" if any(s in str(x).lower() for s in ['independently', 'kdp', 'indipendente', 'createspace', 'self']) else "Publishing House")
                else:
                    mapped_df['Editore'] = "N/D"

                st.session_state.raw_data = mapped_df
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("Carica un file prima.")

    if st.session_state.raw_cols:
        with st.expander("🛠️ Debug Colonne CSV"):
            st.write(st.session_state.raw_cols)

    if st.button("🔄 Reset"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.session_state.raw_cols = None
        st.rerun()

# ==============================================================================
# 3. DASHBOARD
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data
    if st.session_state.pub_filter != "Tutti":
        df = df[df['Editore'] == st.session_state.pub_filter]

    col_left, col_right = st.columns([7, 3], gap="large")

    with col_left:
        st.markdown(f"<div class='section-title'>Dati Mercato ({st.session_state.selected_market})</div>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Libri Analizzati", len(df))
        p_mean = df['Prezzo'].mean()
        c2.metric("Prezzo Medio", f"{p_mean:.2f} €" if pd.notna(p_mean) else "N/D")
        b_mean = df['BSR'].mean()
        c3.metric("BSR Medio", f"{int(b_mean)}" if pd.notna(b_mean) else "N/D")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.dataframe(
            df, 
            use_container_width=True, 
            height=700, 
            hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Copertina"),
                "N. Libro": st.column_config.NumberColumn("ID Libro", help="Numero sequenziale al posto del titolo"),
                "Prezzo": st.column_config.NumberColumn("Prezzo", format="%.2f €"),
                "BSR": st.column_config.NumberColumn("BSR", format="%d"),
                "Recensioni": st.column_config.NumberColumn("Recensioni", format="%d")
            }
        )

    with col_right:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia", placeholder="es. Yoga for Seniors")
        target = st.text_input("Target", placeholder="es. Principianti assoluti")
        
        if st.button("🪄 Genera Strategia", type="primary"):
            if nicchia and target:
                with st.spinner("Analisi in corso..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"Analizza la nicchia '{nicchia}' per il target '{target}' sul mercato {st.session_state.selected_market}. Fornisci 3 titoli KDP, sottotitoli SEO e una trama breve."
                    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = response.choices[0].message.content
            else:
                st.error("Riempi i campi.")
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("👈 Carica il tuo file CSV nella sidebar per visualizzare l'analisi numerica.")
