import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. 全局配置 & 页面美化 ---
st.set_page_config(page_title="宝宝专用 | 顶级投研", layout="wide", page_icon="💖")

# --- CSS 深度定制 (毛玻璃 + 霓虹风格) ---
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background: linear-gradient(to bottom right, #0f2027, #203a43, #2c5364);
        color: white;
    }
    
    /* 侧边栏美化 */
    section[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* 卡片容器样式 (Glassmorphism) */
    .css-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* 指标数字颜色 */
    div[data-testid="stMetricValue"] {
        color: #00d2ff; /* 霓虹蓝 */
        text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
    }
    
    /* 按钮样式 */
    .stButton>button {
        background: linear-gradient(45deg, #FF512F, #DD2476);
        color: white;
        border-radius: 20px;
        border: none;
        padding: 10px 25px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 辅助计算函数 (RSI & 布林带) ---
def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
    df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
    return df

# --- 2. 侧边栏逻辑 ---
with st.sidebar:
    st.markdown("## 💖 宝宝专用投研终端")
    st.caption("Made with love for professional trading")
    st.markdown("---")
    
    # 模式切换
    mode = st.radio("功能模式", ["单股分析", "多股对比 (VS)"], index=0)
    
    st.markdown("---")
    
    if mode == "单股分析":
        st.subheader("🔍 股票检索")
        market_type = st.radio("市场", ["🇺🇸 美股", "🇨🇳 A股"], horizontal=True)
        
        if market_type == "🇺🇸 美股":
            symbol_input = st.text_input("美股代码 (如 NVDA)", value="NVDA").upper()
            final_ticker = symbol_input
        else:
            code_input = st.text_input("A股代码 (如 600519)", value="600519")
            exchange = st.selectbox("交易所", [".SS (上海)", ".SZ (深圳)"])
            suffix = exchange.split(" ")[0]
            final_ticker = code_input + suffix if code_input else ""
            
    else: # 多股对比模式
        st.subheader("⚔️ 多股大乱斗")
        st.info("输入多个代码，用英文逗号分隔")
        st.markdown("**示例:** `AAPL, MSFT, 600519.SS`")
        multi_tickers = st.text_area("输入股票池", value="AAPL, TSLA, NVDA, AMD").upper()
        
    st.markdown("---")
    st.markdown("### 🛠 工具箱")
    time_period = st.select_slider("时间范围", options=["1mo", "3mo", "6mo", "1y", "3y"], value="1y")

# --- 3. 主页面逻辑 ---

# >>>>>>>>> 模式 A: 单股深度分析 (实用功能增强版) <<<<<<<<<
if mode == "单股分析" and final_ticker:
    try:
        with st.spinner(f"正在分析 {final_ticker} ..."):
            stock = yf.Ticker(final_ticker)
            hist = stock.history(period=time_period)
            info = stock.info
            
            if hist.empty:
                st.error("无法获取数据，请检查代码。")
                st.stop()
                
            # 计算技术指标
            hist = calculate_indicators(hist)

        # 1. 头部核心卡片
        st.markdown(f"## {info.get('shortName', final_ticker)} <span style='font-size:16px;color:#aaa'>{final_ticker}</span>", unsafe_allow_html=True)
        
        # 实时价格计算
        curr_price = info.get('currentPrice') or hist['Close'].iloc[-1]
        prev_close = info.get('previousClose') or hist['Close'].iloc[-2]
        change = curr_price - prev_close
        pct_change = (change / prev_close) * 100
        
        # 支撑压力位 (基于过去20天)
        recent_high = hist['High'].tail(20).max()
        recent_low = hist['Low'].tail(20).min()

        # 展示 4 个核心数据
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("当前价格", f"{curr_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
        c2.metric("RSI (强弱指标)", f"{hist['RSI'].iloc[-1]:.1f}", delta=None, help=">70超买(风险)，<30超卖(机会)")
        c3.metric("短期压力位", f"{recent_high:,.2f}", help="过去20天最高价")
        c4.metric("短期支撑位", f"{recent_low:,.2f}", help="过去20天最低价")

        st.markdown("---")

        # 2. 专业图表区 (Tabs)
        tab_main, tab_fin, tab_news = st.tabs(["📈 操盘大屏", "💰 财务透视", "📰 消息面"])

        with tab_main:
            # 高级 K 线图 (含布林带 + 成交量)
            fig = go.Figure()
            
            # 蜡烛图
            fig.add_trace(go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name='K线'))
            
            # 布林带
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Upper'], line=dict(color='rgba(255, 255, 255, 0.3)', width=1), name='布林上轨', hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Lower'], line=dict(color='rgba(255, 255, 255, 0.3)', width=1), name='布林下轨', fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)', hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA20'], line=dict(color='#ff9f43', width=1.5), name='中轨 (20日线)'))

            fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, title="价格走势 + 布林通道")
            st.plotly_chart(fig, use_container_width=True)
            
            # 辅助信号提示
            col_tip1, col_tip2 = st.columns(2)
            with col_tip1:
                st.info(f"📊 **波动区间**: 本周期最低 {hist['Low'].min():.2f} - 最高 {hist['High'].max():.2f}")
            with col_tip2:
                # RSI 简单解读
                last_rsi = hist['RSI'].iloc[-1]
                if last_rsi > 70:
                    st.warning("⚠️ **RSI 警示**: 指标超买 (>70)，注意回调风险！")
                elif last_rsi < 30:
                    st.success("✅ **RSI 提示**: 指标超卖 (<30)，存在反弹可能。")
                else:
                    st.info(f"ℹ️ **RSI 状态**: 中性区间 ({last_rsi:.1f})，趋势跟随。")

            # 数据下载
            st.download_button("📥 下载该股票历史数据 (CSV)", hist.to_csv(), file_name=f"{final_ticker}_data.csv", mime='text/csv')

        with tab_fin:
            # 简化版财务
            st.subheader("核心财务指标")
            fin = stock.financials
            if not fin.empty:
                st.dataframe(fin.style.background_gradient(cmap="Blues"), use_container_width=True)
            else:
                st.warning("暂无详细财务数据")
                
        with tab_news:
            st.subheader("最新舆情")
            for n in stock.news[:5]:
                st.markdown(f"**[{n.get('title', '无标题')}]({n.get('link')})**")
                st.caption(f"来源: {n.get('publisher')} | {datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M')}")
                st.markdown("---")

    except Exception as e:
        st.error(f"发生错误: {e}")

# >>>>>>>>> 模式 B: 多股对比 (VS) - 收益率赛跑 <<<<<<<<<
elif mode == "多股对比 (VS)" and multi_tickers:
    try:
        # 清洗输入的代码
        tickers_list = [t.strip() for t in multi_tickers.split(",") if t.strip()]
        
        if len(tickers_list) > 0:
            st.subheader("🏎️ 收益率赛跑 (标准化对比)")
            
            # 拉取数据
            data_dict = {}
            valid_tickers = []
            
            with st.spinner("正在把所有股票拉上跑道..."):
                for t in tickers_list:
                    s = yf.Ticker(t)
                    h = s.history(period=time_period)
                    if not h.empty:
                        # 计算累计涨幅 %
                        h['Pct'] = (h['Close'] / h['Close'].iloc[0] - 1) * 100
                        data_dict[t] = h['Pct']
                        valid_tickers.append(t)
            
            if data_dict:
                # 绘图
                fig_race = go.Figure()
                for vt in valid_tickers:
                    # 随机颜色或不同颜色
                    fig_race.add_trace(go.Scatter(x=data_dict[vt].index, y=data_dict[vt], mode='lines', name=vt))
                
                fig_race.update_layout(
                    height=600, 
                    template="plotly_dark", 
                    yaxis_title="累计涨跌幅 (%)",
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, xanchor="left")
                )
                st.plotly_chart(fig_race, use_container_width=True)
                
                # 最终排位表
                st.markdown("### 🏆 当前排名 (累计涨跌)")
                final_res = []
                for vt in valid_tickers:
                    final_val = data_dict[vt].iloc[-1]
                    final_res.append({"代码": vt, "累计涨跌幅": final_val})
                
                df_res = pd.DataFrame(final_res).sort_values("累计涨跌幅", ascending=False)
                
                # 美化表格显示
                st.dataframe(
                    df_res.style.format({"累计涨跌幅": "{:.2f}%"})
                    .background_gradient(cmap="RdYlGn", subset=["累计涨跌幅"]),
                    use_container_width=True
                )
                
            else:
                st.warning("输入的代码均无效，请检查。如果是A股记得加 .SS 或 .SZ")
                
    except Exception as e:
        st.error(f"对比出错: {e}")

else:
    # 欢迎页
    st.balloons()
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <h1>👋 欢迎使用宝宝专用投研终端</h1>
        <p>请在左侧侧边栏选择模式并输入代码</p>
    </div>
    """, unsafe_allow_html=True)
