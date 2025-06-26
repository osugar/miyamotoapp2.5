import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="売上ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データ読み込み関数
@st.cache_data
def load_data():
    df = pd.read_csv('sales_test_data_utf8.csv')
    # 売上年月をdatetime型に変換
    df['売上年月'] = pd.to_datetime(df['売上年月'], format='%Y-%m')
    return df

# データ読み込み
df = load_data()

# サイドバー - フィルター
st.sidebar.header("📊 フィルター設定")

# 期間フィルター
min_date = df['売上年月'].min()
max_date = df['売上年月'].max()
date_range = st.sidebar.date_input(
    "期間選択",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# 担当者フィルター
all_staff = ['全て'] + sorted(df['担当者'].unique().tolist())
selected_staff = st.sidebar.selectbox("担当者", all_staff)

# 商品フィルター
all_products = ['全て'] + sorted(df['商品名'].unique().tolist())
selected_product = st.sidebar.selectbox("商品", all_products)

# 顧客フィルター
all_customers = ['全て'] + sorted(df['顧客名'].unique().tolist())
selected_customer = st.sidebar.selectbox("顧客", all_customers)

# フィルター適用
filtered_df = df.copy()

if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df['売上年月'].dt.date >= start_date) &
        (filtered_df['売上年月'].dt.date <= end_date)
    ]

if selected_staff != '全て':
    filtered_df = filtered_df[filtered_df['担当者'] == selected_staff]

if selected_product != '全て':
    filtered_df = filtered_df[filtered_df['商品名'] == selected_product]

if selected_customer != '全て':
    filtered_df = filtered_df[filtered_df['顧客名'] == selected_customer]

# メインページ
st.title("📊 売上ダッシュボード")
st.markdown("---")

# KPI カード
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_sales = filtered_df['売上金額'].sum()
    st.metric("総売上金額", f"¥{total_sales:,}")

with col2:
    total_profit = filtered_df['粗利金額'].sum()
    st.metric("総粗利金額", f"¥{total_profit:,}")

with col3:
    profit_rate = (total_profit / total_sales * 100) if total_sales > 0 else 0
    st.metric("粗利率", f"{profit_rate:.1f}%")

with col4:
    avg_sales = filtered_df['売上金額'].mean()
    st.metric("平均売上", f"¥{avg_sales:,.0f}")

st.markdown("---")

# 年月別売上・粗利グラフ
st.subheader("📈 年月別売上・粗利推移")

# 月次集計
monthly_data = filtered_df.groupby('売上年月').agg({
    '売上金額': 'sum',
    '粗利金額': 'sum'
}).reset_index()

# 昨対比計算
monthly_data['昨対比_売上'] = monthly_data['売上金額'].pct_change() * 100
monthly_data['昨対比_粗利'] = monthly_data['粗利金額'].pct_change() * 100

# サブプロット作成
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=('売上・粗利推移', '昨対比'),
    vertical_spacing=0.1,
    row_heights=[0.7, 0.3]
)

# 売上・粗利グラフ
fig.add_trace(
    go.Scatter(
        x=monthly_data['売上年月'],
        y=monthly_data['売上金額'],
        mode='lines+markers',
        name='売上金額',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=monthly_data['売上年月'],
        y=monthly_data['粗利金額'],
        mode='lines+markers',
        name='粗利金額',
        line=dict(color='#ff7f0e', width=3),
        marker=dict(size=8)
    ),
    row=1, col=1
)

# 昨対比グラフ
fig.add_trace(
    go.Bar(
        x=monthly_data['売上年月'],
        y=monthly_data['昨対比_売上'],
        name='売上昨対比',
        marker_color='#1f77b4',
        opacity=0.7
    ),
    row=2, col=1
)

fig.add_trace(
    go.Bar(
        x=monthly_data['売上年月'],
        y=monthly_data['昨対比_粗利'],
        name='粗利昨対比',
        marker_color='#ff7f0e',
        opacity=0.7
    ),
    row=2, col=1
)

# レイアウト設定
fig.update_layout(
    height=600,
    showlegend=True,
    title_text="売上・粗利の時系列推移",
    hovermode='x unified'
)

fig.update_xaxes(title_text="年月", row=2, col=1)
fig.update_yaxes(title_text="金額 (円)", row=1, col=1)
fig.update_yaxes(title_text="昨対比 (%)", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# 詳細データテーブル
st.subheader("📋 詳細データ")
st.dataframe(
    filtered_df.sort_values('売上年月', ascending=False),
    use_container_width=True,
    hide_index=True
)

# フィルター情報表示
st.sidebar.markdown("---")
st.sidebar.markdown("### 現在のフィルター")
st.sidebar.markdown(f"**期間:** {date_range[0]} 〜 {date_range[1]}")
st.sidebar.markdown(f"**担当者:** {selected_staff}")
st.sidebar.markdown(f"**商品:** {selected_product}")
st.sidebar.markdown(f"**顧客:** {selected_customer}")
st.sidebar.markdown(f"**データ件数:** {len(filtered_df):,}件")
