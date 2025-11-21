import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="ProTrade Alpha", layout="wide", page_icon="⚡")

# --- CSS样式优化 ---
st.markdown("""
<style>
    .big-font { font-size:20px !important; }
    .metric-container { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏设置 ---
with st.sidebar:
    st.title("⚡ ProTrade Alpha")
    ticker = st.text_input("股票代码 (Ticker)", value="AAPL")
    
    st.markdown("### ⚙️ 图表设置")
    time_range = st.selectbox("时间范围", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"], index=3)
    
    # 技术指标开关
    st.markdown("### 📈 技术指标")
    show_ma5 = st.checkbox("MA 5 (周线)", value=True)
    show_ma20 = st.checkbox("MA 20 (月线)", value=True)
    show_ma50 = st.checkbox("MA 50 (季线)", value=False)
    show_vol = st.checkbox("显示成交量", value=True)

    st.info("""
    **代码指南:**
    🇺🇸 美股: AAPL, NVDA, TSLA
    🇨🇳 沪市: 600519.SS (茅台)
    🇨🇳 深市: 300750.SZ (宁得)
    """)

# --- 3. 主程序逻辑 ---
if ticker:
    try:
        # 获取数据
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 顶部核心行情条
        col1, col2, col3, col4, col5 = st.columns(5)
        
        curr_price = info.get('currentPrice', 0)
        prev_close = info.get('previousClose', 0)
        if curr_price and prev_close:
            delta = curr_price - prev_close
            pct = (delta / prev_close) * 100
            color = "green" if delta >= 0 else "red"
        else:
            delta, pct = 0, 0
        
        # 货币符号
        currency = "$" if info.get('currency') == 'USD' else "¥"

        with col1:
            st.metric("最新价格", f"{currency}{curr_price:,.2f}", f"{delta:.2f} ({pct:.2f}%)")
        with col2:
            st.metric("市盈率 (PE)", f"{info.get('trailingPE', 'N/A')}")
        with col3:
            mkt_cap = info.get('marketCap', 0)
            val_str = f"{mkt_cap/1e9:.2f} B" if mkt_cap > 1e9 else f"{mkt_cap/1e6:.2f} M"
            st.metric("总市值", val_str)
        with col4:
            st.metric("52周最高", f"{currency}{info.get('fiftyTwoWeekHigh', 'N/A')}")
        with col5:
             st.metric("Beta (波动率)", f"{info.get('beta', 'N/A')}")

        st.markdown(f"## {info.get('shortName', ticker)} ({ticker.upper()})")
        
        # --- 4. 分页显示功能 (Tabs) ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 技术分析", "💰 基本面数据", "🎯 机构评级", "📰 实时舆情"])

        # === TAB 1: 技术分析 (K线图) ===
        with tab1:
            hist = stock.history(period=time_range)
            
            # 创建K线图
            fig = go.Figure()
            
            # K线
            fig.add_trace(go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name='Price'))
            
            # 均线逻辑
            if show_ma5:
                ma5 = hist['Close'].rolling(window=5).mean()
                fig.add_trace(go.Scatter(x=hist.index, y=ma5, mode='lines', name='MA 5', line=dict(color='orange', width=1)))
            
            if show_ma20:
                ma20 = hist['Close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(x=hist.index, y=ma20, mode='lines', name='MA 20', line=dict(color='blue', width=1)))
                
            if show_ma50:
                ma50 = hist['Close'].rolling(window=50).mean()
                fig.add_trace(go.Scatter(x=hist.index, y=ma50, mode='lines', name='MA 50', line=dict(color='purple', width=1)))

            # 成交量
            if show_vol:
                colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for index, row in hist.iterrows()]
                fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volume', marker_color=colors, yaxis='y2', opacity=0.3))

            # 布局设置
            fig.update_layout(
                height=600,
                xaxis_rangeslider_visible=False,
                hovermode='x unified',
                yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False),
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

        # === TAB 2: 基本面 (财报) ===
        with tab2:
            st.subheader("核心利润表 (Income Statement)")
            fin = stock.financials
            if not fin.empty:
                # 筛选重要字段
                key_metrics = ['Total Revenue', 'Net Income', 'Gross Profit', 'EBITDA', 'Operating Income']
                available_metrics = [m for m in key_metrics if m in fin.index]
                
                # 显示表格
                st.dataframe(fin.loc[available_metrics].style.format("{:,.0f}"), use_container_width=True)
                
                # 可视化：营收 vs 净利润
                if 'Total Revenue' in fin.index and 'Net Income' in fin.index:
                    st.subheader("营收 vs 净利润 趋势")
                    chart_data = fin.loc[['Total Revenue', 'Net Income']].T
                    st.bar_chart(chart_data)
            else:
                st.warning("暂无详细财报数据")
            
            st.markdown("---")
            st.subheader("公司简介")
            st.write(info.get('longBusinessSummary', '无简介'))

        # === TAB 3: 机构评级 ===
        with tab3:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("分析师目标价")
                target_mean = info.get('targetMeanPrice')
                target_high = info.get('targetHighPrice')
                target_low = info.get('targetLowPrice')
                
                if target_mean:
                    st.metric("平均目标价", f"{currency}{target_mean}")
                    st.write(f"最高预测: **{currency}{target_high}**")
                    st.write(f"最低预测: **{currency}{target_low}**")
                    
                    # 简单的进度条表示位置
                    if target_high != target_low:
                        progress = (curr_price - target_low) / (target_high - target_low)
                        progress = min(max(progress, 0.0), 1.0) # 限制在0-1
                        st.progress(progress)
                        st.caption("当前价格在分析师预测区间的位置 (左=低估, 右=高估)")
                else:
                    st.info("暂无分析师目标价数据")

            with c2:
                st.subheader("大股东/机构持仓")
                major_holders = stock.major_holders
                if major_holders is not None:
                    # 清洗一下数据格式以便展示
                    st.dataframe(major_holders, use_container_width=True, hide_index=True)
                else:
                    st.info("暂无持仓数据")

        # === TAB 4: 新闻 ===
        with tab4:
            st.subheader(f"关于 {ticker} 的最新消息")
            news = stock.news
            if news:
                for n in news:
                    with st.container():
                        col_img, col_txt = st.columns([1, 4])
                        # 尝试显示缩略图
                        if 'thumbnail' in n and 'resolutions' in n['thumbnail']:
                            try:
                                thumb_url = n['thumbnail']['resolutions'][0]['url']
                                with col_img:
                                    st.image(thumb_url, use_container_width=True)
                            except:
                                pass
                        
                        with col_txt:
                            st.markdown(f"### [{n['title']}]({n['link']})")
                            st.caption(f"来源: {n['publisher']} | 发布时间: {datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')}")
                        st.markdown("---")
            else:
                st.write("暂无最新新闻")

    except Exception as e:
        st.error(f"哎呀，出错了！请检查股票代码是否正确。\n错误信息: {e}")
