import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import openai
import numpy as np

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

def analyze_data_for_context(filtered_df):
    """より詳細なデータ分析を行い、AIのコンテキストを強化する"""
    analysis = {}
    
    # 基本統計
    analysis['basic_stats'] = {
        'total_records': len(filtered_df),
        'total_sales': filtered_df['売上金額'].sum(),
        'total_profit': filtered_df['粗利金額'].sum(),
        'avg_profit_rate': (filtered_df['粗利金額'].sum() / filtered_df['売上金額'].sum() * 100) if filtered_df['売上金額'].sum() > 0 else 0
    }
    
    # 担当者別分析
    staff_analysis = filtered_df.groupby('担当者').agg({
        '売上金額': ['sum', 'mean', 'count'],
        '粗利金額': ['sum', 'mean']
    }).round(0)
    staff_analysis.columns = ['総売上', '平均売上', '取引回数', '総粗利', '平均粗利']
    staff_analysis['粗利率'] = (staff_analysis['総粗利'] / staff_analysis['総売上'] * 100).round(1)
    analysis['staff_analysis'] = staff_analysis.sort_values('総売上', ascending=False)
    
    # 商品別分析
    product_analysis = filtered_df.groupby('商品名').agg({
        '売上金額': ['sum', 'mean', 'count'],
        '粗利金額': ['sum', 'mean']
    }).round(0)
    product_analysis.columns = ['総売上', '平均売上', '取引回数', '総粗利', '平均粗利']
    product_analysis['粗利率'] = (product_analysis['総粗利'] / product_analysis['総売上'] * 100).round(1)
    analysis['product_analysis'] = product_analysis.sort_values('総売上', ascending=False)
    
    # 月別トレンド分析
    monthly_trend = filtered_df.groupby('売上年月').agg({
        '売上金額': 'sum',
        '粗利金額': 'sum',
        '商品名': 'count'
    }).rename(columns={'商品名': '取引件数'})
    monthly_trend['粗利率'] = (monthly_trend['粗利金額'] / monthly_trend['売上金額'] * 100).round(1)
    analysis['monthly_trend'] = monthly_trend
    
    # 顧客別分析（上位10社）
    customer_analysis = filtered_df.groupby('顧客名').agg({
        '売上金額': 'sum',
        '粗利金額': 'sum',
        '商品名': 'count'
    }).rename(columns={'商品名': '取引回数'})
    customer_analysis['粗利率'] = (customer_analysis['粗利金額'] / customer_analysis['売上金額'] * 100).round(1)
    analysis['customer_analysis'] = customer_analysis.sort_values('売上金額', ascending=False).head(10)
    
    return analysis

def call_llm_api(prompt, context="", filtered_df=None):
    """LLM APIを呼び出す関数（改善版）"""
    try:
        # フィルターされたデータの詳細分析
        if filtered_df is not None and len(filtered_df) > 0:
            analysis = analyze_data_for_context(filtered_df)
            
            # より詳細なデータサマリーを作成
            data_summary = f"""
            売上データの詳細分析:
            
            【基本統計】
            - 総データ件数: {analysis['basic_stats']['total_records']:,}件
            - 総売上: ¥{analysis['basic_stats']['total_sales']:,}
            - 総粗利: ¥{analysis['basic_stats']['total_profit']:,}
            - 平均粗利率: {analysis['basic_stats']['avg_profit_rate']:.1f}%
            
            【担当者別売上ランキング（上位5名）】
            {analysis['staff_analysis'].head().to_string()}
            
            【商品別売上ランキング（上位5商品）】
            {analysis['product_analysis'].head().to_string()}
            
            【月別トレンド】
            {analysis['monthly_trend'].to_string()}
            
            【主要顧客（上位5社）】
            {analysis['customer_analysis'].head().to_string()}
            """
        else:
            # 全データのサマリー
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
        
        # 改善されたシステムプロンプト
        system_prompt = f"""
        あなたは優秀な売上データ分析アシスタントです。以下の指示に従って、正確で洞察に富んだ回答を提供してください：

        【回答のルール】
        1. 必ず具体的な数値データを含めて回答する
        2. データに基づいた客観的な分析を行う
        3. トレンドやパターンを特定し、その理由を考察する
        4. 改善提案や推奨事項を具体的に示す
        5. 日本語で分かりやすく回答する
        6. 必要に応じて表形式でデータを整理する

        【分析の視点】
        - 売上トレンド：時系列での変化と要因
        - 担当者パフォーマンス：個人別の成果と特徴
        - 商品分析：売上・粗利率・人気度
        - 顧客分析：重要顧客と購買パターン
        - 収益性：粗利率と改善点

        {context}
        
        {data_summary}
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
                max_tokens=1500,  # より長い回答を許可
                temperature=0.3,  # より一貫性のある回答
                top_p=0.9
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
                "max_tokens": 1500,
                "temperature": 0.3,
                "top_p": 0.9
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
            response = call_llm_api(prompt, filter_context, filtered_df)
            st.markdown(response)
    
    # AIメッセージを追加
    st.session_state.messages.append({"role": "assistant", "content": response})

# 高度な分析機能
st.subheader("🔍 高度な分析機能")

# 分析タイプの選択
analysis_type = st.selectbox(
    "分析タイプを選択",
    ["基本分析", "詳細トレンド分析", "パフォーマンス比較", "予測分析", "改善提案"]
)

if analysis_type == "基本分析":
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📈 売上トレンドを分析して"):
            with st.spinner("分析中..."):
                question = "現在の期間での売上トレンドを詳細に分析し、月別の変化、成長している商品や担当者、そしてその要因を具体的な数値と共に教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("👥 担当者別パフォーマンス"):
            with st.spinner("分析中..."):
                question = "担当者別の売上パフォーマンスを包括的に分析し、最も優秀な担当者の特徴、各担当者の強みと弱み、そして改善点を具体的な数値と共に教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

    with col2:
        if st.button("📦 商品別分析"):
            with st.spinner("分析中..."):
                question = "商品別の売上分析を行い、最も売上が良い商品と粗利率の高い商品を特定し、商品の特徴、顧客層、そして今後の戦略を具体的な数値と共に教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("💰 収益性分析"):
            with st.spinner("分析中..."):
                question = "全体的な収益性を詳細に分析し、粗利率の改善点、コスト効率、そして具体的な改善提案を数値データと共に教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

elif analysis_type == "詳細トレンド分析":
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 月別詳細トレンド"):
            with st.spinner("分析中..."):
                question = "月別の売上・粗利・取引件数の詳細なトレンド分析を行い、季節性、成長パターン、異常値の特定とその要因を教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("🎯 顧客購買パターン"):
            with st.spinner("分析中..."):
                question = "顧客の購買パターンを分析し、重要顧客の特徴、購買頻度、商品選択の傾向、そして顧客セグメンテーションを教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

    with col2:
        if st.button("📈 成長率分析"):
            with st.spinner("分析中..."):
                question = "売上・粗利・取引件数の成長率を計算し、最も成長している分野、停滞している分野、そしてその要因を分析してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("🔄 相関分析"):
            with st.spinner("分析中..."):
                question = "売上金額、粗利金額、取引件数、担当者、商品の相関関係を分析し、どの要素が売上に最も影響しているかを教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

elif analysis_type == "パフォーマンス比較":
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏆 担当者ランキング"):
            with st.spinner("分析中..."):
                question = "担当者を売上、粗利、取引件数、粗利率でランキングし、各担当者の強みと改善点を詳細に分析してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("📦 商品ランキング"):
            with st.spinner("分析中..."):
                question = "商品を売上、粗利、取引件数、粗利率でランキングし、各商品の市場ポジションと戦略的価値を分析してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

    with col2:
        if st.button("👥 担当者効率性"):
            with st.spinner("分析中..."):
                question = "担当者の効率性（売上/取引件数、粗利/取引件数）を分析し、最も効率的な担当者とその成功要因を教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("📊 商品効率性"):
            with st.spinner("分析中..."):
                question = "商品の効率性（売上/取引件数、粗利/取引件数）を分析し、最も効率的な商品とその特徴を教えてください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

elif analysis_type == "予測分析":
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔮 売上予測"):
            with st.spinner("分析中..."):
                question = "現在のトレンドを基に、今後の売上予測を行い、成長が期待できる分野とリスク要因を分析してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("📈 成長機会"):
            with st.spinner("分析中..."):
                question = "データから成長機会を特定し、どの商品・担当者・顧客セグメントに投資すべきかを分析してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

    with col2:
        if st.button("⚠️ リスク分析"):
            with st.spinner("分析中..."):
                question = "売上データからリスク要因を特定し、どの分野で売上が減少する可能性があるかを分析してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("🎯 最適化提案"):
            with st.spinner("分析中..."):
                question = "現在のリソース配分を最適化し、売上と粗利を最大化するための具体的な戦略を提案してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

elif analysis_type == "改善提案":
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💡 売上改善策"):
            with st.spinner("分析中..."):
                question = "売上を改善するための具体的な施策を、データに基づいて優先度順に提案してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("📊 粗利率改善"):
            with st.spinner("分析中..."):
                question = "粗利率を改善するための具体的な施策を、商品・担当者・顧客の観点から提案してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

    with col2:
        if st.button("👥 担当者育成"):
            with st.spinner("分析中..."):
                question = "担当者のパフォーマンス向上のための育成プログラムと、ベストプラクティスの共有方法を提案してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)
        
        if st.button("🎯 戦略的提案"):
            with st.spinner("分析中..."):
                question = "長期的な成長戦略を、市場分析、競合分析、内部リソースの観点から提案してください。"
                response = call_llm_api(question, filter_context, filtered_df)
                st.info(response)

# チャット履歴管理
st.subheader("💬 チャット履歴管理")
col1, col2 = st.columns(2)

with col1:
    if st.button("🗑️ チャット履歴をクリア"):
        st.session_state.messages = []
        st.rerun()

with col2:
    if st.button("📥 分析結果をエクスポート"):
        if st.session_state.messages:
            # チャット履歴をテキストファイルとしてダウンロード
            chat_history = ""
            for msg in st.session_state.messages:
                role = "ユーザー" if msg["role"] == "user" else "AI"
                chat_history += f"【{role}】\n{msg['content']}\n\n"
            
            st.download_button(
                label="📄 チャット履歴をダウンロード",
                data=chat_history,
                file_name=f"ai_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

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

# 追加の統計情報
if len(filtered_df) > 0:
    st.subheader("📈 詳細統計")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        top_staff = filtered_df.groupby('担当者')['売上金額'].sum().sort_values(ascending=False).head(1)
        if not top_staff.empty:
            st.metric("売上No.1担当者", f"{top_staff.index[0]}\n¥{top_staff.iloc[0]:,}")
    
    with col2:
        top_product = filtered_df.groupby('商品名')['売上金額'].sum().sort_values(ascending=False).head(1)
        if not top_product.empty:
            st.metric("売上No.1商品", f"{top_product.index[0]}\n¥{top_product.iloc[0]:,}")
    
    with col3:
        top_customer = filtered_df.groupby('顧客名')['売上金額'].sum().sort_values(ascending=False).head(1)
        if not top_customer.empty:
            st.metric("売上No.1顧客", f"{top_customer.index[0]}\n¥{top_customer.iloc[0]:,}")
    
    with col4:
        best_profit_rate = filtered_df.groupby('商品名').apply(
            lambda x: (x['粗利金額'].sum() / x['売上金額'].sum() * 100) if x['売上金額'].sum() > 0 else 0
        ).sort_values(ascending=False).head(1)
        if not best_profit_rate.empty:
            st.metric("最高粗利率商品", f"{best_profit_rate.index[0]}\n{best_profit_rate.iloc[0]:.1f}%")

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