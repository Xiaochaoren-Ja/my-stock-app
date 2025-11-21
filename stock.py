import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- 1. 全局配置 & 极光UI系统 ---
st.set_page_config(page_title="宝宝专用 | 顶级投研终端", layout="wide", page_icon="💖")

# --- CSS 深度定制 (磨砂玻璃 + 霓虹) ---
st.markdown("""
<style>
    /* 动态背景：深空极光 */
    .stApp {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        color: #ffffff;
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
        font-size: 28px !important;
    }

    /* 卡片容器 */
    .css-card {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* 页脚样式 */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: rgba(15, 32, 39, 0.95);
        color: #888;
        text-align: center;
        padding: 5px;
        font-size: 12px;
        z-index: 999;
        border-top: 1px solid #333;
    }
    
    /* 让表格更清晰 */
    .stDataFrame { border: 1px solid rgba(255,255,255,0.1); }
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
            
        # 实用小工具：K线周期
        period = st.select_slider("时间跨度", options=["1mo", "6mo", "1y", "3y", "5y"], value="1y")

# --- 3. 主程序逻辑 ---

# >>>>>>>>> 模式 A: 单股深度分析 <<<<<<<<<
if "单股" in mode and final_ticker:
    stock = get_stock_safe(final_ticker)
    
    # 获取数据 (带缓存 spinner)
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
    
    # 核心指标栏
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("当前价格", f"{curr:,.2f}", f"{chg:+.2f} ({pct:+.2f}%)")
    c2.metric("市盈率 (PE)", f"{info.get('trailingPE', 'N/A')}")
    c3.metric("总市值", f"{info.get('marketCap', 0)/1e9:,.2f} B")
    c4.metric("52周最高", f"{info.get('fiftyTwoWeekHigh', 'N/A')}")
    
    st.markdown("---")

    # --- 特色功能区：仪表盘与图表 ---
    col_chart, col_gauge = st.columns([3, 1])
    
    with col_chart:
        st.subheader("📈 价格走势 (Price Action)")
        # K线图 + 均线
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='K线'))
        # 加一条20日均线
        ma20 = hist['Close'].rolling(window=20).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=ma20, mode='lines', name='20日线', line=dict(color='#00d2ff', width=1)))
        
        fig.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_gauge:
        st.subheader("🧭 华尔街态度")
        # 获取分析师建议分数 (1=强买, 5=强卖)
        rec_mean = info.get('targetMeanPrice')
        current_p = curr
        
        # 简单的逻辑：如果目标价 > 现价，就是买入
        if rec_mean:
            upside = ((rec_mean - current_p) / current_p) * 100
            gauge_color = "#00ff00" if upside > 0 else "#ff0000"
            
            fig_g = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = upside,
                title = {'text': "目标涨幅空间 (%)"},
                delta = {'reference': 0},
                gauge = {'axis': {'range': [-50, 100]}, 'bar': {'color': gauge_color}, 'bgcolor': "rgba(0,0,0,0)"}
            ))
            fig_g.update_layout(height=300, margin=dict(l=10,r=10,t=0,b=0), template="plotly_dark")
            st.plotly_chart(fig_g, use_container_width=True)
            st.caption(f"分析师平均目标价: {rec_mean}")
        else:
            st.info("暂无分析师预测数据")

    # --- 实用功能：睡后收入计算器 ---
    with st.expander("🤑 实用工具：分红与睡后收入计算器 (点击展开)", expanded=True):
        st.markdown("#### 假设我持有...")
        c_calc1, c_calc2, c_calc3 = st.columns(3)
        
        shares_to_buy = c_calc1.number_input("我想买多少股?", min_value=100, value=1000, step=100)
        
        # 获取股息率
        div_rate = info.get('dividendRate') # 金额
        div_yield = info.get('dividendYield') # 百分比
        
        if div_rate:
            annual_income = shares_to_buy * div_rate
            c_calc2.metric("每股分红 (年)", f"{div_rate}")
            c_calc3.metric("预计每年躺赚", f"{annual_income:,.2f}", f"收益率 {div_yield*100:.2f}%")
            st.success(f"💰 只要你持有 {shares_to_buy} 股，每年不用动就能拿 **{annual_income:,.2f}** (税前)！")
        else:
            st.warning("⚠️ 这家公司是个铁公鸡（或者处于成长期），目前不发分红。")

    # --- 底部：详情 Tabs ---
    tab1, tab2, tab3 = st.tabs(["💰 深度财报", "📰 智能舆情", "🏦 股东数据"])
    
    with tab1:
        st.markdown("### 利润表 (Income Statement)")
        fin = stock.financials
        if not fin.empty:
            # 放大字体，选取核心行
            key_rows = ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income']
            show_rows = [r for r in key_rows if r in fin.index]
            if show_rows:
                st.dataframe(fin.loc[show_rows].style.background_gradient(cmap="Blues").format("{:,.0f}"), use_container_width=True)
            else:
                st.dataframe(fin, use_container_width=True)
            
            # 资产负债表链接
            with st.expander("查看资产负债表 (Balance Sheet)"):
                st.dataframe(stock.balance_sheet.style.format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("暂无财报数据")

    with tab2:
        col_news_btn, col_news_list = st.columns([1, 3])
        with col_news_btn:
            st.info("觉得新闻不够新？")
            q_name = ticker if "SS" not in ticker else ticker.replace(".SS", " 股票")
            st.link_button("🔍 Google 财经搜索", f"https://www.google.com/search?q={q_name}&tbm=nws")
            st.link_button("🔍 百度资讯搜索", f"https://www.baidu.com/s?wd={q_name} 最新消息")
        
        with col_news_list:
            news = stock.news
            if news:
                for n in news[:4]:
                    title = n.get('title', '无标题')
                    link = n.get('link', '#')
                    pub = n.get('publisher', '未知')
                    time_str = datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%Y-%m-%d')
                    if title:
                        st.markdown(f"**[{title}]({link})**")
                        st.caption(f"📅 {time_str} | 来源: {pub}")
                        st.markdown("---")
            else:
                st.write("暂无直接新闻流，请点击左侧按钮搜索。")

    with tab3:
        st.write("十大股东 / 机构持仓")
        try:
            st.dataframe(stock.institutional_holders, use_container_width=True)
        except:
            st.info("暂无持仓数据")

# >>>>>>>>> 模式 B: 多股对比 <<<<<<<<<
else:
    with st.sidebar:
        st.subheader("配置选手 (输入代码)")
        t1 = st.text_input("选手 1", "NVDA").upper()
        t2 = st.text_input("选手 2", "AMD").upper()
        t3 = st.text_input("选手 3", "INTC").upper()
        t4 = st.text_input("选手 4", "").upper()
        btn = st.button("🚀 开始 PK", type="primary")

    if btn or t1:
        st.title("⚔️ 巅峰对决 (Comparison)")
        tickers = [t.strip() for t in [t1,t2,t3,t4] if t.strip()]
        
        if not tickers: st.stop()
        
        data = {}
        valid = []
        
        with st.spinner("正在计算收益率..."):
            for t in tickers:
                s = get_stock_safe(t)
                h = s.history(period="1y")
                if not h.empty:
                    # 归一化：从 0% 开始跑
                    h['Pct'] = (h['Close'] / h['Close'].iloc[0] - 1) * 100
                    data[t] = h['Pct']
                    valid.append(t)
        
        if valid:
            fig = go.Figure()
            for v in valid:
                fig.add_trace(go.Scatter(x=data[v].index, y=data[v], mode='lines', name=v))
            fig.update_layout(template="plotly_dark", title="近一年累计收益率 (%)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            # 简易基本面PK表
            st.subheader("📊 基本面硬指标")
            infos = []
            for v in valid:
                i = yf.Ticker(v).info
                infos.append({
                    "代码": v,
                    "名称": i.get('shortName'),
                    "最新价": i.get('currentPrice'),
                    "PE (市盈率)": i.get('trailingPE'),
                    "股息率": f"{i.get('dividendYield', 0)*100:.2f}%" if i.get('dividendYield') else "0%"
                })
            st.dataframe(pd.DataFrame(infos).set_index("代码"), use_container_width=True)

# --- 4. 底部 Reference (增加可信度) ---
st.markdown("<br><br><br>", unsafe_allow_html=True) # 占位
st.markdown("""
<div class='footer'>
    <p>🔒 <b>Data Source Reference:</b> All market data provided by <a href='https://finance.yahoo.com/' target='_blank' style='color:#00d2ff'>Yahoo Finance API</a>. 
    News aggregated from global authorized publishers.</p>
    <p>⚠️ <b>Disclaimer:</b> This tool is for informational purposes only and does not constitute financial advice. Trading involves risk.</p>
    <p>© 2025 ProTrade Terminal | Designed for Professional Traders</p>
</div>
""", unsafe_allow_html=True)
