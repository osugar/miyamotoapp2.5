import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import openai

# ページ設定
st.set_page_config(
    page_title="AIアシスタント",
    page_icon="🤖",
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

# LLM接続設定
LLM_URL = "https://api.openai.com"

def call_llm_api(prompt, context=""):
    """LLM APIを呼び出す関数"""
    try:
        # 売上データのサマリーを作成
        data_summary = f"""
        売上データの概要:
        - 総データ件数: {len(df):,}件
        - 期間: {df['売上年月'].min().strftime('%Y-%m')} 〜 {df['売上年月'].max().strftime('%Y-%m')}
        - 担当者数: {df['担当者'].nunique()}名
        - 商品数: {df['商品名'].nunique()}種類
        - 顧客数: {df['顧客名'].nunique()}社
        - 総売上: ¥{df['売上金額'].sum():,}
        - 総粗利: ¥{df['粗利金額'].sum():,}
        - 平均粗利率: {(df['粗利金額'].sum() / df['売上金額'].sum() * 100):.1f}%
        """
        
        # 最新の売上データ（上位10件）
        recent_sales = df.sort_values('売上年月', ascending=False).head(10)[
            ['売上年月', '商品名', '担当者', '顧客名', '売上金額', '粗利金額']
        ].to_string(index=False)
        
        system_prompt = f"""
        あなたは優秀な売上データ分析アシスタントです。
        以下のコンテキストと売上データを基に、ユーザーの質問に日本語で回答してください。
        データに基づいた具体的な数値や分析を含めて、洞察を提供してください。

        {context}
        
        {data_summary}
        
        最新の売上データ（上位10件）:
        {recent_sales}
        """
        
        api_key = os.environ.get("API_KEY")
        # LLM_URLがOpenAIのAPIエンドポイントの場合のみopenaiパッケージを使う例
        if LLM_URL.startswith("https://api.openai.com"):  # OpenAI公式APIの場合
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        else:
            # ローカルLLMサーバー（OpenAI互換API）にはrequestsでPOST
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{LLM_URL}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=120
            )
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', '回答を生成できませんでした。')
            else:
                return f"API接続エラー: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "LLMサーバーからの応答がタイムアウトしました（120秒）。サーバーの処理が重い可能性があります。しばらく待ってから再度お試しください。"
    except requests.exceptions.ConnectionError:
        return "LLMサーバーに接続できません。サーバーが起動しているか、URLが正しいか確認してください。"
    except Exception as e:
        return f"予期せぬエラーが発生しました: {str(e)}"

# メインページ
st.title("🤖 AIアシスタント")
st.markdown("---")

# APIキーの確認
api_key = os.environ.get("API_KEY")
if not api_key or api_key == "Your_LLM_API_Key_Here":
    st.error("🔑 APIキーが環境変数として設定されていません。デプロイ先の環境変数にAPI_KEYを登録してください。")
    st.stop()

# サイドバー - データフィルター
st.sidebar.header("📊 データフィルター")

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

# フィルター情報をコンテキストに追加
filter_context = f"""
現在のフィルター設定:
- 期間: {date_range[0]} 〜 {date_range[1]}
- 担当者: {selected_staff}
- 商品: {selected_product}
- フィルター適用後のデータ件数: {len(filtered_df):,}件
"""

# チャットインターフェース
st.subheader("💬 AIアシスタントに質問")

# チャット履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザー入力
if prompt := st.chat_input("売上データについて質問してください..."):
    # ユーザーメッセージを追加
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI応答を生成
    with st.chat_message("assistant"):
        with st.spinner("AIが回答を生成中..."):
            response = call_llm_api(prompt, filter_context)
            st.markdown(response)
    
    # AIメッセージを追加
    st.session_state.messages.append({"role": "assistant", "content": response})

# クイック質問ボタン
st.subheader("🚀 よくある質問")

col1, col2 = st.columns(2)

with col1:
    if st.button("📈 売上トレンドを分析して"):
        with st.spinner("分析中..."):
            question = "現在の期間での売上トレンドを分析し、成長している商品や担当者を教えてください。"
            response = call_llm_api(question, filter_context)
            st.info(response)
    
    if st.button("👥 担当者別パフォーマンス"):
        with st.spinner("分析中..."):
            question = "担当者別の売上パフォーマンスを分析し、最も優秀な担当者とその特徴を教えてください。"
            response = call_llm_api(question, filter_context)
            st.info(response)

with col2:
    if st.button("📦 商品別分析"):
        with st.spinner("分析中..."):
            question = "商品別の売上分析を行い、最も売上が良い商品と粗利率の高い商品を教えてください。"
            response = call_llm_api(question, filter_context)
            st.info(response)
    
    if st.button("💰 収益性分析"):
        with st.spinner("分析中..."):
            question = "全体的な収益性を分析し、改善点や推奨事項を教えてください。"
            response = call_llm_api(question, filter_context)
            st.info(response)

# チャット履歴クリアボタン
if st.button("🗑️ チャット履歴をクリア"):
    st.session_state.messages = []
    st.rerun()

# データサマリー表示
st.subheader("📊 現在のデータサマリー")
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

# 接続状況表示
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔗 LLM接続状況")
try:
    response = requests.get(f"{LLM_URL}/health", timeout=5)
    if response.status_code == 200:
        st.sidebar.success("✅ LLMサーバー接続中")
    else:
        st.sidebar.error("❌ LLMサーバーエラー")
except:
    st.sidebar.error("❌ LLMサーバー未接続")
    st.sidebar.info("LLMサーバーを起動してください") 