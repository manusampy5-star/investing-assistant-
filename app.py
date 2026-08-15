import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# --- Configurazione Pagina Mobile-Friendly ---
st.set_page_config(
    page_title="AI Investment Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Gestione Stato dell'Applicazione ---
if "portfolio" not in st.session_state:
    # Portfolio iniziale predefinito (modificabile da interfaccia o sincronizzabile)
    st.session_state.portfolio = [
        {"Ticker": "VWCE.DE", "Nome": "Vanguard FTSE All-World UCITS ETF", "Quote": 25.0, "Prezzo_Carico": 112.50, "Categoria": "ETF Azionario Globale"},
        {"Ticker": "SXR8.DE", "Nome": "iShares Core S&P 500 UCITS ETF", "Quote": 5.0, "Prezzo_Carico": 480.00, "Categoria": "ETF USA"},
        {"Ticker": "MEUD.PA", "Nome": "Amundi Stoxx Europe 600", "Quote": 40.0, "Prezzo_Carico": 48.20, "Categoria": "ETF Europa"},
        {"Ticker": "NVDA", "Nome": "NVIDIA Corporation", "Quote": 12.0, "Prezzo_Carico": 110.00, "Categoria": "Azione Tech"},
        {"Ticker": "AAPL", "Nome": "Apple Inc.", "Quote": 10.0, "Prezzo_Carico": 185.00, "Categoria": "Azione Tech"}
    ]
if "liquidita" not in st.session_state:
    st.session_state.liquidita = 1500.00

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Funzioni di Recupero Dati di Mercato ---
@st.cache_data(ttl=300)
def get_live_market_data(tickers):
    """Scarica i prezzi correnti e le variazioni giornaliere tramite Yahoo Finance."""
    data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period="2d")
            if len(history) >= 2:
                current_price = history["Close"].iloc[-1]
                prev_close = history["Close"].iloc[-2]
                change_pct = ((current_price - prev_close) / prev_close) * 100
            elif len(history) == 1:
                current_price = history["Close"].iloc[-1]
                change_pct = 0.0
            else:
                current_price = None
                change_pct = 0.0
            data[ticker] = {"prezzo": current_price, "variazione": change_pct}
        except Exception:
            data[ticker] = {"prezzo": None, "variazione": 0.0}
    return data

# --- Sidebar: Configurazione & Connessione ---
with st.sidebar:
    st.title("⚙️ Impostazioni & Account")
    
    # Configurazione Gemini API
    api_key = st.text_input("Gemini API Key", type="password", help="Inserisci la tua chiave API ottenuta da Google AI Studio")
    
    st.markdown("---")
    st.subheader("🏦 Connessione Trade Republic")
    
    conn_mode = st.radio(
        "Modalità Connessione:",
        ["Dati Sincronizzati / Manuali", "Connessione Diretta API (Beta)"],
        index=0
    )
    
    if conn_mode == "Connessione Diretta API (Beta)":
        st.info("Nota di sicurezza: Trade Republic richiede autorizzazione 2FA su smartphone ad ogni sessione.")
        phone_num = st.text_input("Numero di Telefono (+39...)", value="")
        pin_code = st.text_input("PIN App (4 cifre)", type="password")
        if st.button("Richiedi Token 2FA"):
            if phone_num and pin_code:
                st.warning("Verifica push inviata all'app Trade Republic. Conferma sul telefono.")
            else:
                st.error("Inserisci numero e PIN.")
    
    st.markdown("---")
    st.subheader("💶 Liquidità Disponibile")
    st.session_state.liquidita = st.number_input("Liquidità non investita (€)", value=st.session_state.liquidita, step=100.0)

# --- Calcolo Valori di Portafoglio ---
tickers_list = [item["Ticker"] for item in st.session_state.portfolio]
market_data = get_live_market_data(tickers_list)

portfolio_rows = []
totale_investito = 0.0
totale_valore_attuale = 0.0

for item in st.session_state.portfolio:
    t = item["Ticker"]
    q = item["Quote"]
    pc = item["Prezzo_Carico"]
    
    live_price = market_data.get(t, {}).get("prezzo")
    current_price = live_price if live_price is not None else pc
    var_day = market_data.get(t, {}).get("variazione", 0.0)
    
    investito = q * pc
    valore_attuale = q * current_price
    pl_euro = valore_attuale - investito
    pl_pct = ((current_price - pc) / pc) * 100 if pc > 0 else 0.0
    
    totale_investito += investito
    totale_valore_attuale += valore_attuale
    
    portfolio_rows.append({
        "Ticker": t,
        "Nome": item["Nome"],
        "Categoria": item["Categoria"],
        "Quote": q,
        "Prezzo Carico (€)": round(pc, 2),
        "Prezzo Attuale (€)": round(current_price, 2),
        "Valore Attuale (€)": round(valore_attuale, 2),
        "P&L Totale (€)": round(pl_euro, 2),
        "P&L Totale (%)": round(pl_pct, 2),
        "Var. 24h (%)": round(var_day, 2)
    })

df_portfolio = pd.DataFrame(portfolio_rows)
patrimonio_totale = totale_valore_attuale + st.session_state.liquidita
pl_complessivo_euro = totale_valore_attuale - totale_investito
pl_complessivo_pct = ((totale_valore_attuale - totale_investito) / totale_investito) * 100 if totale_investito > 0 else 0.0

# --- Dashboard Principale ---
st.title("📈 Portafoglio & AI Investment Assistant")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Patrimonio Totale", f"€ {patrimonio_totale:,.2f}")
col2.metric("Capitale Investito", f"€ {totale_valore_attuale:,.2f}")
col3.metric("P&L Non Realizzato", f"€ {pl_complessivo_euro:+,.2f}", f"{pl_complessivo_pct:+.2f}%")
col4.metric("Liquidità Libera", f"€ {st.session_state.liquidita:,.2f}")

st.markdown("---")

# --- Grafici Interattivi ---
tab_overview, tab_allocation, tab_positions = st.tabs(["📊 Panoramica & Performance", "🥧 Asset Allocation", "📋 Posizioni Aperte"])

with tab_overview:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Performance Benchmark vs Mercato")
        # Grafico storico rapido del principale indice mondiale
        hist_vwce = yf.Ticker("VWCE.DE").history(period="1y")
        if not hist_vwce.empty:
            fig_perf = px.line(hist_vwce, y="Close", title="Andamento Globale (Vanguard All-World 1 Anno)", labels={"Close": "Prezzo (€)", "Date": "Data"})
            fig_perf.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=320)
            st.plotly_chart(fig_perf, use_container_width=True)
    with c2:
        st.subheader("Composizione Patrimonio")
        cash_df = pd.DataFrame({
            "Tipo": ["Investito", "Liquidità"],
            "Valore": [totale_valore_attuale, st.session_state.liquidita]
        })
        fig_cash = px.pie(cash_df, names="Tipo", values="Valore", hole=0.5, color_discrete_sequence=["#2E86AB", "#A23B72"])
        fig_cash.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig_cash, use_container_width=True)

with tab_allocation:
    st.subheader("Ripartizione per Categoria")
    fig_alloc = px.pie(df_portfolio, names="Categoria", values="Valore Attuale (€)", hole=0.4, title="Esposizione per Asset Class")
    st.plotly_chart(fig_alloc, use_container_width=True)

with tab_positions:
    st.subheader("Dettaglio Titoli in Portafoglio")
    st.dataframe(
        df_portfolio.style.format({
            "Prezzo Carico (€)": "€ {:.2f}",
            "Prezzo Attuale (€)": "€ {:.2f}",
            "Valore Attuale (€)": "€ {:.2f}",
            "P&L Totale (€)": "{:+.2f} €",
            "P&L Totale (%)": "{:+.2f}%",
            "Var. 24h (%)": "{:+.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

# --- Assistente AI Gemini ---
st.subheader("🤖 Assistente Finanziario Strategico (Powered by Gemini)")

if not api_key:
    st.warning("⚠️ Inserisci la tua API Key di Gemini nella barra laterale a sinistra per attivare l'assistente strategico.")
else:
    # Configura client Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Contesto di sistema formattato con i dati attuali di portafoglio
    def build_system_context():
        portfolio_summary = df_portfolio[["Ticker", "Nome", "Categoria", "Valore Attuale (€)", "P&L Totale (%)"]].to_string(index=False)
        context = f"""
        Sei un Senior Financial Advisor & Quantitative Analyst. 
        Analizza i dati del portafoglio reale dell'utente e fornisci indicazioni strategiche, ribilanciamento, timing di mercato e gestione del rischio.
        
        DATI DEL PORTAFOGLIO:
        - Liquidità disponibile da investire: € {st.session_state.liquidita:.2f}
        - Valore totale investito: € {totale_valore_attuale:.2f}
        - Patrimonio complessivo: € {patrimonio_totale:.2f}
        - Guadagno/Perdita complessiva: € {pl_complessivo_euro:.2f} ({pl_complessivo_pct:.2f}%)
        
        POSIZIONI ATTUALI:
        {portfolio_summary}

        LINEE GUIDA PER LE RISPOSTE:
        1. Sii chiaro, analitico e fondato sui numeri e sulle percentuali.
        2. Se suggerisci acquisti per il PAC, calcola esattamente quante quote e quale importo in euro allocare.
        3. Identifica sovraesposizioni settoriali o geografiche.
        4. Includi sempre una gestione del rischio e ricorda che le analisi sono a scopo decisionale/informativo.
        """
        return context

    # Bottoni di Azione Rapida
    col_a, col_b, col_c = st.columns(3)
    prompt_to_send = None

    if col_a.button("🔍 Analisi Diversificazione & Rischi"):
        prompt_to_send = "Esegui un'analisi approfondita della diversificazione del mio portafoglio attuale. Quali sono i principali punti di forza, i rischi e le concentrazioni da ridurre?"

    if col_b.button("⚖️ Strategia Ribilanciamento & PAC"):
        prompt_to_send = f"Ho a disposizione € {st.session_state.liquidita:.2f} di liquidità. Come mi suggerisci di allocarla oggi tra i miei asset o su nuovi strumenti per ottimizzare il rapporto rischio/rendimento?"

    if col_c.button("🌐 Opportunità & Valutazione Macro"):
        prompt_to_send = "Considerando l'attuale contesto macroeconomico (tassi d'interesse, inflazione, valutazioni tech), quali sono i fattori chiave da monitorare sui miei titoli in portafoglio?"

    # Input manuale dell'utente
    user_input = st.chat_input("Fai una domanda strategica sul tuo portafoglio...")

    active_prompt = prompt_to_send or user_input

    # Mostra cronologia chat
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Esecuzione della richiesta a Gemini
    if active_prompt:
        st.session_state.chat_history.append({"role": "user", "content": active_prompt})
        with st.chat_message("user"):
            st.markdown(active_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Elaborazione dati e analisi finanziaria in corso..."):
                try:
                    full_prompt = f"{build_system_context()}\n\nRICHIESTA UTENTE:\n{active_prompt}"
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Errore durante la generazione dell'analisi: {str(e)}")
