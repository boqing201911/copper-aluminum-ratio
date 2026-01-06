import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go

# --- 1. 网页标题设置 ---
st.set_page_config(page_title="伯清的市场观察", layout="wide")
st.title("📊 宏观对冲监测：沪铜/沪银 比价走势")

# --- 2. 获取数据的函数 (修改版：指定具体合约) ---
@st.cache_data
def get_data():
    with st.spinner('正在获取 沪铜2602 和 沪铝2602 数据...'):
        # 1. 获取 沪铜2602 (代码格式通常是 交易所品种+日期，新浪接口一般是 cu2602)
        # 注意：具体合约的数据长度有限，只有该合约上市后的数据
        df_cu = ak.futures_zh_daily_sina(symbol="cu2602")
        df_cu = df_cu[['date', 'close']].rename(columns={'date': '日期', 'close': '铜价格'})
        
        # 2. 获取 沪铝2602 (al2602)
        df_al = ak.futures_zh_daily_sina(symbol="al2602")
        df_al = df_al[['date', 'close']].rename(columns={'date': '日期', 'close': '铝价格'})
        
        # 3. 拼合数据
        df_merge = pd.merge(df_cu, df_al, on='日期', how='inner')
        df_merge['日期'] = pd.to_datetime(df_merge['日期'])
        
        # 4. 计算比值：铜/铝
        df_merge['比值'] = df_merge['铜价格'] / df_merge['铝价格']
        
        return df_merge

# --- 3. 执行获取数据 ---
try:
    df = get_data()
    
    # 获取最新的比值数据
    latest_ratio = df['比值'].iloc[-1]
    latest_date = df['日期'].iloc[-1].strftime('%Y-%m-%d')
    
    # 在网页顶部显示最新数据
    col1, col2, col3 = st.columns(3)
    col1.metric("最新日期", latest_date)
    col2.metric("当前铜银比", f"{latest_ratio:.2f}")
    
    # --- 4. 画图 (使用交互式图表) ---
    st.subheader("历史走势图 (可缩放拖拽)")
    
    # 创建线条
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['日期'], 
        y=df['比值'],
        mode='lines',
        name='铜银比',
        line=dict(color='#1f77b4', width=2)
    ))
    
    # 设置图表样式
    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="比值 (沪铜/沪银)",
        hovermode="x unified", # 鼠标放上去显示数据
        height=600
    )
    
    # 把图画在网页上
    st.plotly_chart(fig, use_container_width=True)

    # 显示原始数据表格（勾选框）
    if st.checkbox('显示原始数据明细'):
        st.dataframe(df.sort_values('日期', ascending=False))

except Exception as e:
    st.error(f"数据获取失败，可能是网络问题或接口调整。错误信息: {e}")
