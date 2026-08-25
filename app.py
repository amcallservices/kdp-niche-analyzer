import streamlit as st
import pandas as pd
import openai
import re
import numpy as np

# ==============================================================================
# 1. DESIGN SYSTEM
# ==============================================================================
st.set_page_config(
    page_title="KDP OMNI-REASONER 18.6",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stAppHeader {display:none;}
        [data-testid="collapsedControl"] { display: none !important; }

        .stApp {
            background-color: #0d1117 !important;
            color: #c9d1d9 !important;
        }

        section[data-testid="stSidebar"] {
            background-color: #161b22 !important;
            border-right: 1px solid #30363d;
        }

        .program-title {
            color: #58a6ff !important;
            font-size: 2.2rem !important;
            font-weight: 800;
            border-bottom: 2px solid #30363d;
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
        }

        .profit-card {
            background: #1c2128;
            border: 1px solid #30363d;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            min-height: 150px;
        }

        .status-green {
            color: #3fb950;
            font-weight: bold;
        }

        .status-yellow {
            color: #d29922;
            font-weight: bold;
        }

        .status-red {
            color: #f85149;
            font-weight: bold;
        }

        .ai-panel {
            background-color: #161b22;
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #30363d;
            margin-top: 20px;
        }

        [data-testid="stMetricValue"] {
            color: #58a6ff !important;
            font-weight: 800;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    "<div class='program-title'>KDP Intelligence Hub v18.6 💰</div>",
    unsafe_allow_html=True
)

if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None

if 'ai_output' not in st.session_state:
    st.session_state.ai_output = None

if 'ai_plot' not in st.session_state:
    st.session_state.ai_plot = None


# ==============================================================================
# 2. LOGICA DI ESTRAZIONE POTENZIATA E BSR/PRICE/AUTHOR FIX
# ==============================================================================
with st.sidebar:

    st.header("📥 Configurazione")

    mkt = st.selectbox(
        "Marketplace",
        ["IT", "US", "UK", "DE", "FR", "ES"]
    )

    files = st.file_uploader(
        "Carica CSV Amazon",
        type=["csv"],
        accept_multiple_files=True
    )

    if st.button("📊 AVVIA ANALISI PROFITTO", type="primary"):

        if files:

            all_dfs = []

            for f in files:

                try:
                    df_raw = pd.read_csv(
                        f,
                        sep=None,
                        engine='python',
                        on_bad_lines='skip'
                    )

                except:
                    f.seek(0)

                    df_raw = pd.read_csv(
                        f,
                        sep=None,
                        engine='python',
                        encoding='latin-1',
                        on_bad_lines='skip'
                    )

                cols = df_raw.columns.tolist()

                temp = pd.DataFrame(index=df_raw.index)

                for col_name in [
                    "Copertina",
                    "Titolo",
                    "BSR",
                    "Prezzo",
                    "Autore",
                    "Recensioni"
                ]:
                    temp[col_name] = np.nan


                # --------------------------------------------------------------
                # CICLO AVANZATO RIGA PER RIGA PER I NUOVI FORMATI AMAZON
                # --------------------------------------------------------------
                bsrs = []
                authors = []
                prices = []

                for _, row in df_raw.iterrows():

                    # ==========================================================
                    # 1. BSR ESTRAZIONE
                    # ==========================================================
                    ranks = []

                    for v in row.dropna():

                        v_s = str(v).strip()

                        if 'http' not in v_s.lower() and len(v_s) < 200:

                            if any(
                                k in v_s.lower()
                                for k in [
                                    '#',
                                    'n.',
                                    'pos.',
                                    'rank',
                                    'classifica',
                                    'bestseller'
                                ]
                            ):

                                matches = re.findall(
                                    r'\d+(?:[.,]\d+)*',
                                    v_s
                                )

                                for m in matches:

                                    try:

                                        val = int(
                                            m.replace('.', '').replace(',', '')
                                        )

                                        if val > 0:
                                            ranks.append(val)

                                    except:
                                        continue

                    bsrs.append(
                        max(ranks) if ranks else np.nan
                    )


                    # ==========================================================
                    # 2. AUTORE ESTRAZIONE
                    # ==========================================================
                    auth = "N/D"

                    for i, c in enumerate(cols):

                        val_c = str(row[c]).strip()

                        c_lower = str(c).lower()

                        if (
                            "author" in c_lower
                            or val_c.lower() in [
                                "author",
                                "di",
                                "by",
                                "da"
                            ]
                        ):

                            if val_c.lower() in [
                                "author",
                                "di",
                                "by",
                                "da"
                            ]:

                                for j in range(1, 4):

                                    if i + j < len(cols):

                                        candidate = str(
                                            row[cols[i + j]]
                                        ).strip()

                                        if (
                                            candidate
                                            and candidate.lower() != 'nan'
                                            and 'http' not in candidate
                                        ):

                                            auth = candidate
                                            break

                            else:
                                auth = val_c

                            break


                    # ----------------------------------------------------------
                    # Fallback intelligente per gli autori nei nuovi CSV
                    # ----------------------------------------------------------
                    if auth == "N/D":

                        for c in cols:

                            if any(
                                k in str(c).lower()
                                for k in [
                                    'secondary',
                                    'color-base 2',
                                    'sc-cddgoi'
                                ]
                            ):

                                cand = str(row[c]).strip()

                                if (
                                    cand
                                    and cand.lower() != 'nan'
                                    and 'http' not in cand
                                    and len(cand) > 2
                                ):

                                    # Seleziona testo escludendo date
                                    # o prezzi anomali
                                    if len(re.findall(r'\d', cand)) < 3:

                                        auth = cand
                                        break

                    authors.append(
                        re.sub(
                            r'^(di|by|da|Author:)\s+',
                            '',
                            auth,
                            flags=re.IGNORECASE
                        )
                    )


                    # ==========================================================
                    # 3. PREZZO ESTRAZIONE
                    # ==========================================================
                    # Ignora le false colonne testuali come "aok-offscreen"
                    p = np.nan

                    for c in cols:

                        c_lower = str(c).lower()

                        if (
                            any(
                                k in c_lower
                                for k in [
                                    'price',
                                    'prezzo',
                                    'offscreen'
                                ]
                            )
                            and not any(
                                x in c_lower
                                for x in [
                                    'aok',
                                    'symbol',
                                    'fraction',
                                    'decimal',
                                    'whole'
                                ]
                            )
                        ):

                            val = str(row[c]).strip()

                            if val.lower() != 'nan' and val != '':

                                try:

                                    # Pulisce lettere o simboli valutari
                                    # lasciando solo numeri e virgole/punti
                                    cleaned = "".join(
                                        filter(
                                            lambda x:
                                            x.isdigit()
                                            or x in ".,",
                                            val
                                        )
                                    )

                                    if ',' in cleaned and '.' in cleaned:

                                        cleaned = cleaned.replace(',', '')

                                    else:

                                        cleaned = cleaned.replace(',', '.')

                                    num = float(cleaned)

                                    if num > 0:

                                        p = num
                                        break

                                except:
                                    continue

                    prices.append(p)


                # ==============================================================
                # MAPPIAMO I DATI TROVATI SULLE COLONNE DEL DATAFRAME
                # ==============================================================
                temp['BSR'] = bsrs
                temp['Autore'] = authors
                temp['Prezzo'] = prices


                # ==============================================================
                # MAPPING IMMAGINE, TITOLO E RECENSIONI
                # CON FILTRO ANTI-ESCA AMAZON (v18.6)
                # ==============================================================

                # --------------------------------------------------------------
                # COPERTINA
                # --------------------------------------------------------------
                img_c = None

                for k in [
                    's-image src',
                    'image',
                    'copertina',
                    'src'
                ]:

                    img_c = next(
                        (
                            c
                            for c in cols
                            if k in c.lower()
                        ),
                        None
                    )

                    if img_c:
                        break

                if img_c:
                    temp['Copertina'] = df_raw[img_c]


                # --------------------------------------------------------------
                # TITOLO
                # --------------------------------------------------------------
                tit_c = None

                # Ordine di priorità ottimizzato e filtro per escludere
                # le colonne fisse inserite da Amazon
                for k in [
                    'title',
                    'titolo',
                    'name',
                    'line-clamp-1',
                    'a-size-medium',
                    'a-size-base-plus',
                    'a-size-medium-plus',
                    'sc-epzla-d'
                ]:

                    tit_c = next(
                        (
                            c
                            for c in cols
                            if (
                                k in c.lower()
                                and len(
                                    df_raw[c]
                                    .dropna()
                                    .unique()
                                ) > 3
                            )
                        ),
                        None
                    )

                    if tit_c:
                        break

                if tit_c:
                    temp['Titolo'] = df_raw[tit_c]


                # --------------------------------------------------------------
                # RECENSIONI
                # --------------------------------------------------------------
                rev_c = None

                for k in [
                    'review',
                    'voti',
                    'rating',
                    'a-size-mini',
                    'a-size-base'
                ]:

                    rev_c = next(
                        (
                            c
                            for c in cols
                            if k in c.lower()
                        ),
                        None
                    )

                    if rev_c:
                        break

                if rev_c:

                    def cl_rev(v):

                        n = re.findall(
                            r'\b\d+\b',
                            str(v)
                            .replace('.', '')
                            .replace(',', '')
                        )

                        return (
                            int(max(n, key=int))
                            if n
                            else np.nan
                        )

                    temp['Recensioni'] = df_raw[rev_c].apply(cl_rev)


                # ==============================================================
                # PULIZIA RIGHE VUOTE E RIMOZIONE DUPLICATI
                # ==============================================================
                temp = temp[
                    temp['Titolo'].notna()
                ]

                temp = temp[
                    temp['Titolo']
                    .astype(str)
                    .str.strip() != ''
                ]

                temp = temp[
                    temp['Titolo']
                    .astype(str)
                    .str.lower() != 'nan'
                ]

                temp = (
                    temp
                    .sort_values(
                        'BSR',
                        na_position='last'
                    )
                    .drop_duplicates(
                        subset=['Titolo'],
                        keep='first'
                    )
                )

                all_dfs.append(temp)


            st.session_state.raw_data = pd.concat(
                all_dfs,
                ignore_index=True
            )

            st.session_state.raw_data.insert(
                1,
                'ID',
                range(
                    1,
                    len(st.session_state.raw_data) + 1
                )
            )

            st.session_state.ai_output = None
            st.session_state.ai_plot = None

            st.rerun()


    if st.button("🔄 RESET"):

        st.session_state.raw_data = None
        st.session_state.ai_output = None
        st.session_state.ai_plot = None

        st.rerun()


# ==============================================================================
# 3. PROFITABILITY ANALYSIS & GRAPHICAL INSIGHTS
# ==============================================================================
if st.session_state.raw_data is not None:

    df = st.session_state.raw_data.copy()

    avg_bsr = (
        df['BSR'].mean()
        if not df['BSR'].isna().all()
        else 0
    )

    avg_price = (
        df['Prezzo'].mean()
        if not df['Prezzo'].isna().all()
        else 0
    )


    st.markdown(
        "### 📈 Valutazione Ragionata della Nicchia"
    )

    c1, c2, c3 = st.columns(3)


    # ==========================================================================
    # PROFITTABILITÀ
    # ==========================================================================
    with c1:

        if avg_bsr > 0 and avg_bsr < 80000:

            status = "PROFITTABILITÀ ALTA"
            color = "status-green"
            desc = "Volume di vendite elevato. Ottima nicchia."

        elif avg_bsr > 0 and avg_bsr < 150000:

            status = "PROFITTABILITÀ MEDIA"
            color = "status-yellow"
            desc = "Richiede Ads attive."

        else:

            status = "PROFITTABILITÀ BASSA"
            color = "status-red"
            desc = "Poche vendite o mercato saturo."

        st.markdown(
            f"""
            <div class='profit-card'>
                <p style='color:#8b949e;'>
                    VENDITE STIMATE
                </p>
                <h2 class='{color}'>
                    {status}
                </h2>
                <p>
                    {desc}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


    # ==========================================================================
    # ECONOMIA
    # ==========================================================================
    with c2:

        p_status = (
            "BUON MARGINE"
            if avg_price > 12
            else "BASSO MARGINE"
        )

        p_color = (
            "status-green"
            if avg_price > 12
            else "status-red"
        )

        st.markdown(
            f"""
            <div class='profit-card'>
                <p style='color:#8b949e;'>
                    ECONOMIA
                </p>
                <h2 class='{p_color}'>
                    {p_status}
                </h2>
                <p>
                    Prezzo medio: {avg_price:.2f}€
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


    # ==========================================================================
    # VERDETTO
    # ==========================================================================
    with c3:

        verdict = (
            "ECCELLENTE"
            if (
                avg_bsr < 80000
                and avg_bsr > 0
                and avg_price > 12
            )
            else "VALUTARE"
        )

        st.markdown(
            f"""
            <div class='profit-card'>
                <p style='color:#8b949e;'>
                    VERDETTO FINALE
                </p>
                <h2 style='color:#58a6ff;'>
                    {verdict}
                </h2>
                <p>
                    Analisi su {len(df)} concorrenti.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


    # ==========================================================================
    # ANALISI GRAFICA
    # ==========================================================================
    st.markdown(
        "### 📊 Market Insights (Analisi Grafica)"
    )

    g1, g2 = st.columns(2)


    with g1:

        # Mostra TUTTI i competitor per BSR
        # rimuovendo il limite .head(10)
        bsr_chart_data = (
            df
            .dropna(subset=['BSR'])
            .sort_values('BSR')
        )

        if not bsr_chart_data.empty:

            st.write(
                "**Competitor per Ranking (BSR)**"
            )

            st.bar_chart(
                data=bsr_chart_data,
                x="Titolo",
                y="BSR",
                color="#58a6ff"
            )

        else:

            st.info(
                "⚠️ Dati BSR non presenti nei file per generare "
                "il grafico. Carica una classifica Bestseller "
                "per visualizzarli."
            )


    with g2:

        # Distribuzione Prezzi
        if not df['Prezzo'].isna().all():

            st.write(
                "**Andamento Prezzi di Mercato (€)**"
            )

            st.line_chart(
                df['Prezzo']
            )

        else:

            st.info(
                "⚠️ Dati Prezzo non disponibili per il grafico."
            )


    st.markdown("---")


    # ==============================================================================
    # 4. TABELLA DATI E STEP 2 (AI STRATEGY LAB)
    # ==============================================================================
    col_table, col_ai = st.columns([7, 3])


    with col_table:

        st.markdown(
            """
            <p style='font-weight:bold; font-size:1.2rem;'>
                Dati Estratti (BSR Globale Corretto)
            </p>
            """,
            unsafe_allow_html=True
        )

        cols_to_show = [
            "Copertina",
            "ID",
            "Titolo",
            "BSR",
            "Prezzo",
            "Autore",
            "Recensioni"
        ]

        st.dataframe(
            df[cols_to_show],
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config={
                "Copertina": st.column_config.ImageColumn(
                    "Cover",
                    width="small"
                ),
                "Titolo": st.column_config.TextColumn(
                    "Titolo",
                    width="large"
                ),
                "Prezzo": st.column_config.NumberColumn(
                    "Prezzo (€)",
                    format="%.2f"
                ),
                "BSR": st.column_config.NumberColumn(
                    "BSR Rank",
                    format="%d"
                )
            }
        )


        # ======================================================================
        # NUOVA FUNZIONE:
        # DOWNLOAD CSV COMPLETO DEI RISULTATI DELL'ANALISI
        # ======================================================================

        df_export = df.copy()

        # Aggiunge i dati tecnici generali dell'analisi
        df_export["Marketplace"] = mkt

        df_export["BSR Medio Nicchia"] = round(
            avg_bsr,
            2
        )

        df_export["Prezzo Medio Nicchia"] = round(
            avg_price,
            2
        )

        df_export["Numero Competitor Analizzati"] = len(df)

        df_export["Valutazione Profittabilita"] = status

        df_export["Valutazione Margine"] = p_status

        df_export["Verdetto Finale"] = verdict


        # Ordine colonne del CSV
        colonne_export = [
            "ID",
            "Titolo",
            "Autore",
            "BSR",
            "Prezzo",
            "Recensioni",
            "Copertina",
            "Marketplace",
            "BSR Medio Nicchia",
            "Prezzo Medio Nicchia",
            "Numero Competitor Analizzati",
            "Valutazione Profittabilita",
            "Valutazione Margine",
            "Verdetto Finale"
        ]

        df_export = df_export[colonne_export]


        # Crea CSV compatibile con Excel
        csv_export = df_export.to_csv(
            index=False,
            encoding="utf-8-sig",
            sep=";"
        ).encode("utf-8-sig")


        st.download_button(
            label="⬇️ SCARICA ANALISI COMPLETA CSV",
            data=csv_export,
            file_name=f"KDP_Analisi_Completa_{mkt}.csv",
            mime="text/csv",
            use_container_width=True
        )


    # ==============================================================================
    # STEP 2: AI STRATEGY LAB
    # ==============================================================================
    with col_ai:

        st.markdown(
            "<div class='ai-panel' style='margin-top:0px;'>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<h3>✨ Step 2: AI Strategy Lab</h3>",
            unsafe_allow_html=True
        )

        nicchia_target = st.text_input(
            "Nicchia analizzata"
        )


        if st.button("🪄 GENERA STRATEGIA"):

            if (
                nicchia_target
                and not df['Titolo'].isna().all()
            ):

                with st.spinner(
                    "L'IA sta analizzando tutti i dati "
                    "completi dei file..."
                ):

                    try:

                        client = openai.OpenAI(
                            api_key=st.secrets[
                                "OPENAI_API_KEY"
                            ]
                        )


                        # ------------------------------------------------------
                        # Determina la lingua in base al Marketplace scelto
                        # ------------------------------------------------------
                        lingue_mercato = {
                            "IT": "Italiano",
                            "US": "Inglese Americano",
                            "UK": "Inglese Britannico",
                            "DE": "Tedesco",
                            "FR": "Francese",
                            "ES": "Spagnolo"
                        }

                        lingua_destinazione = (
                            lingue_mercato.get(
                                mkt,
                                "Inglese"
                            )
                        )


                        # ------------------------------------------------------
                        # Estrae TUTTI I DATI
                        # ------------------------------------------------------
                        colonne_utili = [
                            'Titolo',
                            'Autore',
                            'Prezzo',
                            'BSR',
                            'Recensioni'
                        ]

                        tutti_i_dati = (
                            df[colonne_utili]
                            .to_csv(
                                index=False,
                                sep='|'
                            )
                        )


                        # ------------------------------------------------------
                        # Aggiunta la forzatura per la lingua target
                        # ------------------------------------------------------
                        prompt = (
                            f"Sei un esperto di KDP per {mkt}. "
                            f"Nicchia: {nicchia_target}. "
                            f"Ecco TUTTI i dati completi dei competitor "
                            f"(Titolo, Autore, Prezzo, BSR, Recensioni):\n"
                            f"{tutti_i_dati}\n\n"
                            f"Basandoti su un'attenta analisi di tutti "
                            f"questi dati incrociati, genera 5 Titoli "
                            f"e 5 Sottotitoli SEO. "
                            f"DEVI SCRIVERLI ESCLUSIVAMENTE IN LINGUA: "
                            f"{lingua_destinazione}."
                        )


                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        )


                        st.session_state.ai_output = (
                            response
                            .choices[0]
                            .message
                            .content
                        )


                    except Exception as e:

                        st.error(
                            f"Errore AI: {e}"
                        )


            else:

                st.warning(
                    "Inserisci la nicchia."
                )


        if st.session_state.ai_output:

            st.markdown("---")

            st.markdown(
                st.session_state.ai_output
            )


        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


    # ==============================================================================
    # 5. STEP 3: BOOK ARCHITECT (TRAMA E OBIETTIVO)
    # ==============================================================================
    st.markdown("---")

    st.markdown(
        "<div class='ai-panel'>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h3>✍️ Step 3: Book Architect (Obiettivo & Trama)</h3>",
        unsafe_allow_html=True
    )


    col_input, col_empty = st.columns([1, 1])


    with col_input:

        titolo_scelto = st.text_input(
            "Inserisci il Titolo del Libro scelto "
            "per generare la Trama:"
        )


    if st.button(
        "📝 ELABORA TRAMA DETTAGLIATA",
        type="primary"
    ):

        if titolo_scelto:

            with st.spinner(
                "Generazione trama in corso..."
            ):

                try:

                    client = openai.OpenAI(
                        api_key=st.secrets[
                            "OPENAI_API_KEY"
                        ]
                    )


                    lingue_mercato = {
                        "IT": "Italiano",
                        "US": "Inglese Americano",
                        "UK": "Inglese Britannico",
                        "DE": "Tedesco",
                        "FR": "Francese",
                        "ES": "Spagnolo"
                    }


                    lingua_destinazione = (
                        lingue_mercato.get(
                            mkt,
                            "Inglese"
                        )
                    )


                    prompt_trama = f"""
                    Sei un Ghostwriter professionista e Book Architect
                    per il mercato Amazon KDP.

                    Titolo del libro:
                    "{titolo_scelto}".

                    Mercato target:
                    {mkt}.

                    REGOLA FONDAMENTALE:
                    Devi redigere l'obiettivo del libro e l'intera
                    outline (titoli dei capitoli, sotto-argomenti
                    e descrizioni) ESCLUSIVAMENTE in
                    {lingua_destinazione}.

                    Se il mercato non è IT, non devi utilizzare MAI
                    l'italiano nella tua risposta.

                    STRUTTURA:

                    1. OBIETTIVO:
                    Core promise e trasformazione del lettore.

                    2. OUTLINE:
                    Struttura complessa e dettagliata capitolo
                    per capitolo con 3-4 sotto-argomenti avanzati
                    per ciascuno.
                    """


                    response_trama = (
                        client
                        .chat
                        .completions
                        .create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "user",
                                    "content": prompt_trama
                                }
                            ]
                        )
                    )


                    st.session_state.ai_plot = (
                        response_trama
                        .choices[0]
                        .message
                        .content
                    )


                except Exception as e:

                    st.error(
                        f"Errore AI: {e}"
                    )


        else:

            st.warning(
                "Inserisci un titolo."
            )


    if st.session_state.ai_plot:

        st.markdown(
            "<hr style='border-color:#30363d;'>",
            unsafe_allow_html=True
        )

        st.markdown(
            st.session_state.ai_plot
        )


    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


else:

    st.info(
        "🌙 Carica i tuoi file CSV per iniziare "
        "l'analisi di mercato."
    )
