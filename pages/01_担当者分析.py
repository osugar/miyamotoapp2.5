import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ページ設定
st.set_page_config(
    page_title="担当者分析",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データ読み込み関数
@st.cache_data
def load_data():
    df = pd.read_csv('sales_test_data_utf8.csv')
    df['売上年月'] = pd.to_datetime(df['売上年月'], format='%Y-%m')
    return df

# データ読み込み
df = load_data()

# 担当者選択
st.title("👤 担当者分析ダッシュボード")
st.markdown("---")

# 担当者選択
all_staff = sorted(df['担当者'].unique().tolist())
selected_staff = st.selectbox("担当者を選択してください", all_staff)

if selected_staff:
    # 選択された担当者のデータをフィルター
    staff_df = df[df['担当者'] == selected_staff].copy()
    
    # KPI カード
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = staff_df['売上金額'].sum()
        st.metric("総売上金額", f"¥{total_sales:,}")
    
    with col2:
        total_profit = staff_df['粗利金額'].sum()
        st.metric("総粗利金額", f"¥{total_profit:,}")
    
    with col3:
        profit_rate = (total_profit / total_sales * 100) if total_sales > 0 else 0
        st.metric("粗利率", f"{profit_rate:.1f}%")
    
    with col4:
        avg_sales = staff_df['売上金額'].mean()
        st.metric("平均売上", f"¥{avg_sales:,.0f}")
    
    st.markdown("---")
    
    # 期間フィルター
    st.subheader("📅 期間フィルター")
    col1, col2 = st.columns(2)
    
    with col1:
        min_date = staff_df['売上年月'].min()
        max_date = staff_df['売上年月'].max()
        start_date = st.date_input("開始日", value=min_date, min_value=min_date, max_value=max_date)
    
    with col2:
        end_date = st.date_input("終了日", value=max_date, min_value=min_date, max_value=max_date)
    
    # 期間フィルター適用
    filtered_staff_df = staff_df[
        (staff_df['売上年月'].dt.date >= start_date) &
        (staff_df['売上年月'].dt.date <= end_date)
    ]
    
    # 時系列グラフ
    st.subheader("📈 売上・粗利・昨対比の時系列推移")
    
    # 月次集計
    monthly_data = filtered_staff_df.groupby('売上年月').agg({
        '売上金額': 'sum',
        '粗利金額': 'sum'
    }).reset_index()
    
    # 昨対比計算
    monthly_data['昨対比_売上'] = monthly_data['売上金額'].pct_change() * 100
    monthly_data['昨対比_粗利'] = monthly_data['粗利金額'].pct_change() * 100
    
    # サブプロット作成
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{selected_staff}の売上・粗利推移', '昨対比'),
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
        height=500,
        showlegend=True,
        title_text=f"{selected_staff}の売上・粗利分析",
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="年月", row=2, col=1)
    fig.update_yaxes(title_text="金額 (円)", row=1, col=1)
    fig.update_yaxes(title_text="昨対比 (%)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # TOP20商品リスト
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 売上金額TOP20商品")
        
        # 売上金額TOP20
        sales_top20 = filtered_staff_df.groupby('商品名').agg({
            '売上金額': 'sum',
            '粗利金額': 'sum'
        }).reset_index()
        sales_top20 = sales_top20.sort_values('売上金額', ascending=False).head(20)
        
        # 売上TOP20テーブル
        sales_display = sales_top20.copy()
        sales_display['売上金額'] = sales_display['売上金額'].apply(lambda x: f"¥{x:,}")
        sales_display['粗利金額'] = sales_display['粗利金額'].apply(lambda x: f"¥{x:,}")
        sales_display['粗利率'] = (sales_display['粗利金額'].str.replace('¥', '').str.replace(',', '').astype(float) / 
                                  sales_display['売上金額'].str.replace('¥', '').str.replace(',', '').astype(float) * 100).round(1)
        sales_display['粗利率'] = sales_display['粗利率'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            sales_display[['商品名', '売上金額', '粗利金額', '粗利率']],
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.subheader("💰 粗利金額TOP20商品")
        
        # 粗利金額TOP20
        profit_top20 = filtered_staff_df.groupby('商品名').agg({
            '売上金額': 'sum',
            '粗利金額': 'sum'
        }).reset_index()
        profit_top20 = profit_top20.sort_values('粗利金額', ascending=False).head(20)
        
        # 粗利TOP20テーブル
        profit_display = profit_top20.copy()
        profit_display['売上金額'] = profit_display['売上金額'].apply(lambda x: f"¥{x:,}")
        profit_display['粗利金額'] = profit_display['粗利金額'].apply(lambda x: f"¥{x:,}")
        profit_display['粗利率'] = (profit_display['粗利金額'].str.replace('¥', '').str.replace(',', '').astype(float) / 
                                   profit_display['売上金額'].str.replace('¥', '').str.replace(',', '').astype(float) * 100).round(1)
        profit_display['粗利率'] = profit_display['粗利率'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            profit_display[['商品名', '売上金額', '粗利金額', '粗利率']],
            use_container_width=True,
            hide_index=True
        )
    
    # 詳細データ
    st.subheader("📋 詳細データ")
    st.dataframe(
        filtered_staff_df.sort_values('売上年月', ascending=False),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("担当者を選択してください") 