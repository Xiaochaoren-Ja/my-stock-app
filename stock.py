import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="ProTrade Ultimate", layout="wide", page_icon="⚡")

# --- CSS 样式优化 ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    /* 调整表格字体 */
    div[data-testid="stDataFrame"] { font-size: 14px; }
    /* 指标颜色 */
    div[data-testid="stMetricValue"] { color: #00e5ff; }
</style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏与输入逻辑 ---
with st.sidebar:
    st.title("⚡ ProTrade Ultimate")
    
    # 模式选择
    mode = st.radio("模式选择", ["单股分析", "双股对比 (VS)"])
    
    st.markdown("---")
    
    # --- 股票 1 输入 ---
    st.subheader("股票 A (主代码)")
    market_1 = st.selectbox("市场 A", ["美股 (US)", "A股 (CN)"], key="m1")
    code_1 = st.text_input("代码 A", value="NVDA" if market_1 == "美股 (US)" else "600519", key="c1")
    
    # 股票 1 代码处理
    if "A股" in market_1:
        suffix_1 = ".SS" if st.selectbox("交易所 A", ["上海 (.SS)", "深圳 (.SZ)"], key="s1") == "上海 (.SS)" else ".SZ"
        ticker_1 = code_1 + suffix_1 if code_1 else ""
    else:
        ticker_1 = code_1.upper()

    # --- 股票 2 输入 (仅对比模式) ---
    ticker_2 = None
    if mode == "双股对比 (VS)":
        st.markdown("---")
        st.subheader("股票 B (对比代码)")
        market_2 = st.selectbox("市场 B", ["美股 (US)", "A股 (CN)"], key="m2")
        code_2 = st.text_input("代码 B", value="AMD" if market_2 == "美股 (US)" else "000858", key="c2")
        
        if "A股" in market_2:
            suffix_2 = ".SS" if st.selectbox("交易所 B", ["上海 (.SS)", "深圳 (.SZ)"], key="s2") == "上海 (.SS)" else ".SZ"
            ticker_2 = code_2 + suffix_2 if code_2 else ""
        else:
            ticker_2 = code_2.upper()

    st.markdown("---")
    st.info("提示: 对比模式下将显示累计涨跌幅(%)，方便比较不同价位的股票。")

# --- 辅助函数：获取数据 ---
def get_stock_data(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1y")
    info = stock.info
    return stock, hist, info

# --- 3. 主程序逻辑 ---

# >>>>>> 场景 A: 单股分析模式 <<<<<<
if mode == "单股分析" and ticker_1:
    try:
        stock, hist, info = get_stock_data(ticker_1)
        if hist.empty: st.stop()

        # 标题区
        st.title(f"{info.get('shortName', ticker_1)} ({ticker_1})")
        
        # 核心指标
        curr = info.get('currentPrice', hist['Close'].iloc[-1])
        prev = info.get('previousClose', hist['Close'].iloc[-2])
        delta = curr - prev
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新价", f"{curr:,.2f}", f"{delta:.2f} ({(delta/prev)*100:.2f}%)")
        c2.metric("PE (市盈率)", f"{info.get('trailingPE', 'N/A')}")
        c3.metric("总市值", f"{info.get('marketCap', 0)/1e9:.2f} B")
        c4.metric("52周高", f"{info.get('fiftyTwoWeekHigh', 'N/A')}")
        
        st.markdown("---")
        
        # 图表
        st.subheader("📈 价格走势")
        fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"无法获取数据: {e}")

# >>>>>> 场景 B: 双股对比模式 <<<<<<
elif mode == "双股对比 (VS)" and ticker_1 and ticker_2:
    try:
        st.title(f"⚔️ 巅峰对决: {ticker_1} vs {ticker_2}")
        
        # 获取两只股票数据
        s1, h1, i1 = get_stock_data(ticker_1)
        s2, h2, i2 = get_stock_data(ticker_2)
        
        if h1.empty or h2.empty:
            st.error("其中一只股票数据无效")
            st.stop()

        # 1. 核心指标 PK 表格
        st.subheader("📊 核心数据 PK")
        col_pk1, col_pk2 = st.columns(2)
        
        # 股票 A 数据卡片
        with col_pk1:
            st.info(f"🟢 {i1.get('shortName', ticker_1)}")
            st.metric("市值", f"{i1.get('marketCap',0)/1e9:.1f}B")
            st.metric("市盈率 (PE)", i1.get('trailingPE', 'N/A'))
            st.metric("毛利率", f"{i1.get('grossMargins', 0)*100:.1f}%" if i1.get('grossMargins') else "N/A")

        # 股票 B 数据卡片
        with col_pk2:
            st.success(f"🔵 {i2.get('shortName', ticker_2)}")
            st.metric("市值", f"{i2.get('marketCap',0)/1e9:.1f}B")
            st.metric("市盈率 (PE)", i2.get('trailingPE', 'N/A'))
            st.metric("毛利率", f"{i2.get('grossMargins', 0)*100:.1f}%" if i2.get('grossMargins') else "N/A")

        st.markdown("---")

        # 2. 走势对比图 (使用百分比涨幅，否则价格差太大没法比)
        st.subheader("📈 累计收益率对比 (1年)")
        
        # 计算累计收益率
        h1['Pct Change'] = (h1['Close'] / h1['Close'].iloc[0] - 1) * 100
        h2['Pct Change'] = (h2['Close'] / h2['Close'].iloc[0] - 1) * 100
        
        fig_vs = go.Figure()
        fig_vs.add_trace(go.Scatter(x=h1.index, y=h1['Pct Change'], name=f"{ticker_1} (%)", line=dict(color='green', width=2)))
        fig_vs.add_trace(go.Scatter(x=h2.index, y=h2['Pct Change'], name=f"{ticker_2} (%)", line=dict(color='cyan', width=2)))
        
        fig_vs.update_layout(
            height=500, 
            template="plotly_dark", 
            title="谁的投资回报更高？",
            yaxis_title="累计涨跌幅 (%)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_vs, use_container_width=True)
        
        # 设置 stock 变量供下方财报使用 (默认展示股票1的，或者不做展示)
        stock = s1 # 默认底部财报显示股票1

    except Exception as e:
        st.error(f"对比模式出错: {e}")

else:
    st.info("请在左侧配置股票代码")


# >>>>>> 底部通用功能：完整财报与数据 <<<<<<
st.markdown("---")
st.header("📚 深度财务报表中心")

if 'stock' in locals() and ticker_1:
    # 只有在单股模式或者对比模式获取成功后才显示
    target_stock_obj = stock # 在单股模式是当前股票，对比模式默认是股票1
    target_name = ticker_1
    
    # 如果是对比模式，允许用户切换看谁的财报
    if mode == "双股对比 (VS)":
        target_choice = st.radio("查看哪家公司的财报？", [ticker_1, ticker_2], horizontal=True)
        if target_choice == ticker_2:
            target_stock_obj = s2
    
    # 获取三大表
    bs = target_stock_obj.balance_sheet
    is_ = target_stock_obj.financials
    cf = target_stock_obj.cashflow
    
    tab_f1, tab_f2, tab_f3 = st.tabs(["💰 利润表 (Income)", "🏦 资产负债表 (Balance)", "💵 现金流量表 (Cash Flow)"])
    
    with tab_f1:
        st.markdown("#### 利润表 (Annual Income Statement)")
        if not is_.empty:
            # 颜色渐变 (需要 matplotlib)
            st.dataframe(is_.style.background_gradient(cmap="Blues", axis=1).format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("暂无数据")
            
    with tab_f2:
        st.markdown("#### 资产负债表 (Balance Sheet)")
        if not bs.empty:
            st.dataframe(bs.style.background_gradient(cmap="Greens", axis=1).format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("暂无数据")
            
    with tab_f3:
        st.markdown("#### 现金流量表 (Cash Flow)")
        if not cf.empty:
            st.dataframe(cf.style.background_gradient(cmap="Oranges", axis=1).format("{:,.0f}"), use_container_width=True)
        else:
            st.warning("暂无数据")
            
    st.caption("提示: 表格支持左右滑动，点击表头可全屏查看。数据单位通常为原币种（美元/人民币）。")
