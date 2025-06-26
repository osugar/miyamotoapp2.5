import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import openai
import os

# ページ設定
st.set_page_config(
    page_title="商品分析",
    page_icon="📦",
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

# 商品選択
st.title("📦 商品分析ダッシュボード")
st.markdown("---")

# 商品選択
all_products = sorted(df['商品名'].unique().tolist())
selected_product = st.selectbox("商品を選択してください", all_products)

if selected_product:
    # 選択された商品のデータをフィルター
    product_df = df[df['商品名'] == selected_product].copy()
    
    # KPI カード
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = product_df['売上金額'].sum()
        st.metric("総売上金額", f"¥{total_sales:,}")
    
    with col2:
        total_profit = product_df['粗利金額'].sum()
        st.metric("総粗利金額", f"¥{total_profit:,}")
    
    with col3:
        profit_rate = (total_profit / total_sales * 100) if total_sales > 0 else 0
        st.metric("粗利率", f"{profit_rate:.1f}%")
    
    with col4:
        avg_sales = product_df['売上金額'].mean()
        st.metric("平均売上", f"¥{avg_sales:,.0f}")
    
    st.markdown("---")
    
    # 期間フィルター
    st.subheader("📅 期間フィルター")
    col1, col2 = st.columns(2)
    
    with col1:
        min_date = product_df['売上年月'].min()
        max_date = product_df['売上年月'].max()
        start_date = st.date_input("開始日", value=min_date, min_value=min_date, max_value=max_date)
    
    with col2:
        end_date = st.date_input("終了日", value=max_date, min_value=min_date, max_value=max_date)
    
    # 期間フィルター適用
    filtered_product_df = product_df[
        (product_df['売上年月'].dt.date >= start_date) &
        (product_df['売上年月'].dt.date <= end_date)
    ]
    
    # 時系列グラフ
    st.subheader("📈 売上・粗利・昨対比の時系列推移")
    
    # 月次集計
    monthly_data = filtered_product_df.groupby('売上年月').agg({
        '売上金額': 'sum',
        '粗利金額': 'sum'
    }).reset_index()
    
    # 昨対比計算
    monthly_data['昨対比_売上'] = monthly_data['売上金額'].pct_change() * 100
    monthly_data['昨対比_粗利'] = monthly_data['粗利金額'].pct_change() * 100
    
    # サブプロット作成
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{selected_product}の売上・粗利推移', '昨対比'),
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
        title_text=f"{selected_product}の売上・粗利分析",
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="年月", row=2, col=1)
    fig.update_yaxes(title_text="金額 (円)", row=1, col=1)
    fig.update_yaxes(title_text="昨対比 (%)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 売上上位担当者TOP20
    st.subheader("👥 売上上位担当者TOP20")
    
    # 担当者別売上集計
    staff_sales = filtered_product_df.groupby('担当者').agg({
        '売上金額': 'sum',
        '粗利金額': 'sum',
        '売上年月': 'count'  # 取引回数
    }).reset_index()
    staff_sales = staff_sales.rename(columns={'売上年月': '取引回数'})
    staff_sales = staff_sales.sort_values('売上金額', ascending=False).head(20)
    
    # 表示用データフレーム作成
    staff_display = staff_sales.copy()
    staff_display['売上金額'] = staff_display['売上金額'].apply(lambda x: f"¥{x:,}")
    staff_display['粗利金額'] = staff_display['粗利金額'].apply(lambda x: f"¥{x:,}")
    staff_display['粗利率'] = (staff_display['粗利金額'].str.replace('¥', '').str.replace(',', '').astype(float) / 
                              staff_display['売上金額'].str.replace('¥', '').str.replace(',', '').astype(float) * 100).round(1)
    staff_display['粗利率'] = staff_display['粗利率'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        staff_display[['担当者', '売上金額', '粗利金額', '粗利率', '取引回数']],
        use_container_width=True,
        hide_index=True
    )
    
    # 担当者別売上グラフ
    st.subheader("📊 担当者別売上比較")
    
    fig_staff = px.bar(
        staff_sales.head(10),  # TOP10のみ表示
        x='担当者',
        y='売上金額',
        color='粗利金額',
        title=f"{selected_product}の担当者別売上（TOP10）",
        color_continuous_scale='viridis',
        text='売上金額'
    )
    
    fig_staff.update_traces(
        texttemplate='¥%{text:,}',
        textposition='outside'
    )
    
    fig_staff.update_layout(
        height=400,
        xaxis_title="担当者",
        yaxis_title="売上金額 (円)",
        coloraxis_colorbar_title="粗利金額"
    )
    
    st.plotly_chart(fig_staff, use_container_width=True)
    
    # 詳細データ
    st.subheader("📋 詳細データ")
    st.dataframe(
        filtered_product_df.sort_values('売上年月', ascending=False),
        use_container_width=True,
        hide_index=True
    )

    # --- AIアドバイス機能 ---
    st.markdown("---")
    st.subheader("🤖 AIアシスタントに質問する")

    user_question = st.text_input("AIに聞きたいことを入力してください（例：この商品の売上を伸ばすには？）")

    if user_question:
        # 分析用データを要約（例として直近3ヶ月の売上・粗利を渡す）
        summary_df = filtered_product_df.sort_values('売上年月', ascending=False).head(3)
        summary_text = summary_df[['売上年月', '売上金額', '粗利金額']].to_string(index=False)

        prompt = f"""
あなたは優秀な営業コンサルタントです。
以下は{selected_product}の直近3ヶ月の売上データです。

{summary_text}

ユーザーからの質問: {user_question}

このデータをもとに、分かりやすくアドバイスや回答を日本語でお願いします。
"""

        api_key = os.environ.get("API_KEY")
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_answer = response.choices[0].message.content
            st.success("AIアドバイス:")
            st.write(ai_answer)
        except Exception as e:
            st.error(f"AIアドバイスの取得中にエラーが発生しました: {e}")

else:
    st.info("商品を選択してください") 