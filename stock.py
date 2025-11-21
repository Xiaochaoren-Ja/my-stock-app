import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- 1. 全局配置 & 极光UI系统 ---
st.set_page_config(page_title="宝宝专用 | 顶级投研终端", layout="wide", page_icon="💖")

# --- CSS 深度定制 ---
st.markdown("""
<style>
    /* 动态背景：深空极光 */
    .stApp {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        color: #ffffff;
        padding-bottom: 80px; /* 给底部页脚留出空间 */
    }
    
    /* 侧边栏毛玻璃 */
    section[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* 关键指标数字美化 */
    div[data-testid="stMetricValue"] {
        background: -webkit-linear-gradient(#00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 26px !important;
    }

    /* 按钮样式 */
    .stButton>button {
        border-radius: 20px;
        background: linear-gradient(to right, #00c6ff, #0072ff);
        color: white;
        border: none;
    }

    /* 固定页脚样式 (Fixed Footer) */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: rgba(15, 32, 39, 0.95);
        color: #a0a0a0;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        z-index: 9999;
        border-top: 1px solid #333;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
    }
    .footer a { color: #00d2ff; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- 辅助函数 ---
def get_stock_safe(ticker):
    try:
        return yf.Ticker(ticker)
    except:
        return None

# --- 2. 侧边栏逻辑 ---
with st.sidebar:
    st.markdown("## 💖 宝宝专用投研")
    st.caption("Professional Intelligence Terminal")
    st.markdown("---")
    
    mode = st.radio("功能模式", ["🔍 单股深度分析", "⚔️ 多股PK (VS)"])
    
    st.markdown("---")
    
    # 初始化 final_ticker 变量，防止 NameError
    final_ticker = None 
    
    if "单股" in mode:
        st.subheader("📌 标的选择")
        market = st.selectbox("市场", ["🇺🇸 美股 (US)", "🇨🇳 A股 (CN)"])
        
        if "美股" in market:
            symbol = st.text_input("代码", value="NVDA", help="例如 AAPL, TSLA").upper()
            final_ticker = symbol
        else:
            symbol = st.text_input("代码", value="600519", help="例如 600519")
            ex = st.selectbox("交易所", [".SS (上海)", ".SZ (深圳)"])
            final_ticker = symbol + ex.split(" ")[0] if symbol else ""
            
        period = st.select_slider("时间跨度", options=["1mo", "3mo", "6mo", "1y", "3y", "5y"], value="1y")

# --- 3. 主程序逻辑 ---

# >>>>>>>>> 模式 A: 单股深度分析 <<<<<<<<<
if "单股" in mode and final_ticker:
    stock = get_stock_safe(final_ticker)
    
    # 获取数据
    with st.spinner(f"正在连接交易所拉取 {final_ticker} 数据..."):
        try:
            hist = stock.history(period=period)
            info = stock.info
            if hist.empty: raise ValueError("Empty Data")
        except:
            st.error(f"⚠️ 无法获取数据，请检查代码 {final_ticker} 是否正确。")
            st.stop()

    # --- 顶部：核心行情 ---
    st.markdown(f"## {info.get('shortName', final_ticker)} <span style='font-size:0.6em;color:#aaa'>({final_ticker})</span>", unsafe_allow_html=True)
    
    curr = info.get('currentPrice') or hist['Close'].iloc[-1]
    prev = info.get('previousClose') or hist['Close'].iloc[-2]
    chg = curr - prev
    pct = (chg/prev)*100
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("当前价格", f"{curr:,.2f}", f"{chg:+.2f} ({pct:+.2f}%)")
    c2.metric("市盈率 (PE)", f"{info.get('trailingPE', 'N/A')}")
    c3.metric("总市值", f"{info.get('marketCap', 0)/1e9:,.2f} B")
    c4.metric("52周最高", f"{info.get('fiftyTwoWeekHigh', 'N/A')}")
    
    st.markdown("---")

    # --- 超级图表区 (Interactive Chart) ---
    col_chart, col_gauge = st.columns([3, 1])
    
    with col_chart:
        st.subheader("📈 价格走势 (Price Action)")
        
        # >>> 图表控制台 <<<
        indicators = st.multiselect(
            "🛠️ 添加技术指标 (可多选)",
            ["MA 20 (月线)", "MA 50 (季线)", "布林带 (Bollinger)", "唐奇安通道 (Donchian)", "EMA 20 (趋势)"],
            default=["MA 20 (月线)", "布林带 (Bollinger)"]
        )
        
        # 绘图逻辑
        fig = go.Figure()
        
        # 1. 基础K线
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='K线'))

        # 2. 动态添加指标
        if "MA 20 (月线)" in indicators:
            ma20 = hist['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma20, mode='lines', name='MA 20', line=dict(color='#00d2ff', width=1.5)))
            
        if "MA 50 (季线)" in indicators:
            ma50 = hist['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma50, mode='lines', name='MA 50', line=dict(color='#ff9f43', width=1.5)))

        if "EMA 20 (趋势)" in indicators:
            ema20 = hist['Close'].ewm(span=20, adjust=False).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ema20, mode='lines', name='EMA 20', line=dict(color='#e056fd', width=1.5, dash='dot')))

        if "布林带 (Bollinger)" in indicators:
            sma = hist['Close'].rolling(window=20).mean()
            std = hist['Close'].rolling(window=20).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            fig.add_trace(go.Scatter(x=hist.index, y=upper, mode='lines', line=dict(width=0), name='布林上轨', showlegend=False, hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=hist.index, y=lower, mode='lines', line=dict(width=0), name='布林下轨', fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)', showlegend=False, hoverinfo='skip'))

        if "唐奇安通道 (Donchian)" in indicators:
            high_20 = hist['High'].rolling(window=20).max()
            low_20 = hist['Low'].rolling(window=20).min()
            fig.add_trace(go.Scatter(x=hist.index, y=high_20, mode='lines', name='唐奇安上轨', line=dict(color='rgba(0, 255, 0, 0.5)', width=1, dash='dash')))
            fig.add_trace(go.Scatter(x=hist.index, y=low_20, mode='lines', name='唐奇安下轨', line=dict(color='rgba(255, 0, 0, 0.5)', width=1, dash='dash')))

        fig.update_layout(height=500, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_gauge:
        st.subheader("🧭 华尔街态度")
        rec_mean = info.get('targetMeanPrice')
        current_p = curr
        if rec_mean:
            upside = ((rec_mean - current_p) / current_p) * 100
            gauge_color = "#00ff00" if upside > 0 else "#ff0000"
            fig_g = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = upside,
                title = {'text': "目标空间 (%)"},
                delta = {'reference': 0},
                gauge = {'axis': {'range': [-30, 80]}, 'bar': {'color': gauge_color}, 'bgcolor': "rgba(0,0,0,0)"}
            ))
            fig_g.update_layout(height=350, margin=dict(l=10,r=10,t=0,b=0), template="plotly_dark")
            st.plotly_chart(fig_g, use_container_width=True)
            st.caption(f"分析师目标价: {rec_mean}")
        else:
            st.info("暂无预测数据")

    # --- 实用功能：睡后收入计算器 ---
    with st.expander("🤑 分红计算器 (点击展开)", expanded=False):
        c_calc1, c_calc2, c_calc3 = st.columns(3)
        shares_to_buy = c_calc1.number_input("持股数量", min_value=100, value=1000, step=100)
        div_rate = info.get('dividendRate', 0)
        if div_rate:
            annual_income = shares_to_buy * div_rate
            c_calc2.metric("每股分红", f"{div_rate}")
            c_calc3.metric("预计年收入", f"{annual_income:,.2f}")
            st.success(f"💰 持有 {shares_to_buy} 股，预计每年躺赚 **{annual_income:,.2f}**！")
        else:
            st.warning("该公司暂无分红记录。")

    # --- 底部 Tabs ---
    tab1, tab2, tab3 = st.tabs(["💰 深度财报", "📰 智能舆情", "🏦 股东数据"])
    
    with tab1:
        st.markdown("### 利润表 (Income Statement)")
        fin = stock.financials
        if not fin.empty:
            key_rows = ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income']
            show_rows = [r for r in key_rows if r in fin.index]
            if show_rows:
                st.dataframe(fin.loc[show_rows].style.background_gradient(cmap="Blues").format("{:,.0f}"), use_container_width=True)
            else:
                st.dataframe(fin, use_container_width=True)
            with st.expander("查看资产负债表 (Balance Sheet)"):
                st.dataframe(stock.balance_sheet.style.format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("暂无财报数据")

    with tab2:
        # 修复：这里必须使用 final_ticker，而不是 ticker
        # 同时也增加了 robust 的错误处理
        q_name = final_ticker if "SS" not in final_ticker else final_ticker.replace(".SS", " 股票")
        q_name = q_name.replace(".SZ", " 股票")

        col_btn, col_list = st.columns([1, 3])
        with col_btn:
            st.info("🔗 外部信源直达")
            st.link_button("🔍 Google 财经", f"https://www.google.com/search?q={q_name}&tbm=nws")
            st.link_button("🔍 百度资讯", f"https://www.baidu.com/s?wd={q_name} 最新消息")
        
        with col_list:
            news = stock.news
            if news:
                for n in news[:5]:
                    title = n.get('title', '无标题')
                    link = n.get('link', '#')
                    pub = n.get('publisher', '未知来源')
                    # 只有当标题有效时才显示
                    if title and title != "无标题":
                        st.markdown(f"**[{title}]({link})**")
                        st.caption(f"来源: {pub}")
                        st.markdown("---")
            else:
                st.write("暂无直接新闻流，请使用左侧按钮搜索。")

    with tab3:
        st.write("十大股东 / 机构持仓")
        try:
            st.dataframe(stock.institutional_holders, use_container_width=True)
        except:
            st.info("暂无持仓数据")

# >>>>>>>>> 模式 B: 多股对比 <<<<<<<<<
else:
    with st.sidebar:
        st.subheader("配置选手")
        t1 = st.text_input("选手 1", "NVDA").upper()
        t2 = st.text_input("选手 2", "AMD").upper()
        t3 = st.text_input("选手 3", "").upper()
        t4 = st.text_input("选手 4", "").upper()

    if t1:
        st.title("⚔️ 巅峰对决")
        tickers = [t.strip() for t in [t1,t2,t3,t4] if t.strip()]
        data = {}
        valid = []
        
        with st.spinner("正在计算收益率..."):
            for t in tickers:
                s = get_stock_safe(t)
                if s:
                    h = s.history(period="1y")
                    if not h.empty:
                        h['Pct'] = (h['Close'] / h['Close'].iloc[0] - 1) * 100
                        data[t] = h['Pct']
                        valid.append(t)
        
        if valid:
            fig = go.Figure()
            for v in valid:
                fig.add_trace(go.Scatter(x=data[v].index, y=data[v], mode='lines', name=v))
            fig.update_layout(template="plotly_dark", title="近一年累计收益率 (%)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

# --- 4. 固定页脚 (Reference) ---
# 这是一个 HTML/CSS 注入，确保永远在最底部
st.markdown("""
<div class='footer'>
    <p>🔒 <b>Data Source Reference:</b> Market data provided by <a href='https://finance.yahoo.com/' target='_blank'>Yahoo Finance API</a>. 
    Calculations powered by Pandas/Streamlit.</p>
    <p>⚠️ <b>Disclaimer:</b> This tool is for informational purposes only. "Passive Income" estimates are based on historical dividends.</p>
    <p>© 2025 ProTrade Terminal | Designed for Professional Traders</p>
</div>
""", unsafe_allow_html=True)
