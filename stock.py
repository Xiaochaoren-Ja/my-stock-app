import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. 全局配置 & 页面美化 ---
st.set_page_config(page_title="宝宝专用 | 顶级投研", layout="wide", page_icon="💖")

# --- CSS 深度定制 (大字体 + 优化表格) ---
st.markdown("""
<style>
    /* 全局背景 - 深蓝极光色 */
    .stApp {
        background: linear-gradient(to bottom, #0f0c29, #302b63, #24243e);
        color: white;
    }
    
    /* 表格字体放大，更清晰 */
    div[data-testid="stDataFrame"] div {
        font-size: 16px !important; 
        font-family: 'Arial', sans-serif;
    }
    
    /* 侧边栏半透明 */
    section[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
    }
    
    /* 指标数字 */
    div[data-testid="stMetricValue"] {
        color: #00d2ff; /* 霓虹蓝 */
        font-weight: bold;
    }
    
    /* 按钮美化 */
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
        border: 1px solid #ffffff30;
    }
</style>
""", unsafe_allow_html=True)

# --- 辅助函数 ---
def get_data_safe(ticker):
    """安全获取数据，防止报错"""
    try:
        s = yf.Ticker(ticker)
        h = s.history(period="1y")
        i = s.info
        return s, h, i
    except:
        return None, pd.DataFrame(), {}

def calculate_rsi(df, periods=14):
    """计算RSI指标"""
    if df.empty: return df
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# --- 2. 侧边栏 ---
with st.sidebar:
    st.markdown("## 💖 宝宝专用投研终端")
    st.markdown("---")
    
    # 模式切换
    mode = st.radio("功能模式", ["🔍 单股深度分析", "⚔️ 多股PK (最多4只)"])
    st.markdown("---")
    
    # 只有单股模式才显示时间选择
    if "单股" in mode:
        period_map = {"1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "3年": "3y"}
        time_sel = st.selectbox("K线时间", list(period_map.keys()), index=3)
        time_period = period_map[time_sel]

# --- 3. 主程序逻辑 ---

# ==========================================
# 模式 A: 单股深度分析
# ==========================================
if "单股" in mode:
    # --- 股票选择区 ---
    with st.sidebar:
        st.subheader("输入代码")
        mkt = st.radio("市场", ["美股", "A股"], horizontal=True)
        if mkt == "美股":
            ticker = st.text_input("代码 (如 NVDA)", value="NVDA").upper()
        else:
            code = st.text_input("代码 (如 600519)", value="600519")
            ex = st.selectbox("交易所", [".SS (上海)", ".SZ (深圳)"])
            ticker = code + ex.split(" ")[0] if code else ""

    if ticker:
        stock, hist, info = get_data_safe(ticker)
        
        if hist.empty:
            st.error(f"⚠️ 找不到代码 {ticker}，请检查拼写或网络。")
            st.stop()
            
        hist = calculate_rsi(hist)

        # --- 1. 核心行情 (Top) ---
        st.title(f"{info.get('shortName', ticker)} ({ticker})")
        
        # 价格与指标
        curr = info.get('currentPrice') or hist['Close'].iloc[-1]
        prev = info.get('previousClose') or hist['Close'].iloc[-2]
        chg = curr - prev
        pct = (chg/prev)*100
        
        # RSI 状态
        rsi_val = hist['RSI'].iloc[-1]
        rsi_state = "超买 (高风险)" if rsi_val > 70 else "超卖 (机会?)" if rsi_val < 30 else "正常"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("当前价格", f"{curr:,.2f}", f"{chg:+.2f} ({pct:+.2f}%)")
        c2.metric("RSI 指标", f"{rsi_val:.1f}", rsi_state)
        c3.metric("市盈率 (PE)", f"{info.get('trailingPE', 'N/A')}")
        c4.metric("总市值", f"{info.get('marketCap', 0)/1e9:,.2f} B")

        st.markdown("---")

        # --- 2. K线图 (Middle) ---
        st.subheader("📈 价格走势")
        fig = go.Figure(data=[go.Candlestick(x=hist.index,
                        open=hist['Open'], high=hist['High'],
                        low=hist['Low'], close=hist['Close'], name='K线')])
        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- 3. 底部功能区 (Tabs) ---
        st.markdown("<br>", unsafe_allow_html=True)
        tab_fin, tab_holder, tab_news = st.tabs(["💰 财务透视 (大表)", "🏦 股东与分红", "📰 智能舆情"])

        # >>> Tab 1: 财务透视 (已放大) <<<
        with tab_fin:
            st.markdown("### 📊 核心财务报表")
            fin = stock.financials
            bs = stock.balance_sheet
            cf = stock.cashflow
            
            # 财务概览 (User 要求放在显眼位置)
            if not fin.empty:
                st.info("💡 提示：这里展示的是年度合并报表，单位为原币种。")
                
                # 利润表
                st.markdown("#### 1. 利润表 (Income Statement)")
                # 选取最重要的几行
                key_rows = ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income', 'EBITDA']
                existing_rows = [r for r in key_rows if r in fin.index]
                # 如果有数据，显示
                if existing_rows:
                     st.dataframe(fin.loc[existing_rows].style.background_gradient(cmap="Blues").format("{:,.0f}"), use_container_width=True)
                else:
                    st.dataframe(fin.head(10), use_container_width=True)

                st.markdown("---")
                
                # 资产负债表一角
                st.markdown("#### 2. 资产状况 (Balance Sheet Snapshot)")
                bs_rows = ['Total Assets', 'Total Liab', 'Total Stockholder Equity', 'Cash And Cash Equivalents']
                existing_bs = [r for r in bs_rows if r in bs.index]
                if existing_bs:
                    st.dataframe(bs.loc[existing_bs].style.format("{:,.0f}"), use_container_width=True)
            else:
                st.warning("暂无详细财务数据")

        # >>> Tab 2: 股东与分红 <<<
        with tab_holder:
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                st.subheader("👥 机构/大股东持仓")
                try:
                    # 尝试获取大股东数据
                    holders = stock.major_holders
                    inst = stock.institutional_holders
                    if inst is not None and not inst.empty:
                        st.dataframe(inst, use_container_width=True)
                    elif holders is not None:
                        st.dataframe(holders, use_container_width=True)
                    else:
                        st.info("暂无持仓数据")
                except:
                    st.info("数据源暂未提供持仓信息")

            with c_h2:
                st.subheader("📅 分红与拆股")
                divs = stock.dividends
                if not divs.empty:
                    st.bar_chart(divs.tail(10)) # 显示最近10次分红
                    st.caption("最近10次分红记录")
                else:
                    st.info("近期无分红记录")

        # >>> Tab 3: 智能舆情 (修复版) <<<
        with tab_news:
            st.subheader("📰 市场消息")
            
            # 1. 尝试获取 yfinance 新闻
            news_list = stock.news
            has_valid_news = False
            
            if news_list:
                for n in news_list[:5]:
                    # 严格清洗数据
                    title = n.get('title')
                    link = n.get('link')
                    pub = n.get('publisher')
                    # 过滤掉无标题或无链接的坏数据
                    if title and link and title != "":
                        has_valid_news = True
                        with st.container():
                            st.markdown(f"**🔗 [{title}]({link})**")
                            st.caption(f"来源: {pub}")
                            st.markdown("---")
            
            # 2. 如果没有有效新闻，提供备选方案
            if not has_valid_news:
                st.warning("⚠️ 数据源暂无最新新闻，或者数据格式异常。")
            
            # 3. 永远显示的“备用搜索按钮” (最实用)
            st.markdown("#### 🌐 全网搜索该股票")
            col_s1, col_s2 = st.columns(2)
            # 生成 Google 和 必应 的搜索链接
            q_ticker = ticker.replace(".SS", " stock").replace(".SZ", " stock")
            if "SS" in ticker or "SZ" in ticker:
                search_q = f"{ticker} 股票新闻"
            else:
                search_q = f"{ticker} stock news"
                
            with col_s1:
                st.link_button("🔍 去 Google 财经搜索", f"https://www.google.com/search?q={search_q}&tbm=nws")
            with col_s2:
                st.link_button("🔍 去 百度/必应 搜索", f"https://www.bing.com/news/search?q={search_q}")

    # --- 第一页最底部的财务速览 (User Request) ---
    if ticker and not hist.empty:
        st.markdown("---")
        st.markdown("### ⚡ 财务速览 (Quick Look)")
        st.caption("最近一期核心数据概览")
        # 再次调用 info 里的快速数据
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("总营收", f"{info.get('totalRevenue', 0)/1e9:,.2f} B")
        f2.metric("毛利润", f"{info.get('grossProfits', 0)/1e9:,.2f} B")
        f3.metric("总现金", f"{info.get('totalCash', 0)/1e9:,.2f} B")
        f4.metric("总债务", f"{info.get('totalDebt', 0)/1e9:,.2f} B")


# ==========================================
# 模式 B: 多股 PK (3-4股对比)
# ==========================================
else:
    with st.sidebar:
        st.subheader("配置比赛选手")
        st.caption("请填入代码 (美股直接填，A股加 .SS 或 .SZ)")
        
        # 固定 4 个输入框
        t1 = st.text_input("选手 1", value="NVDA").strip().upper()
        t2 = st.text_input("选手 2", value="AMD").strip().upper()
        t3 = st.text_input("选手 3 (选填)", value="INTC").strip().upper()
        t4 = st.text_input("选手 4 (选填)", value="").strip().upper()
        
        start_pk = st.button("🚀 开始 PK", type="primary")

    if start_pk or t1:
        st.title("⚔️ 股票擂台赛")
        
        # 收集所有非空代码
        candidates = [c for c in [t1, t2, t3, t4] if c]
        
        if not candidates:
            st.info("请在左侧至少输入两只股票代码。")
            st.stop()

        data_box = {}
        valid_candidates = []

        with st.spinner("裁判正在入场 (加载数据)..."):
            for c in candidates:
                s = yf.Ticker(c)
                h = s.history(period="1y")
                if not h.empty:
                    # 计算累计收益率 %
                    h['Pct'] = (h['Close'] / h['Close'].iloc[0] - 1) * 100
                    data_box[c] = h['Pct']
                    valid_candidates.append(c)
        
        if valid_candidates:
            # 1. 赛跑图
            st.subheader("📈 累计收益率对比 (1年)")
            fig = go.Figure()
            for vc in valid_candidates:
                fig.add_trace(go.Scatter(x=data_box[vc].index, y=data_box[vc], mode='lines', name=vc))
            
            fig.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="累计涨跌 (%)")
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. 核心数据横向对比表
            st.subheader("📊 基本面硬碰硬")
            
            # 构建对比数据
            comp_data = []
            for vc in valid_candidates:
                inf = yf.Ticker(vc).info
                comp_data.append({
                    "代码": vc,
                    "名称": inf.get('shortName', vc),
                    "最新价": inf.get('currentPrice', 'N/A'),
                    "市盈率 (PE)": inf.get('trailingPE', 'N/A'),
                    "市值 (Billions)": f"{inf.get('marketCap', 0)/1e9:.2f} B",
                    "52周最高": inf.get('fiftyTwoWeekHigh', 'N/A'),
                    "机构评级": inf.get('recommendationKey', 'N/A').upper()
                })
            
            df_comp = pd.DataFrame(comp_data)
            st.dataframe(df_comp, use_container_width=True)
            
        else:
            st.error("输入的代码似乎都无法获取数据，请检查拼写 (A股记得加后缀)。")
