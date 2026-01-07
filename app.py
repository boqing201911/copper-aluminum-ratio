
import streamlit as st
import pandas as pd
import plotly.express as px
import akshare as ak
from datetime import datetime

# ==========================================
# 页面基础配置
# ==========================================
st.set_page_config(
    page_title="铜铝比价实时监测",
    layout="wide",
    page_icon="📈"
)

st.title("📊 宏观对冲监测：沪铜/沪铝 比价走势 (实时版)")

# ==========================================
# 核心数据获取函数 (带实时拼接功能)
# ==========================================
# ttl=60 表示每60秒过期一次，强制重新抓取数据，保证盘中实时性
@st.cache_data(ttl=60)
def get_merged_data():
    # 1. 定义要获取的合约代码 (cu0=铜主力, al0=铝主力)
    symbol_cu = "cu0"
    symbol_al = "al0"

    # --- 内部函数：获取单品种的“历史+实时”拼接数据 ---
    def fetch_smart_data(symbol):
        # A. 获取日线历史 (可能有延迟)
        df_daily = ak.futures_zh_daily_sina(symbol=symbol)
        
        # B. 获取最新的1分钟线 (这是实时的)
        # period="1" 表示1分钟线
        df_min = ak.futures_zh_minute_sina(symbol=symbol, period="1")
        
        # C. 提取最新一笔数据
        if not df_min.empty:
            latest_row = df_min.iloc[-1]
            latest_price = float(latest_row['close'])
            # 格式化时间字符串 "2026-01-07 10:00:00" -> datetime对象
            latest_time_str = latest_row['day']
            latest_date = pd.to_datetime(latest_time_str).date()
            
            # D. 检查日线数据的最后一天
            last_daily_date = pd.to_datetime(df_daily['date'].iloc[-1]).date()
            
            # E. 关键逻辑：如果“实时日期”比“日线最后日期”要新，说明日线没更新，我们要人工补一行
            if latest_date > last_daily_date:
                # 创建一个新行，格式要和 df_daily 一样
                new_row = pd.DataFrame({
                    'date': [pd.to_datetime(latest_date)], # 保持 datetime 类型
                    'open': [float(latest_row['open'])],
                    'high': [float(latest_row['high'])],
                    'low':  [float(latest_row['low'])],
                    'close': [latest_price],
                    'volume': [float(latest_row['volume'])],
                    'hold': [0], # 分钟线可能没持仓量，填0即可
                    'settle': [latest_price] # 盘中暂时用最新价当结算价
                })
                # 拼接到最后
                df_daily = pd.concat([df_daily, new_row], ignore_index=True)
            
            # F. 如果日期一样，说明日线已经更新了(或者是收盘了)，
            # 但为了保证价格最最新，我们可以用 minute 的 close 更新日线的 close
            elif latest_date == last_daily_date:
                df_daily.at[df_daily.index[-1], 'close'] = latest_price

        return df_daily[['date', 'close']]

    # 2. 分别获取铜和铝的智能数据
    df_cu = fetch_smart_data(symbol_cu)
    df_al = fetch_smart_data(symbol_al)

    # 3. 数据合并
    # 重命名列，方便识别
    df_cu = df_cu.rename(columns={'close': 'copper_price', 'date': 'date'})
    df_al = df_al.rename(columns={'close': 'aluminum_price', 'date': 'date'})
    
    # 确保日期列是 datetime 类型，方便合并
    df_cu['date'] = pd.to_datetime(df_cu['date'])
    df_al['date'] = pd.to_datetime(df_al['date'])

    # 按日期合并
    df_merge = pd.merge(df_cu, df_al, on='date', how='inner')

    # 4. 计算比价
    df_merge['ratio'] = df_merge['copper_price'] / df_merge['aluminum_price']
    
    # 5. 为了显示美观，把日期里的 00:00:00 去掉，只保留日期部分
    df_merge['date_str'] = df_merge['date'].dt.strftime('%Y-%m-%d')

    return df_merge

# ==========================================
# 执行数据获取
# ==========================================
try:
    with st.spinner('正在连接交易所获取最新行情...'):
        df = get_merged_data()

    # 获取最新一天的数值
    latest_record = df.iloc[-1]
    latest_date = latest_record['date_str']
    latest_ratio = round(latest_record['ratio'], 2)
    latest_cu = int(latest_record['copper_price'])
    latest_al = int(latest_record['aluminum_price'])

    # ==========================================
    # 页面展示部分
    # ==========================================

    # 1. 核心指标卡片
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新日期", latest_date)
    col2.metric("当前铜银比", f"{latest_ratio}")
    col3.metric("沪铜主力", f"¥{latest_cu:,}")
    col4.metric("沪铝主力", f"¥{latest_al:,}")

    # 2. 交互式图表
    st.subheader("历史走势图 (可缩放拖拽)")
    
    # 使用 Plotly 画交互图
    fig = px.line(df, x='date', y='ratio', 
                  title='铜/铝价格比率 (Copper/Aluminum Ratio)',
                  labels={'date': '日期', 'ratio': '比值'})
    
    # 优化图表样式
    fig.update_traces(line_color='#FF4B4B', line_width=2)
    fig.update_layout(hovermode="x unified") # 鼠标悬停显示数值
    
    st.plotly_chart(fig, use_container_width=True)

    # 3. 数据明细表格 (默认折叠)
    with st.expander("查看原始数据明细"):
        # 按日期倒序排列，最新的在最上面
        st.dataframe(
            df[['date_str', 'copper_price', 'aluminum_price', 'ratio']].sort_values(by='date_str', ascending=False),
            use_container_width=True
        )

except Exception as e:
    st.error(f"数据获取失败，请稍后刷新重试。错误信息: {e}")
