
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
# ttl=60 表示每60秒过期一次，强制重新抓取数据
@st.cache_data(ttl=60)
def get_merged_data():
    # 1. 定义要获取的合约代码
    symbol_cu = "cu0"
    symbol_al = "al0"

    # --- 内部函数：获取单品种的“历史+实时”拼接数据 ---
    def fetch_smart_data(symbol):
        # A. 获取日线历史
        df_daily = ak.futures_zh_daily_sina(symbol=symbol)
        
        # B. 获取最新的1分钟线
        df_min = ak.futures_zh_minute_sina(symbol=symbol, period="1")
        
        # C. 提取最新一笔数据
        if not df_min.empty:
            latest_row = df_min.iloc[-1]
            latest_price = float(latest_row['close'])
            
            # ===【修复点在这里】===
            # 分钟数据的列名是 'datetime'，不是 'day'
            latest_time_str = latest_row['datetime'] 
            latest_date = pd.to_datetime(latest_time_str).date()
            
            # D. 检查日线数据的最后一天
            last_daily_date = pd.to_datetime(df_daily['date'].iloc[-1]).date()
            
            # E. 拼接逻辑：如果实时日期比日线日期新，就补一行
            if latest_date > last_daily_date:
                new_row = pd.DataFrame({
                    'date': [pd.to_datetime(latest_date)],
                    'open': [float(latest_row['open'])],
                    'high': [float(latest_row['high'])],
                    'low':  [float(latest_row['low'])],
                    'close': [latest_price],
                    'volume': [float(latest_row['volume'])],
                    'hold': [0],
                    'settle': [latest_price]
                })
                df_daily = pd.concat([df_daily, new_row], ignore_index=True)
            
            # F. 如果日期一样，用最新价更新收盘价
            elif latest_date == last_daily_date:
                df_daily.at[df_daily.index[-1], 'close'] = latest_price

        return df_daily[['date', 'close']]

    # 2. 获取数据
    df_cu = fetch_smart_data(symbol_cu)
    df_al = fetch_smart_data(symbol_al)

    # 3. 数据合并
    df_cu = df_cu.rename(columns={'close': 'copper_price', 'date': 'date'})
    df_al = df_al.rename(columns={'close': 'aluminum_price', 'date': 'date'})
    
    df_cu['date'] = pd.to_datetime(df_cu['date'])
    df_al['date'] = pd.to_datetime(df_al['date'])

    df_merge = pd.merge(df_cu, df_al, on='date', how='inner')

    # 4. 计算比价
    df_merge['ratio'] = df_merge['copper_price'] / df_merge['aluminum_price']
    
    # 5. 格式化日期显示
    df_merge['date_str'] = df_merge['date'].dt.strftime('%Y-%m-%d')

    return df_merge

# ==========================================
# 执行与展示
# ==========================================
try:
    with st.spinner('正在连接交易所获取最新行情...'):
        df = get_merged_data()

    latest_record = df.iloc[-1]
    latest_date = latest_record['date_str']
    latest_ratio = round(latest_record['ratio'], 4) # 保留4位小数更精确
    latest_cu = int(latest_record['copper_price'])
    latest_al = int(latest_record['aluminum_price'])

    # 1. 指标卡片
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新日期", latest_date)
    col2.metric("当前铜银比", f"{latest_ratio}")
    col3.metric("沪铜主力", f"¥{latest_cu:,}")
    col4.metric("沪铝主力", f"¥{latest_al:,}")

    # 2. 图表
    st.subheader("历史走势图 (含今日实时)")
    fig = px.line(df, x='date', y='ratio', 
                  title='铜/铝价格比率走势',
                  labels={'date': '日期', 'ratio': '比值'})
    fig.update_traces(line_color='#FF4B4B', line_width=2)
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # 3. 表格
    with st.expander("查看原始数据明细"):
        st.dataframe(
            df[['date_str', 'copper_price', 'aluminum_price', 'ratio']].sort_values(by='date_str', ascending=False),
            use_container_width=True
        )

except Exception as e:
    st.error(f"出错啦，请截图发给开发者: {e}")
