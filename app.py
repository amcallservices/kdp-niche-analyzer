import streamlit as st
import pandas as pd
import openai
import re

# ==============================================================================
# 1. DESIGN SYSTEM: PREMIUM SAAS DASHBOARD (IMPORT EDITION)
# ==============================================================================
st.set_page_config(page_title="KDP OMNI-REASONER 13.0", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp { background-color: #f9fafb !important; }

        section[data-testid="stSidebar"] { 
            background-color: #1f2937 !important; 
            min-width: 350px !important;
            border-right: 1px solid #374151;
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] * { 
            color: #f3f4f6 !important; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #374151 !important;
            border: 1px solid #4b5563 !important;
            color: white !important;
            border-radius: 6px !important;
        }

        .program-title { 
            color: #111827 !important; 
            font-size: 2rem !important; 
            font-weight: 800; 
            margin-bottom: 1rem; 
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0.5rem;
        }
        .section-title {
            color: #374151 !important; 
            font-size: 1.2rem !important; 
            font-weight: 700; 
            margin-bottom: 1rem;
            margin-top: 1rem;
        }

        [data-testid="stMetricValue"] { color: #2563eb !important; font-weight: 800 !important; font-size: 1.8rem !important; }
        [data-testid="stMetricLabel"] p { color: #6b7280 !important; font-weight: 600 !important; text-transform: uppercase; font-size: 0.8rem; }
        .stMetric { background-color: white !important; border: 1px solid #e5e7eb; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

        [data-testid="stDataFrame"] {
            background-color: white; padding: 1rem; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
        }

        .ai-panel {
            background-color: white; padding: 1.5rem; border-radius: 8px;
            border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%;
        }

        .stButton button { border-radius: 6px !important; font-weight: 600 !important; width: 100%;}
        button[kind="primary"] { background-color: #2563eb !important; color: white !important; border: none !important; }
        button[kind="primary"]:hover { background-color: #1d4ed8 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='program-title'>KDP Market Intelligence Hub v13</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE STATO
# ==============================================================================
for key in ['raw_data', 'suggestions', 'selected_market', 'pub_filter']:
    if key not in st.session_state: st.session_state[key] = None

# ==============================================================================
# 3. SIDEBAR: CARICAMENTO FILE (STEP 1)
# ==============================================================================
with st.sidebar:
    st.markdown("<p style='font-weight:700; color:#9ca3af; font-size:0.8rem; margin-bottom:5px; margin-top:0;'>STEP 1: IMPORTA DATI REALI</p>", unsafe_allow_html=True)
    
    mkt_choice = st.selectbox("Marketplace di riferimento", ["US", "UK", "IT", "DE", "FR", "ES", "CA"])
    st.session_state.selected_market = mkt_choice

    uploaded_file = st.file_uploader("Carica CSV di Amazon", type=["csv"])
    
    pub_choice = st.selectbox("Filtra Tipo Editore", ["Tutti", "Independent", "Publishing House"])
    st.session_state.pub_filter = pub_choice

    st.markdown("---")
    if st.button("📊 Elabora Dati Caricati", type="primary"):
        if uploaded_file is not None:
            try:
                # Carichiamo il CSV
                df_raw = pd.read_csv(uploaded_file)
                
                # LOGICA DI MAPPING INTELLIGENTE
                # Cerchiamo di capire quali colonne corrispondono ai nostri dati
                cols = df_raw.columns.tolist()
                
                def find_col(keywords):
                    for k in keywords:
                        for c in cols:
                            if k.lower() in c.lower(): return c
                    return None

                mapped_df = pd.DataFrame()
                
                # Mappatura Titolo
                t_col = find_col(['title', 'titolo', 'product name'])
                if t_col: mapped_df['Titolo'] = df_raw[t_col]
                
                # Mappatura BSR
                b_col = find_col(['bsr', 'rank', 'classifica'])
                if b_col: mapped_df['BSR'] = df_raw[b_col].astype(str).str.replace(r'[^\d]', '', regex=True).replace('', '0').astype(int)
                
                # Mappatura Prezzo
                p_col = find_col(['price', 'prezzo'])
                if p_col: mapped_df['Prezzo'] = df_raw[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.').astype(float)
                
                # Mappatura Recensioni
                r_col = find_col(['review count', 'ratings', 'recensioni', 'reviews'])
                if r_col: mapped_df['Recensioni'] = df_raw[r_col].astype(str).str.replace(r'[^\d]', '', regex=True).replace('', '0').astype(int)

                # Determinazione Editore (basata su colonna Brand/Author o Manufacturer)
                e_col = find_col(['brand', 'manufacturer', 'author', 'editore', 'publisher'])
                if e_col:
                    mapped_df['Editore'] = df_raw[e_col].apply(lambda x: "Independent" if any(s in str(x).lower() for s in ['independently', 'kdp', 'indipendente']) else "Publishing House")
                else:
                    mapped_df['Editore'] = "N/D"

                st.session_state.raw_data = mapped_df
                st.success("File elaborato correttamente!")
            except Exception as e:
                st.error(f"Errore nella lettura del file: {e}")
        else:
            st.warning("Per favore, carica prima un file CSV.")

    if st.button("🔄 Reset"):
        st.session_state.raw_data = None
        st.session_state.suggestions = None
        st.rerun()

# ==============================================================================
# 4. DASHBOARD: ANALISI E AI LAB (STEP 2)
# ==============================================================================
if st.session_state.raw_data is not None:
    df = st.session_state.raw_data
    
    # Filtro Editore
    if st.session_state.pub_filter != "Tutti":
        df = df[df['Editore'] == st.session_state.pub_filter]

    col_left, col_right = st.columns([6, 4], gap="large")

    with col_left:
        st.markdown(f"<div class='section-title'>Dati Mercato Importati ({st.session_state.selected_market})</div>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Libri nel DB", len(df))
        c2.metric("Prezzo Medio", f"{df['Prezzo'].mean():.2f} €")
        c3.metric("BSR Medio", f"{int(df['BSR'].mean())}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, height=600, hide_index=True)

    with col_right:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='margin-top:0;'>✨ AI Strategy Lab</div>", unsafe_allow_html=True)
        
        nicchia = st.text_input("Nicchia individuata nel CSV", placeholder="es. Yoga for Seniors")
        target = st.text_input("Target Lettore", placeholder="es. Principianti assoluti")
        
        if st.button("🪄 Genera Strategia AI", type="primary"):
            if not nicchia or not target:
                st.error("Inserisci nicchia e target.")
            else:
                with st.spinner("L'AI sta analizzando i dati importati..."):
                    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    prompt = f"""
                    Agisci come esperto KDP. Analisi nicchia: '{nicchia}'. Target: '{target}'. 
                    Mercato: {st.session_state.selected_market}.
                    Genera 3 titoli magnetici, sottotitoli SEO e una trama breve.
                    """
                    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.suggestions = response.choices[0].message.content
        
        if st.session_state.suggestions:
            st.markdown("---")
            st.markdown(st.session_state.suggestions)
        
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("👈 Carica un file CSV esportato da un'estensione Amazon nella sidebar per iniziare l'analisi.")
