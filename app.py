import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from utils import data_manager, FilterManager, ChartManager

# ページ設定
st.set_page_config(
    page_title="売上ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSSでローディング状態を改善
st.markdown("""
<style>
    .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 200px;
        background: #f0f2f6;
        border-radius: 10px;
        margin: 20px 0;
    }
    .error-container {
        background: #ffebee;
        border: 1px solid #f44336;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #c62828;
    }
    .success-container {
        background: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

# データ読み込み
with st.spinner("データを読み込み中..."):
    df = data_manager.load_data()

# データが空の場合はエラーメッセージを表示
if df.empty:
    st.error("データの読み込みに失敗しました。CSVファイルが正しい形式で配置されているか確認してください。")
    st.stop()

# データ検証
validation_result = data_manager.validate_data(df)
if not validation_result['is_valid']:
    st.warning("データに問題が検出されました:")
    for issue in validation_result['issues']:
        st.write(f"⚠️ {issue}")

# データ概要表示
if st.sidebar.checkbox("データ概要を表示"):
    st.sidebar.markdown("### 📊 データ概要")
    summary = validation_result['summary']
    st.sidebar.markdown(f"**総レコード数:** {summary['total_records']:,}件")
    st.sidebar.markdown(f"**期間:** {summary['date_range']}")
    st.sidebar.markdown(f"**担当者数:** {summary['staff_count']}名")
    st.sidebar.markdown(f"**商品数:** {summary['product_count']}種類")
    st.sidebar.markdown(f"**顧客数:** {summary['customer_count']}社")

# サイドバー - フィルター
st.sidebar.header("📊 フィルター設定")

# 期間フィルター
min_date = df['売上年月'].min()
max_date = df['売上年月'].max()
date_range = st.sidebar.date_input(
    "期間選択",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    help="分析対象の期間を選択してください"
)

# 担当者フィルター
all_staff = ['全て'] + sorted(df['担当者'].unique().tolist())
selected_staff = st.sidebar.selectbox(
    "担当者", 
    all_staff,
    help="特定の担当者のデータのみを表示します"
)

# 商品フィルター
all_products = ['全て'] + sorted(df['商品名'].unique().tolist())
selected_product = st.sidebar.selectbox(
    "商品", 
    all_products,
    help="特定の商品のデータのみを表示します"
)

# 顧客フィルター
all_customers = ['全て'] + sorted(df['顧客名'].unique().tolist())
selected_customer = st.sidebar.selectbox(
    "顧客", 
    all_customers,
    help="特定の顧客のデータのみを表示します"
)

# フィルター適用
filtered_df = FilterManager.apply_filters(
    df, date_range, selected_staff, selected_product, selected_customer
)

# フィルター結果の表示
if len(filtered_df) == 0:
    st.warning("選択されたフィルター条件に該当するデータがありません。")
    st.stop()

# メインページ
st.title("📊 売上ダッシュボード")
st.markdown("---")

# KPI カード
ChartManager.create_kpi_cards(filtered_df)

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

# 追加分析セクション
st.markdown("---")
st.subheader("📊 追加分析")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🏆 売上TOP10商品**")
    top_products = filtered_df.groupby('商品名')['売上金額'].sum().sort_values(ascending=False).head(10)
    top_products_df = pd.DataFrame({
        '商品名': top_products.index,
        '売上金額': top_products.values
    })
    top_products_df['売上金額'] = top_products_df['売上金額'].apply(ChartManager.format_currency)
    st.dataframe(top_products_df, use_container_width=True, hide_index=True)

with col2:
    st.markdown("**👥 売上TOP10担当者**")
    top_staff = filtered_df.groupby('担当者')['売上金額'].sum().sort_values(ascending=False).head(10)
    top_staff_df = pd.DataFrame({
        '担当者': top_staff.index,
        '売上金額': top_staff.values
    })
    top_staff_df['売上金額'] = top_staff_df['売上金額'].apply(ChartManager.format_currency)
    st.dataframe(top_staff_df, use_container_width=True, hide_index=True)

# 詳細データテーブル
st.markdown("---")
st.subheader("📋 詳細データ")

# データエクスポート機能
csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
st.download_button(
    label="📥 CSVダウンロード",
    data=csv,
    file_name=f"売上データ_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

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

# パフォーマンス情報
if st.sidebar.checkbox("パフォーマンス情報を表示"):
    st.sidebar.markdown("### ⚡ パフォーマンス")
    st.sidebar.markdown(f"**処理時間:** {st.session_state.get('processing_time', 'N/A')}")
    st.sidebar.markdown(f"**メモリ使用量:** {st.session_state.get('memory_usage', 'N/A')}")
