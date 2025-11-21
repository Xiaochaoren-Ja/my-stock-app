import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- 1. 页面高级配置 ---
st.set_page_config(
    page_title="ProTrade Alpha | 极速投研终端", 
    layout="wide", 
    page_icon="🚀",
    initial_sidebar_state="expanded"
)

# --- CSS 美化 (黑金风格 & 卡片设计) ---
st.markdown("""
<style>
    /* 全局字体与背景优化 */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* 指标卡片样式 */
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 700;
        color: #00e5ff; /* 科技蓝 */
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        color: #a0a0a0;
    }
    
    /* 侧边栏美化 */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
    }
    
    /* 选项卡样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1f2937;
        border-radius: 5px;
        color: white;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important; /* 选中变蓝 */
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 智能侧边栏 (分市场输入) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/bullish.png", width=80) # 加上一个牛市Logo
    st.title("🚀 ProTrade Alpha")
    st.caption("专业交易员的实时终端")
    st.markdown("---")
    
    # 市场选择器
    market_type = st.radio("🌎 选择市场 / Market", ["🇺🇸 美股 (US Market)", "🇨🇳 A股 (China Market)"])
    
    if "美股" in market_type:
        ticker_input = st.text_input("输入美股代码 (如 AAPL)", value="NVDA").upper().strip()
        final_ticker = ticker_input
    else:
        # A股智能处理
        a_share_code = st.text_input("输入A股代码 (如 600519)", value="600519").strip()
        market_suffix = st.selectbox("选择交易所", ["上海 (.SS)", "深圳 (.SZ)"], index=0)
        suffix = ".SS" if "上海" in market_suffix else ".SZ"
        # 自动拼接
        if a_share_code:
            final_ticker = a_share_code + suffix
        else:
            final_ticker = ""

    st.markdown("### ⚙️ 分析设置")
    period = st.select_slider("K线范围", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
    
    st.markdown("### 📈 技术指标开关")
    col_ind1, col_ind2 = st.columns(2)
    with col_ind1:
        show_ma = st.checkbox("均线 (MA)", value=True)
        show_vol = st.checkbox("成交量", value=True)
    with col_ind2:
        show_macd = st.checkbox("MACD", value=True)
        show_kdj = st.checkbox("KDJ (Beta)", value=False) # 预留功能

    st.markdown("---")
    if st.button("🔄 刷新数据", type="primary"):
        st.rerun()

# --- 3. 核心逻辑 ---
if final_ticker:
    try:
        # 使用 spinner 提升加载体验
        with st.spinner(f'正在从华尔街/沪深交易所拉取 {final_ticker} 数据...'):
            stock = yf.Ticker(final_ticker)
            # 获取历史数据
            hist = stock.history(period=period)
            # 获取基本信息
            info = stock.info
            
            if hist.empty:
                st.error(f"⚠️ 未找到代码 {final_ticker} 的数据，请检查代码或交易所后缀。")
                st.stop()

        # --- 第一部分：行情看板 (Dashboard) ---
        st.markdown(f"## {info.get('shortName', final_ticker)} <span style='color:#888; font-size:0.6em'>{final_ticker}</span>", unsafe_allow_html=True)
        
        # 提取数据（加入容错处理）
        current_price = info.get('currentPrice') or hist['Close'].iloc[-1]
        prev_close = info.get('previousClose') or hist['Close'].iloc[-2]
        delta = current_price - prev_close
        delta_pct = (delta / prev_close) * 100
        
        # 货币符号
        currency = "¥" if "CNY" in info.get('currency', '') else "$"
        
        # 5个核心指标卡片
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("最新价", f"{currency}{current_price:,.2f}", f"{delta:+.2f} ({delta_pct:+.2f}%)")
        col2.metric("市盈率 (PE)", f"{info.get('trailingPE', 'N/A')}")
        
        mkt_cap = info.get('marketCap', 0)
        col3.metric("总市值", f"{mkt_cap/1e8:,.2f} 亿") # 统一用亿
        
        col4.metric("52周最高", f"{currency}{info.get('fiftyTwoWeekHigh', 'N/A')}")
        
        # 换手率计算 (Volume / Shares Outstanding) - 估算
        shares = info.get('sharesOutstanding', 1)
        vol_today = hist['Volume'].iloc[-1] if not hist.empty else 0
        turnover = (vol_today / shares) * 100 if shares else 0
        col5.metric("今日换手率", f"{turnover:.2f}%")
        
        st.markdown("---")

        # --- 第二部分：多维度分析 Tab ---
        tab_chart, tab_fin, tab_news, tab_ai = st.tabs(["📊 专业图表", "💰 财务透视", "📰 舆情新闻", "🤖 智能分析"])

        # === TAB 1: 专业 K 线图 (含 MACD) ===
        with tab_chart:
            # 主图 (K线 + MA)
            fig = go.Figure()
            
            # 蜡烛图
            fig.add_trace(go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name='Price'))
            
            # 均线
            if show_ma:
                ma5 = hist['Close'].rolling(window=5).mean()
                ma20 = hist['Close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(x=hist.index, y=ma5, line=dict(color='orange', width=1.5), name='MA 5'))
                fig.add_trace(go.Scatter(x=hist.index, y=ma20, line=dict(color='#00e5ff', width=1.5), name='MA 20'))

            # 布局优化
            fig.update_layout(
                height=550,
                xaxis_rangeslider_visible=False,
                template="plotly_dark", # 使用深色主题
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0),
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)

            # MACD 子图
            if show_macd:
                st.caption("MACD 指标 (12, 26, 9)")
                # 计算 MACD
                exp12 = hist['Close'].ewm(span=12, adjust=False).mean()
                exp26 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd = exp12 - exp26
                signal = macd.ewm(span=9, adjust=False).mean()
                hist_macd = macd - signal

                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(x=hist.index, y=macd, line=dict(color='white', width=1), name='MACD'))
                fig_macd.add_trace(go.Scatter(x=hist.index, y=signal, line=dict(color='orange', width=1), name='Signal'))
                fig_macd.add_trace(go.Bar(x=hist.index, y=hist_macd, marker_color=['red' if val < 0 else 'green' for val in hist_macd], name='Hist'))
                
                fig_macd.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark", showlegend=False)
                st.plotly_chart(fig_macd, use_container_width=True)

        # === TAB 2: 财务透视 ===
        with tab_fin:
            st.subheader("📊 核心财务摘要 (单位: 原币种)")
            fin = stock.financials
            if not fin.empty:
                # 修复可能缺失的字段
                targets = ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income']
                existing = [t for t in targets if t in fin.index]
                
                if existing:
                    # 转置表格，让年份在左边
                    df_fin = fin.loc[existing].T
                    st.dataframe(df_fin.style.format("{:,.0f}").background_gradient(cmap='Blues'), use_container_width=True)
                    
                    # 营收趋势图
                    st.caption("📈 营收与净利趋势")
                    st.bar_chart(df_fin[['Total Revenue', 'Net Income']])
                else:
                    st.warning("数据源未提供标准财务字段")
            else:
                st.info("暂无详细财务报表")

            st.subheader("🏢 公司简介")
            with st.expander("点击展开阅读全文", expanded=True):
                st.write(info.get('longBusinessSummary', '暂无简介'))

        # === TAB 3: 舆情新闻 (已修复报错) ===
        with tab_news:
            st.subheader("📰 最新市场消息")
            news_data = stock.news
            
            if news_data:
                for idx, item in enumerate(news_data[:5]): # 只看前5条
                    # --- 修复报错的核心代码 ---
                    # 使用 .get() 方法，如果找不到 title 就用默认文本，避免 KeyError
                    title = item.get('title', '无标题新闻')
                    link = item.get('link', '#')
                    publisher = item.get('publisher', '未知来源')
                    # 时间戳处理
                    try:
                        pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M')
                    except:
                        pub_time = "近期"

                    # 渲染新闻卡片
                    with st.container():
                        col_img, col_txt = st.columns([1, 4])
                        # 尝试渲染图片
                        thumb = item.get('thumbnail')
                        if thumb and 'resolutions' in thumb:
                            try:
                                img_url = thumb['resolutions'][0]['url']
                                col_img.image(img_url, use_container_width=True)
                            except:
                                col_img.markdown("📷")
                        
                        with col_txt:
                            st.markdown(f"#### [{title}]({link})")
                            st.caption(f"🗓 {pub_time} | 来源: {publisher}")
                        st.markdown("---")
            else:
                st.info("暂无相关新闻")

        # === TAB 4: 智能分析 (静态展示，预留位) ===
        with tab_ai:
            st.success("🤖 AI 投资建议 (根据现有指标自动生成)")
            
            # 简单的基于指标的逻辑判断
            advice_list = []
            
            # 1. 均线判断
            last_close = hist['Close'].iloc[-1]
            ma20_val = hist['Close'].rolling(window=20).mean().iloc[-1]
            if last_close > ma20_val:
                advice_list.append("✅ **趋势**: 股价位于20日均线上方，短期趋势偏多。")
            else:
                advice_list.append("⚠️ **趋势**: 股价跌破20日均线，注意回调风险。")
            
            # 2. 估值判断
            pe = info.get('trailingPE')
            if pe:
                if pe < 15:
                    advice_list.append("✅ **估值**: 静态市盈率低 (PE < 15)，可能具有安全边际。")
                elif pe > 50:
                    advice_list.append("⚠️ **估值**: 静态市盈率较高 (PE > 50)，成长性预期透支风险。")
            
            # 3. 机构评级
            rec = info.get('recommendationKey')
            if rec:
                advice_list.append(f"🏦 **华尔街评级**: {rec.upper().replace('_', ' ')}")

            for advice in advice_list:
                st.markdown(advice)

            st.info("免责声明: 以上分析基于技术指标自动生成，仅供参考，不构成投资建议。")

    except Exception as e:
        st.error("🤯 数据加载遇到一点小问题")
        st.code(f"Error Details: {e}")
        st.markdown("建议：\n1. 检查股票代码是否正确 (A股不需要加后缀，直接输数字，然后在左侧选交易所)\n2. 可能是网络连接超时，请点击左侧'刷新数据'按钮重试")
else:
    st.info("👈 请在左侧侧边栏选择市场并输入代码")
