import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 13.9.1", page_icon="📈", layout="wide")

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

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v13.9.1</div>", unsafe_allow_html=True)

# --- STATO ---
for key in ['raw_data', 'suggestions', 'selected_market', 'pub_filter', 'raw_cols']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# 2. SIDEBAR E LOGICA DI IMPORT
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem;'>STEP 1: IMPORTA DATI</p>", unsafe_allow_html=True)
    mkt_choice = st.selectbox("Marketplace", ["IT", "US", "UK", "DE", "FR", "ES"])
    st.session_state.selected_market = mkt_choice
    
    domain_map = {"IT": "amazon.it", "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es"}
    base_url = f"https://www.{domain_map[mkt_choice]}"

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
                
                # 1. COPERTINA
                img_col = find_col(['image', 'img', 'thumbnail', 'photo', 'src', 'a-dynamic-image'])
                mapped_df['Copertina'] = df_raw[img_col] if img_col else None
                
                # 2. TITOLO E LINK
                t_col = find_col(['title', 'titolo', 'name', 'nome', 'product', 'text', 'a-size-medium', 'a-link-normal', 's-line-clamp'])
                raw_titles = df_raw[t_col].astype(str).replace('nan', 'Titolo non trovato') if t_col else pd.Series(["N/D"] * len(df_raw))
                
                link_col = find_col(['url', 'link', 'href', 'page url'])
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

                mapped_df['Titolo'] = [f"[{t}]({make_url(i)})" if make_url(i) else t for i, t in enumerate(raw_titles)]
                
                # 3. BSR (LA NUOVA LOGICA "TERMINATOR")
                b_col = find_col(['bsr', 'rank', 'classifica', 'sales', 'posizione', 'ranking', 'best sellers'])
                if b_col:
                    def estrai_primo_numero_pulito(testo):
                        if pd.isna(testo): return np.nan
                        # Converte in stringa
                        testo = str(testo)
                        # Rimuove tutto tranne numeri, punti e virgole
                        solo_numeri_e_punteggiatura = re.sub(r'[^\d.,]', '', testo)
                        # Rimuove punti e virgole (formattazione europea/USA) per avere il numero puro
                        numero_pulito = solo_numeri_e_punteggiatura.replace('.', '').replace(',', '')
                        # Se è rimasto un numero, lo restituisce come int
                        if numero_pulito.isdigit():
                            return int(numero_pulito)
                        return np.nan

                    mapped_df['BSR'] = df_raw[b_col].apply(estrai_primo_numero_pulito)
                else:
                    mapped_df['BSR'] = np.nan
                
                # 4. PREZZO
                p_col = find_col(['price', 'prezzo', 'list price', 'buy price', 'costo', 'a-offscreen', 'a-price'])
                if p_col:
                    mapped_df['Prezzo'] = pd.to_numeric(df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce')
                else:
                    mapped_df['Prezzo'] = np.nan
                
                # 5. RECENSIONI
                r_col = find_col(['review count', 'ratings', 'recensioni', 'voti', 'reviews', 's-underline-text', 'a-size-base', 'count'])
                if r_col:
                    mapped_df['Recensioni'] = pd.to_numeric(df_raw[r_col].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce')
                else:
                    mapped_df['Recensioni'] = np.nan

                # 6. EDITORE
                e_col = find_col(['brand', 'manufacturer', 'author', 'editore', 'publisher', 'marca', 'vendor', 'byline'])
                if e_col:
                    mapped_df['Editore'] = df_raw[e_col].apply(lambda x: "Independent" if any(s in str(x).lower() for s in ['independently', 'kdp', 'indipendente', 'createspace']) else "Publishing House")
                else:
                    mapped_df['Editore'] = "N/D"

                st.session_state.raw_data = mapped_df
                st.success("Dati estratti e puliti.")
            except Exception as e:
                st.error(f"Errore tecnico: {e}")
        else:
            st.warning("Carica un file prima.")

    if st.session_state.raw_cols:
        with st.expander("🔍 Mapping Helper"):
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
        st.markdown(f"<div class='section-title'>Mercato: {st.session_state.selected_market}</div>", unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Libri", len(df))
        m2.metric("Prezzo Avg", f"{df['Prezzo'].mean():.2f} €" if pd.notna(df['Prezzo'].mean()) else "N/D")
        m3.metric("BSR Avg", f"{int(df['BSR'].mean())}" if pd.notna(df['BSR'].mean()) else "N/D")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.dataframe(
            df, 
            use_container_width=True, 
            height=700, 
            hide_index=True,
            column_config={
                "Copertina": st.column_config.ImageColumn("Copertina", width="small"),
                "Titolo": st.column_config.TextColumn("Titolo (Cliccabile)", width="large"),
                "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="%.2f"),
                "BSR": st.column_config.NumberColumn("BSR Rank", format="%d"),
                "Recensioni": st.column_config.NumberColumn("Recensioni", format="%d")
            }
        )

    with col_right:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        nicchia = st.text_input("Nicchia analizzata", placeholder="es. Ricette Sane")
        target = st.text_input("Target Lettore", placeholder="es. Studenti fuori sede")
        
        if st.button("🪄 Genera Idee KDP", type="primary"):
            if nicchia and target:
                with st.spinner("L'AI sta studiando i dati..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"Basandoti sul mercato KDP {st.session_state.selected_market}, analizza la nicchia '{nicchia}' per il target '{target}'. Suggerisci 3 titoli magnetici, sottotitoli SEO e una trama persuasiva."
                    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = response.choices[0].message.content
            else:
                st.error("Riempi i campi nicchia e target.")
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("👈 Carica il file CSV nella sidebar.")
