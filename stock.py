import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="Pro Trade Terminal", layout="wide", page_icon="📈")

# --- Sidebar ---
st.sidebar.title("📈 Market Terminal")
ticker = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL")
st.sidebar.markdown("---")
st.sidebar.info("""
**Ticker Examples:**
🇺🇸 US: AAPL, TSLA, NVDA
🇨🇳 CN (Shanghai): 600519.SS
🇨🇳 CN (Shenzhen): 000858.SZ
""")

if st.sidebar.button("Analyze") or ticker:
    try:
        # Fetch Data
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 1. Header & Key Metrics
        st.title(f"{info.get('shortName', ticker)} ({ticker.upper()})")
        
        # Check currency symbol
        currency_symbol = "$" if info.get('currency') == "USD" else "¥"
        
        col1, col2, col3, col4 = st.columns(4)
        
        current_price = info.get('currentPrice', 0)
        previous_close = info.get('previousClose', 0)
        delta = current_price - previous_close
        
        col1.metric("Price", f"{currency_symbol}{current_price:,.2f}", f"{delta:.2f}")
        col2.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
        
        # Format Market Cap
        mkt_cap = info.get('marketCap', 0)
        if mkt_cap > 1e9:
            mkt_val = f"{mkt_cap/1e9:.2f} B"
        else:
            mkt_val = f"{mkt_cap/1e6:.2f} M"
            
        col3.metric("Market Cap", mkt_val)
        col4.metric("52W High", f"{currency_symbol}{info.get('fiftyTwoWeekHigh', 'N/A')}")
        
        st.markdown("---")

        # 2. Interactive Chart
        st.subheader("📊 Price Action (1 Year)")
        hist = stock.history(period="1y")
        
        fig = go.Figure(data=[go.Candlestick(x=hist.index,
                        open=hist['Open'], high=hist['High'],
                        low=hist['Low'], close=hist['Close'])])
        
        fig.update_layout(
            height=500, 
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            title=f"{ticker.upper()} Daily Chart"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 3. Financials & News
        c1, c2 = st.columns([2,1])
        
        with c1:
            st.subheader("💰 Key Financials (Annual)")
            fin = stock.financials
            if not fin.empty:
                # Filter for key rows
                rows = ['Total Revenue', 'Net Income', 'Gross Profit', 'EBITDA']
                available = [r for r in rows if r in fin.index]
                
                if available:
                    df_show = fin.loc[available]
                    st.dataframe(df_show.style.format("{:,.0f}"), use_container_width=True)
                else:
                    st.write(fin.head(5)) 
            else:
                st.warning("No detailed financial data available.")

        with c2:
            st.subheader("📰 Latest News")
            news = stock.news
            if news:
                for n in news[:5]:
                    st.markdown(f"**[{n['title']}]({n['link']})**")
                    st.caption(f"Source: {n['publisher']}")
                    st.markdown("---")
            else:
                st.info("No recent news found.")

    except Exception as e:
        st.error(f"Error fetching data. Please check the ticker symbol.\nDetails: {e}")